import requests
import pandas as pd
import time
import logging
import copy
from datetime import datetime, timedelta
from . import robust_services
import os
from .indicators import (
    calculate_rsi, 
    calculate_bollinger_bands, 
    calculate_macd, 
    calculate_emas, 
    calculate_hilo_signals, 
    calculate_media_movel_cross,
    calculate_hma,    
    calculate_vwap
)
from .notification_service import send_telegram_alert
from pycoingecko import CoinGeckoAPI
from .app_state import load_coin_list_cache, save_coin_list_cache
from .notification_service import send_telegram_alert


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

def get_market_caps_coingecko(symbols_to_monitor, all_coins):
    """Busca o valor de mercado (market cap) para uma lista de moedas via CoinGecko."""
    logging.info(f"Buscando market caps para os seguintes símbolos: {symbols_to_monitor}")
    market_caps = {}
    coin_ids_to_fetch = []
    symbol_to_coin_id = {}

    if not all_coins:
        logging.error("A lista de moedas da CoinGecko não está disponível.")
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

def get_cached_coin_list():
    """
    Busca a lista de moedas da CoinGecko, utilizando um cache local que é atualizado a cada 24 horas.
    """
    cached_list = load_coin_list_cache()
    if cached_list is not None:
        return cached_list

    logging.info("Buscando nova lista de moedas da CoinGecko (cache expirado ou inexistente)...")
    robust_services.rate_limiter.wait_if_needed()
    try:
        coins_list = cg_client.get_coins_list()
        save_coin_list_cache(coins_list) # Salva a lista completa no cache

        logging.info("Lista de moedas da CoinGecko carregada e cache atualizado.")
        return coins_list
    except Exception as e:
        logging.error(f"Não foi possível buscar a lista de moedas da CoinGecko: {e}")
        return []

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

        # WORKAROUND: Fallback to a hardcoded list for sandbox/offline testing.
        hardcoded_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'SHIBUSDT', 'AVAXUSDT', 'LINKUSDT',
            'DOTUSDT', 'TRXUSDT', 'MATICUSDT', 'ICPUSDT', 'BCHUSDT', 'LTCUSDT', 'NEARUSDT', 'UNIUSDT', 'FILUSDT', 'ETCUSDT',
            'ATOMUSDT', 'XMRUSDT', 'XLMUSDT', 'HBARUSDT', 'APTUSDT', 'CROUSDT', 'VETUSDT', 'LDOUSDT',
            'IMXUSDT', 'GRTUSDT', 'RNDRUSDT', 'OPUSDT', 'EGLDUSDT', 'QNTUSDT', 'AAVEUSDT', 'ALGOUSDT', 'STXUSDT', 'MANAUSDT',
            'SANDUSDT', 'AXSUSDT', 'FTMUSDT', 'THETAUSDT', 'EOSUSDT', 'XTZUSDT', 'ZECUSDT', 'IOTAUSDT', 'NEOUSDT', 'CHZUSDT'
        ]

        config_symbols = [c['symbol'] for c in existing_config.get('cryptos_to_monitor', [])]
        combined_symbols = sorted(list(set(hardcoded_symbols + config_symbols)))
        logging.warning(f"WORKAROUND: Retornando uma lista combinada de {len(combined_symbols)} moedas (hardcoded + config) como fallback.")
        return combined_symbols

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

def _check_and_trigger_alerts(symbol, alert_config, analysis_data, global_config):
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
    macd_value = analysis_data.get('macd_value', 0)

    # Gerencia o estado do "Filter Mode" (Death Cross)
    death_cross_active = alert_config.get('death_cross_active', False)
    if analysis_data.get('mme_cross') == "Cruz da Morte":
        death_cross_active = True
        alert_config['death_cross_active'] = True  # Persiste o estado
    elif analysis_data.get('mme_cross') == "Cruz Dourada":
        death_cross_active = False
        alert_config['death_cross_active'] = False # Persiste o estado

    # Define as condições de alerta
    alert_definitions = {
        'preco_baixo': {'key': 'PRECO_ABAIXO', 'msg': f"Preço Abaixo de ${conditions.get('preco_baixo', {}).get('value', 0):.2f}"},
        'preco_alto': {'key': 'PRECO_ACIMA', 'msg': f"Preço Acima de ${conditions.get('preco_alto', {}).get('value', 0):.2f}"},
        'rsi_sobrevendido': {'key': 'RSI_SOBREVENDA', 'msg': f"RSI em Sobrevenda (<= {conditions.get('rsi_sobrevendido', {}).get('value', 30):.1f})"},
        'rsi_sobrecomprado': {'key': 'RSI_SOBRECOMPRA', 'msg': f"RSI em Sobrecompra (>= {conditions.get('rsi_sobrecomprado', {}).get('value', 75):.1f})"},
        'bollinger_abaixo': {'key': 'PRECO_ABAIXO_BANDA_INFERIOR', 'msg': "Preço Abaixo da Banda de Bollinger"},
        'bollinger_acima': {'key': 'PRECO_ACIMA_BANDA_SUPERIOR', 'msg': "Preço Acima da Banda de Bollinger"},
        'macd_cruz_baixa': {'key': 'CRUZAMENTO_MACD_BAIXA', 'msg': "MACD: Cruzamento de Baixa"},
        'macd_cruz_alta': {'key': 'CRUZAMENTO_MACD_ALTA', 'msg': "MACD: Cruzamento de Alta"},
        'mme_cruz_morte': {'key': 'CRUZ_DA_MORTE', 'msg': "MME: Cruz da Morte (50/200)"},
        'mme_cruz_dourada': {'key': 'CRUZ_DOURADA', 'msg': "MME: Cruz Dourada (50/200)"},
        'hilo_compra': {'key': 'HILO_COMPRA', 'msg': "HiLo: Sinal de Compra"},
        'hilo_venda': {'key': 'HILO_VENDA', 'msg': "HiLo: Sinal de Venda"},
        'media_movel_cima': {'key': 'MEDIA_MOVEL_CIMA', 'msg': f"Preço cruzou MME {conditions.get('media_movel_cima', {}).get('value', 200)} para Cima + MACD > 0"},
        'media_movel_baixo': {'key': 'MEDIA_MOVEL_BAIXO', 'msg': f"Preço cruzou MME {conditions.get('media_movel_baixo', {}).get('value', 17)} para Baixo"},
    }

    active_triggers = []
    # Lógica de verificação de condições
    if conditions.get('PRECO_ABAIXO', {}).get('enabled') and current_price <= conditions['PRECO_ABAIXO']['value']: active_triggers.append(alert_definitions['preco_baixo'])
    if conditions.get('PRECO_ACIMA', {}).get('enabled') and current_price >= conditions['PRECO_ACIMA']['value']: active_triggers.append(alert_definitions['preco_alto'])
    if conditions.get('rsi_sobrevendido', {}).get('enabled') and rsi <= conditions['rsi_sobrevendido']['value']: active_triggers.append(alert_definitions['rsi_sobrevendido'])

    if (config := conditions.get('rsi_sobrecomprado', {})) and config.get('enabled'):
        if rsi >= config.get('value', 75):
            active_triggers.append(alert_definitions['rsi_sobrecomprado'])

    if conditions.get('bollinger_abaixo', {}).get('enabled') and analysis_data.get('bollinger_signal') == "Abaixo da Banda": active_triggers.append(alert_definitions['bollinger_abaixo'])
    if conditions.get('bollinger_acima', {}).get('enabled') and analysis_data.get('bollinger_signal') == "Acima da Banda": active_triggers.append(alert_definitions['bollinger_acima'])
    if conditions.get('macd_cruz_baixa', {}).get('enabled') and analysis_data.get('macd_signal') == "Cruzamento de Baixa": active_triggers.append(alert_definitions['macd_cruz_baixa'])
    if conditions.get('macd_cruz_alta', {}).get('enabled') and analysis_data.get('macd_signal') == "Cruzamento de Alta" and rsi < 30: active_triggers.append(alert_definitions['macd_cruz_alta'])
    if conditions.get('mme_cruz_morte', {}).get('enabled') and analysis_data.get('mme_cross') == "Cruz da Morte" and current_price < analysis_data.get('mme_200', float('inf')): active_triggers.append(alert_definitions['mme_cruz_morte'])
    if conditions.get('mme_cruz_dourada', {}).get('enabled') and analysis_data.get('mme_cross') == "Cruz Dourada": active_triggers.append(alert_definitions['mme_cruz_dourada'])

    # Aplica o "Filter Mode" para suprimir alertas de compra se a Death Cross estiver ativa
    if not death_cross_active:
        if conditions.get('hilo_compra', {}).get('enabled') and analysis_data.get('hilo_signal') == "HiLo Buy":
            active_triggers.append(alert_definitions['hilo_compra'])

        if (config := conditions.get('media_movel_cima', {})) and config.get('enabled'):
            period = config.get('value', 200)
            if analysis_data.get('media_movel_cross', {}).get(period) == "Cruzamento de Alta" and macd_value > 0:
                active_triggers.append(alert_definitions['media_movel_cima'])

    if conditions.get('hilo_venda', {}).get('enabled') and analysis_data.get('hilo_signal') == "HiLo Sell": active_triggers.append(alert_definitions['hilo_venda'])

    if (config := conditions.get('media_movel_baixo', {})) and config.get('enabled'):
        period = config.get('value', 17)
        if analysis_data.get('media_movel_cross', {}).get(period) == "Cruzamento de Baixa":
            active_triggers.append(alert_definitions['media_movel_baixo'])

    now = datetime.now()
    telegram_config = global_config.get('telegram_config', {})
    bot_token = telegram_config.get('bot_token')
    chat_id = telegram_config.get('chat_id')

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

        # Envia notificação para o Telegram
        if bot_token and chat_id:
            telegram_message = f"🔔 *Alerta de Cripto* 🔔\n\n*Moeda:* {symbol}\n*Condição:* {trigger['msg']}\n*Preço Atual:* ${current_price:.2f}"
            send_telegram_alert(bot_token, chat_id, telegram_message)

        # Atualiza o timestamp do último disparo para o cooldown
        triggered_conditions[trigger_key] = now.isoformat()

    # Retorna os alertas disparados e o estado atualizado dos cooldowns
    return triggered_alerts, triggered_conditions

def _analyze_symbol(symbol, ticker_data, market_cap=None, coingecko_mapping=None):
    """Coleta e analisa todos os dados técnicos para um único símbolo."""
    base_asset = symbol.replace('USDT', '')
    coin_name = coingecko_mapping.get(base_asset, base_asset) if coingecko_mapping else base_asset

    # 1. Primeiro buscamos os dados (df)
    df = get_klines_data(symbol)
    
    # Se não houver dados, retornamos um dicionário básico para evitar erro
    if df is None or df.empty:
        return {
            'symbol': symbol, 'name': coin_name, 'price': 0.0,
            'hma_active': False, 'vwap_active': False
        }

    # 2. Agora calculamos os novos indicadores (PRECISAM VIR ANTES DO DICIONÁRIO)
    # Cálculo da HMA
    hma_series = calculate_hma(df['close'], period=21)
    latest_hma = hma_series.iloc[-1] if not hma_series.empty else 0.0

    # Cálculo do VWAP
    vwap_series = calculate_vwap(df)
    latest_vwap = vwap_series.iloc[-1] if not vwap_series.empty else 0.0

    current_price = float(df['close'].iloc[-1])
    
    # Lógica de ativação (Preço acima da HMA e acima do VWAP)
    hma_active = bool(current_price > latest_hma) if latest_hma != 0 else False
    vwap_active = bool(current_price > latest_vwap) if latest_vwap != 0 else False

    # 3. Agora montamos o dicionário com todas as variáveis já definidas
    analysis_result = {
        'symbol': symbol,
        'name': coin_name,
        'price': current_price,
        'price_change_24h': 0.0,
        'volume_24h': 0.0,
        'market_cap': market_cap or 0,
        'rsi_value': 0.0,
        'rsi_signal': "N/A",
        'bollinger_signal': "Nenhum",
        'macd_signal': "Nenhum",
        'macd_value': 0.0,
        'macd_signal_line': 0.0,
        'macd_histogram': 0.0,
        'mme_cross': "Nenhum",
        'mme_200': 0.0,
        'hilo_signal': "Nenhum",
        'media_movel_cross': {},
        'hma': float(latest_hma),
        'hma_active': hma_active,
        'vwap': float(latest_vwap),
        'vwap_active': vwap_active,
        'timestamp': datetime.now().isoformat()
    }

    # 4. Preenchemos os dados extras do ticker
    symbol_ticker = ticker_data.get(symbol, {})
    analysis_result['price_change_24h'] = robust_services.DataValidator.safe_float(symbol_ticker.get('priceChangePercent'))
    analysis_result['volume_24h'] = robust_services.DataValidator.safe_float(symbol_ticker.get('quoteVolume'))

    # 5. Calculamos o restante dos indicadores antigos
    rsi_series, _, _ = calculate_rsi(df)
    upper_band_series, lower_band_series, _ = calculate_bollinger_bands(df)
    macd_signal, macd_value, macd_signal_line, macd_histogram = calculate_macd(df)
    _, _, hilo_signal = calculate_hilo_signals(df)
    emas = calculate_emas(df, periods=[50, 200])

    # Extração de valores do RSI e Bandas
    rsi_value = rsi_series.iloc[-1] if not rsi_series.empty and pd.notna(rsi_series.iloc[-1]) else 0.0
    upper_band = upper_band_series.iloc[-1] if not upper_band_series.empty and pd.notna(upper_band_series.iloc[-1]) else 0.0
    lower_band = lower_band_series.iloc[-1] if not lower_band_series.empty and pd.notna(lower_band_series.iloc[-1]) else 0.0

    analysis_result['hilo_signal'] = hilo_signal
    analysis_result['rsi_value'] = rsi_value
    analysis_result['rsi_signal'] = f"{rsi_value:.2f}" if rsi_value > 0 else "N/A"

    # Lógica de Bollinger
    if upper_band > 0 and analysis_result['price'] > 0:
        if analysis_result['price'] > upper_band:
            analysis_result['bollinger_signal'] = "Acima da Banda"
        elif analysis_result['price'] < lower_band:
            analysis_result['bollinger_signal'] = "Abaixo da Banda"

    analysis_result['macd_signal'] = macd_signal
    analysis_result['macd_value'] = macd_value
    analysis_result['macd_signal_line'] = macd_signal_line
    analysis_result['macd_histogram'] = macd_histogram

    # Lógica de Médias Móveis (MME 200 e Cruzamentos)
    if 200 in emas and not emas[200].empty and pd.notna(emas[200].iloc[-1]):
        analysis_result['mme_200'] = emas[200].iloc[-1]

    if 50 in emas and 200 in emas and len(emas[50]) > 1 and len(emas[200]) > 1:
        if emas[50].iloc[-2] < emas[200].iloc[-2] and emas[50].iloc[-1] > emas[200].iloc[-1]:
            analysis_result['mme_cross'] = "Cruz Dourada"
        elif emas[50].iloc[-2] > emas[200].iloc[-2] and emas[50].iloc[-1] < emas[200].iloc[-1]:
            analysis_result['mme_cross'] = "Cruz da Morte"

    for period in [17, 34, 72, 90, 100, 144, 200]:
        media_movel_signal = calculate_media_movel_cross(df, period=period)
        if media_movel_signal != "Nenhum":
            analysis_result['media_movel_cross'][period] = media_movel_signal

    # O único return deve ficar no FINAL da função
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
            triggered_alerts, updated_cooldowns = _check_and_trigger_alerts(symbol, alert_config, analysis_data, config)
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
        triggered_alerts, updated_cooldowns = _check_and_trigger_alerts(symbol, alert_config, analysis_data, config)
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