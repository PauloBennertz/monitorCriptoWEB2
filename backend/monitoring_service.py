import requests
import pandas as pd
import time
import logging
import copy
from datetime import datetime, timedelta
from . import robust_services
import os
from .indicators import calculate_rsi, calculate_bollinger_bands, calculate_macd, calculate_emas, calculate_hilo_signals
from .notification_service import send_telegram_alert
from pycoingecko import CoinGeckoAPI
from .app_state import load_coin_mapping_cache, save_coin_mapping_cache

cg_client = CoinGeckoAPI()

def get_klines_data(symbol, interval='1h', limit=300):
    """Busca dados de k-lines da Binance com cache, rate limiting e validação."""
    if not robust_services.DataValidator.validate_symbol(symbol):
        logging.warning(f"Tentativa de busca por símbolo inválido: {symbol}")
        return None

    cache_args = {'func': 'get_klines_data', 'symbol': symbol, 'interval': interval, 'limit': limit}
    cached_df = robust_services.data_cache.get(cache_args, ttl=180)
    if cached_df is not None:
        return cached_df

    robust_services.rate_limiter.wait_if_needed()
    url = "https://api.binance.com/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        df = pd.DataFrame(response.json(), columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['close'] = df['close'].apply(robust_services.DataValidator.safe_price)
        df['high'] = df['high'].apply(robust_services.DataValidator.safe_price)
        df['low'] = df['low'].apply(robust_services.DataValidator.safe_price)
        robust_services.data_cache.set(cache_args, df)
        return df
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de rede ao buscar klines para {symbol}: {e}")
        return None

def get_ticker_data():
    """Busca os dados de ticker de 24h para todas as moedas, com cache."""
    cache_args = {'func': 'get_ticker_data'}
    cached_data = robust_services.data_cache.get(cache_args, ttl=60)
    if cached_data is not None: return cached_data

    robust_services.rate_limiter.wait_if_needed()
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        response.raise_for_status()
        ticker_data = {item['symbol']: item for item in response.json()}
        robust_services.data_cache.set(cache_args, ticker_data)
        return ticker_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao buscar dados de 24h (ticker): {e}")
        return {}

def get_market_caps_coingecko(symbols_to_monitor, coingecko_mapping):
    """Busca o valor de mercado (market cap) para uma lista de moedas via CoinGecko."""
    logging.info(f"Buscando market caps para os seguintes símbolos: {symbols_to_monitor}")
    market_caps = {}
    coin_ids_to_fetch = []
    symbol_to_coin_id = {}

    try:
        all_coins = cg_client.get_coins_list()
    except Exception as e:
        logging.error(f"Falha ao buscar a lista de moedas da CoinGecko: {e}")
        return {}

    for binance_symbol in symbols_to_monitor:
        base_asset = binance_symbol.replace('USDT', '').lower()

        # Busca case-insensitive pelo símbolo
        coin_info = next((item for item in all_coins if item['symbol'].lower() == base_asset), None)

        if coin_info:
            coin_id = coin_info['id']
            coin_ids_to_fetch.append(coin_id)
            symbol_to_coin_id[coin_id] = binance_symbol
        else:
            logging.warning(f"Não foi possível encontrar o ID da CoinGecko para o símbolo: {base_asset.upper()}")

    if not coin_ids_to_fetch: return {}

    cache_key = {'func': 'get_market_caps_coingecko', 'ids': tuple(sorted(coin_ids_to_fetch))}
    cached_data = robust_services.data_cache.get(cache_key, ttl=300)
    if cached_data is not None: return cached_data

    try:
        robust_services.rate_limiter.wait_if_needed()
        response = cg_client.get_coins_markets(vs_currency='usd', ids=','.join(coin_ids_to_fetch))
        for coin_data in response:
            original_binance_symbol = symbol_to_coin_id.get(coin_data['id'])
            if original_binance_symbol:
                market_caps[original_binance_symbol] = coin_data.get('market_cap')
        robust_services.data_cache.set(cache_key, market_caps)
        return market_caps
    except Exception as e:
        logging.error(f"Erro ao buscar market caps da CoinGecko: {e}")
        return {}

def get_coingecko_global_mapping():
    """
    Busca a lista de moedas da CoinGecko para mapear Símbolo -> Nome.
    Utiliza um cache local que é atualizado a cada 24 horas.
    """
    cached_mapping = load_coin_mapping_cache()
    if cached_mapping is not None:
        return cached_mapping

    logging.info("Buscando novo mapeamento de nomes da CoinGecko (cache expirado ou inexistente)...")
    robust_services.rate_limiter.wait_if_needed()
    try:
        coins_list = cg_client.get_coins_list()
        mapping = {coin['symbol'].upper(): coin['name'] for coin in coins_list}

        save_coin_mapping_cache(mapping) # Salva o novo mapeamento no cache

        logging.info("Mapeamento de nomes CoinGecko carregado e cache atualizado.")
        return mapping
    except Exception as e:
        logging.error(f"Não foi possível buscar mapeamento da CoinGecko: {e}")
        return {}

def fetch_all_binance_symbols_startup(existing_config):
    """Busca todos os símbolos USDT da Binance na inicialização."""
    logging.info("Buscando lista de moedas da Binance...")
    robust_services.rate_limiter.wait_if_needed()
    try:
        response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=15)
        response.raise_for_status()
        symbols = sorted([s['symbol'] for s in response.json()['symbols'] if s['symbol'].endswith('USDT')])
        logging.info(f"{len(symbols)} moedas encontradas na Binance.")
        return symbols
    except Exception as e:
        logging.error(f"Não foi possível buscar a lista de moedas da Binance: {e}")
        logging.warning("Retornando moedas da configuração existente como fallback.")
        return [c['symbol'] for c in existing_config.get('cryptos_to_monitor', [])]

def _get_sound_for_trigger(trigger_key, sound_config):
    """Determina o som apropriado para um gatilho de alerta com base na sua chave programática."""
    if not sound_config:
        return os.path.join('sons', 'Alerta.mp3')

    key_to_config_map = {
        'RSI_SOBRECOMPRA': 'overbought',
        'RSI_SOBREVENDA': 'oversold',
        'CRUZ_DOURADA': 'golden_cross',
        'CRUZ_DA_MORTE': 'death_cross',
        'PRECO_ACIMA': 'price_above',
        'PRECO_ABAIXO': 'price_below',
        'VOLUME_ANORMAL': 'high_volume',
        'FUGA_CAPITAL': 'critical_alert',
        'ENTRADA_CAPITAL': 'critical_alert',
        'HILO_COMPRA': 'golden_cross',
        'HILO_VENDA': 'death_cross',
    }

    default_sounds = {
        'overbought': 'sobrecomprado.wav',
        'oversold': 'sobrevendido.wav',
        'golden_cross': 'cruzamentoAlta.wav',
        'death_cross': 'cruzamentoBaixa.wav',
        'price_above': 'precoAcima.wav',
        'price_below': 'precoAbaixo.wav',
        'high_volume': 'volumeAlto.wav',
        'critical_alert': 'alertaCritico.wav',
        'default_alert': 'Alerta.mp3',
    }

    config_key = key_to_config_map.get(trigger_key, 'default_alert')
    sound_file = sound_config.get(config_key, default_sounds.get(config_key))

    return os.path.join('sons', sound_file)

def _check_and_trigger_alerts(symbol, alert_config, analysis_data):
    """
    Verifica as condições de alerta para um símbolo e retorna uma lista de alertas disparados.
    Refatorado para não ter dependências de GUI (data_queue, sound_config).
    """
    triggered_alerts = []
    conditions = alert_config.get('conditions', {})
    triggered_conditions = alert_config.get('triggered_conditions', {})
    if isinstance(triggered_conditions, list): # Legacy config compatibility
        triggered_conditions = {}

    alert_cooldown_minutes = alert_config.get('alert_cooldown_minutes', 60)
    current_price = analysis_data.get('price', 0)
    rsi = analysis_data.get('rsi_value', 50)

    # Define as condições de alerta
    alert_definitions = {
        'preco_baixo': {'key': 'PRECO_ABAIXO', 'msg': f"Preço Abaixo de ${conditions.get('preco_baixo', {}).get('value', 0):.2f}"},
        'preco_alto': {'key': 'PRECO_ACIMA', 'msg': f"Preço Acima de ${conditions.get('preco_alto', {}).get('value', 0):.2f}"},
        'rsi_sobrevendido': {'key': 'RSI_SOBREVENDA', 'msg': f"RSI em Sobrevenda (<= {conditions.get('rsi_sobrevendido', {}).get('value', 30):.1f})"},
        'rsi_sobrecomprado': {'key': 'RSI_SOBRECOMPRA', 'msg': f"RSI em Sobrecompra (>= {conditions.get('rsi_sobrecomprado', {}).get('value', 70):.1f})"},
        'bollinger_abaixo': {'key': 'PRECO_ABAIXO_BANDA_INFERIOR', 'msg': "Preço Abaixo da Banda de Bollinger"},
        'bollinger_acima': {'key': 'PRECO_ACIMA_BANDA_SUPERIOR', 'msg': "Preço Acima da Banda de Bollinger"},
        'macd_cruz_baixa': {'key': 'CRUZAMENTO_MACD_BAIXA', 'msg': "MACD: Cruzamento de Baixa"},
        'macd_cruz_alta': {'key': 'CRUZAMENTO_MACD_ALTA', 'msg': "MACD: Cruzamento de Alta"},
        'mme_cruz_morte': {'key': 'CRUZ_DA_MORTE', 'msg': "MME: Cruz da Morte (50/200)"},
        'mme_cruz_dourada': {'key': 'CRUZ_DOURADA', 'msg': "MME: Cruz Dourada (50/200)"},
        'hilo_compra': {'key': 'HILO_COMPRA', 'msg': "HiLo: Sinal de Compra"},
        'hilo_venda': {'key': 'HILO_VENDA', 'msg': "HiLo: Sinal de Venda"},
    }

    active_triggers = []
    # Lógica de verificação de condições
    if conditions.get('preco_baixo', {}).get('enabled') and current_price <= conditions['preco_baixo']['value']: active_triggers.append(alert_definitions['preco_baixo'])
    if conditions.get('preco_alto', {}).get('enabled') and current_price >= conditions['preco_alto']['value']: active_triggers.append(alert_definitions['preco_alto'])
    if conditions.get('rsi_sobrevendido', {}).get('enabled') and rsi <= conditions['rsi_sobrevendido']['value']: active_triggers.append(alert_definitions['rsi_sobrevendido'])
    if conditions.get('rsi_sobrecomprado', {}).get('enabled') and rsi >= conditions['rsi_sobrecomprado']['value']: active_triggers.append(alert_definitions['rsi_sobrecomprado'])
    if conditions.get('bollinger_abaixo', {}).get('enabled') and analysis_data.get('bollinger_signal') == "Abaixo da Banda": active_triggers.append(alert_definitions['bollinger_abaixo'])
    if conditions.get('bollinger_acima', {}).get('enabled') and analysis_data.get('bollinger_signal') == "Acima da Banda": active_triggers.append(alert_definitions['bollinger_acima'])
    if conditions.get('macd_cruz_baixa', {}).get('enabled') and analysis_data.get('macd_signal') == "Cruzamento de Baixa": active_triggers.append(alert_definitions['macd_cruz_baixa'])
    if conditions.get('macd_cruz_alta', {}).get('enabled') and analysis_data.get('macd_signal') == "Cruzamento de Alta": active_triggers.append(alert_definitions['macd_cruz_alta'])
    if conditions.get('mme_cruz_morte', {}).get('enabled') and analysis_data.get('mme_cross') == "Cruz da Morte": active_triggers.append(alert_definitions['mme_cruz_morte'])
    if conditions.get('mme_cruz_dourada', {}).get('enabled') and analysis_data.get('mme_cross') == "Cruz Dourada": active_triggers.append(alert_definitions['mme_cruz_dourada'])
    if conditions.get('hilo_compra', {}).get('enabled') and analysis_data.get('hilo_signal') == "HiLo Buy": active_triggers.append(alert_definitions['hilo_compra'])
    if conditions.get('hilo_venda', {}).get('enabled') and analysis_data.get('hilo_signal') == "HiLo Sell": active_triggers.append(alert_definitions['hilo_venda'])

    now = datetime.now()
    for trigger in active_triggers:
        trigger_key = trigger['key']
        last_triggered_str = triggered_conditions.get(trigger_key)
        if last_triggered_str:
            try:
                last_triggered_time = datetime.fromisoformat(last_triggered_str)
                if now - last_triggered_time < timedelta(minutes=alert_cooldown_minutes):
                    continue  # Pula o alerta se estiver em cooldown
            except ValueError:
                logging.warning(f"Formato de data inválido para cooldown: {last_triggered_str}")

        # Se não estiver em cooldown, adiciona à lista de retorno
        alert_info = {
            'timestamp': now.isoformat(),
            'symbol': symbol,
            'trigger_key': trigger_key,
            'message': trigger['msg'],
            'analysis_snapshot': analysis_data
        }
        triggered_alerts.append(alert_info)

        # Atualiza o timestamp do último disparo para o cooldown
        triggered_conditions[trigger_key] = now.isoformat()

    # Retorna os alertas disparados e o estado atualizado dos cooldowns
    return triggered_alerts, triggered_conditions

def _analyze_symbol(symbol, ticker_data, market_cap=None, coingecko_mapping=None):
    """Coleta e analisa todos os dados técnicos para um único símbolo."""
    base_asset = symbol.replace('USDT', '')
    coin_name = coingecko_mapping.get(base_asset, base_asset) if coingecko_mapping else base_asset

    analysis_result = {
        'symbol': symbol,
        'name': coin_name,
        'price': 0.0,
        'price_change_24h': 0.0,
        'volume_24h': 0.0,
        'market_cap': market_cap or 0,
        'rsi_value': 0.0,
        'rsi_signal': "N/A",
        'bollinger_signal': "Nenhum",
        'macd_signal': "Nenhum",
        'mme_cross': "Nenhum",
        'hilo_signal': "Nenhum"
    }

    symbol_ticker = ticker_data.get(symbol, {})
    analysis_result['price'] = robust_services.DataValidator.safe_price(symbol_ticker.get('lastPrice'))
    analysis_result['price_change_24h'] = robust_services.DataValidator.safe_float(symbol_ticker.get('priceChangePercent'))
    analysis_result['volume_24h'] = robust_services.DataValidator.safe_float(symbol_ticker.get('quoteVolume'))

    df = get_klines_data(symbol)
    if df is None or df.empty:
        return analysis_result

    rsi_series, _, _ = calculate_rsi(df)
    upper_band_series, lower_band_series, _ = calculate_bollinger_bands(df)
    macd_cross = calculate_macd(df)
    _, _, hilo_signal = calculate_hilo_signals(df)
    emas = calculate_emas(df, periods=[50, 200])

    # Get the latest numeric value from each indicator series, handling potential NaNs
    rsi_value = rsi_series.iloc[-1] if not rsi_series.empty and pd.notna(rsi_series.iloc[-1]) else 0.0
    upper_band = upper_band_series.iloc[-1] if not upper_band_series.empty and pd.notna(upper_band_series.iloc[-1]) else 0.0
    lower_band = lower_band_series.iloc[-1] if not lower_band_series.empty and pd.notna(lower_band_series.iloc[-1]) else 0.0

    analysis_result['hilo_signal'] = hilo_signal
    analysis_result['rsi_value'] = rsi_value
    analysis_result['rsi_signal'] = f"{rsi_value:.2f}" if rsi_value > 0 else "N/A"

    if upper_band > 0 and analysis_result['price'] > 0:
        if analysis_result['price'] > upper_band:
            analysis_result['bollinger_signal'] = "Acima da Banda"
        elif analysis_result['price'] < lower_band:
            analysis_result['bollinger_signal'] = "Abaixo da Banda"

    analysis_result['macd_signal'] = macd_cross

    if 50 in emas and 200 in emas and len(emas[50]) > 1 and len(emas[200]) > 1:
        if emas[50].iloc[-2] < emas[200].iloc[-2] and emas[50].iloc[-1] > emas[200].iloc[-1]:
            analysis_result['mme_cross'] = "Cruz Dourada"
        elif emas[50].iloc[-2] > emas[200].iloc[-2] and emas[50].iloc[-1] < emas[200].iloc[-1]:
            analysis_result['mme_cross'] = "Cruz da Morte"

    return analysis_result

def run_monitoring_cycle(config, coingecko_mapping):
    """
    Executa um único ciclo de monitoramento para todas as moedas configuradas.
    Retorna uma lista de dados analisados e uma lista de alertas disparados.
    Refatorado para ser uma função one-shot para uso da API.
    """
    logging.info("Executando ciclo de monitoramento sob demanda.")

    all_analysis_data = []
    all_triggered_alerts = []

    monitored_cryptos = copy.deepcopy(config.get("cryptos_to_monitor", []))
    if not monitored_cryptos:
        return all_analysis_data, all_triggered_alerts

    ticker_data = get_ticker_data()
    if not ticker_data:
        logging.error("Não foi possível obter dados do ticker da Binance. Abortando ciclo.")
        return [], []

    symbols = [c['symbol'] for c in monitored_cryptos]
    market_caps_data = get_market_caps_coingecko(symbols, coingecko_mapping)

    for crypto_config in monitored_cryptos:
        symbol = crypto_config.get('symbol')
        if not symbol or not robust_services.DataValidator.validate_symbol(symbol):
            continue

        analysis_data = _analyze_symbol(symbol, ticker_data, market_caps_data.get(symbol), coingecko_mapping)
        all_analysis_data.append(analysis_data)

        if alert_config := crypto_config.get('alert_config'):
            triggered_alerts, updated_cooldowns = _check_and_trigger_alerts(symbol, alert_config, analysis_data)
            if triggered_alerts:
                all_triggered_alerts.extend(triggered_alerts)
                # Atualiza o estado do cooldown na configuração principal
                alert_config['triggered_conditions'] = updated_cooldowns

        time.sleep(0.1) # Pequeno delay para não sobrecarregar a API

    logging.info(f"Ciclo de monitoramento sob demanda completo. {len(all_analysis_data)} moedas analisadas, {len(all_triggered_alerts)} alertas gerados.")
    return all_analysis_data, all_triggered_alerts

def run_single_symbol_update(symbol, config, coingecko_mapping):
    """
    Executa uma atualização de dados para uma única moeda.
    Retorna os dados de análise e quaisquer alertas disparados.
    """
    logging.info(f"Iniciando atualização sob demanda para {symbol}...")
    crypto_config = next((c for c in config.get("cryptos_to_monitor", []) if c['symbol'] == symbol), None)
    if not crypto_config:
        logging.warning(f"Nenhuma configuração encontrada para {symbol}. Não é possível atualizar.")
        return None, None

    ticker_data = get_ticker_data()
    if not ticker_data:
        logging.error(f"Não foi possível obter dados do ticker para a atualização de {symbol}.")
        return None, None

    market_caps_data = get_market_caps_coingecko([symbol], coingecko_mapping)
    analysis_data = _analyze_symbol(symbol, ticker_data, market_caps_data.get(symbol), coingecko_mapping)

    triggered_alerts = []
    if alert_config := crypto_config.get('alert_config'):
        triggered_alerts, updated_cooldowns = _check_and_trigger_alerts(symbol, alert_config, analysis_data)
        if triggered_alerts:
             alert_config['triggered_conditions'] = updated_cooldowns

    logging.info(f"Atualização para {symbol} completa. {len(triggered_alerts)} alertas gerados.")
    return analysis_data, triggered_alerts

def get_btc_dominance():
    """Busca a dominância de mercado do BTC a partir da CoinGecko."""
    try:
        cache_key = {'func': 'get_btc_dominance'}
        if cached_data := robust_services.data_cache.get(cache_key, ttl=300):
            return cached_data

        robust_services.rate_limiter.wait_if_needed()
        global_data = cg_client.get_global()

        # A estrutura da resposta é {'data': {'market_cap_percentage': {'btc': 49.9}}}
        btc_dominance = global_data.get('market_cap_percentage', {}).get('btc')

        if btc_dominance is not None and isinstance(btc_dominance, (int, float)):
            # Retorna o número puro para ser formatado no frontend
            robust_services.data_cache.set(cache_key, btc_dominance)
            return btc_dominance
        else:
            logging.warning(f"Dominância BTC não encontrada ou em formato inválido na resposta da API: {global_data}")
            return "N/A"

    except Exception as e:
        logging.error(f"Não foi possível buscar a dominância do BTC: {e}")
        return "Erro"

def get_top_100_coins():
    """Busca as 100 principais criptomoedas por capitalização de mercado da CoinGecko."""
    try:
        robust_services.rate_limiter.wait_if_needed()
        coins = cg_client.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=100, page=1)
        return coins
    except Exception as e:
        logging.error(f"Erro ao buscar as 100 principais moedas da CoinGecko: {e}")
        return []