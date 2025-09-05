# token_movers.py (VERSÃO FINAL COM INJEÇÃO DE DEPENDÊNCIA)

import pandas as pd
from pycoingecko import CoinGeckoAPI
from robust_services import DataCache, BinanceRateLimiter
import logging # Importar logging para mensagens internas

def run_token_analysis(config, cg_client: CoinGeckoAPI, data_cache_instance: DataCache, rate_limiter_instance: BinanceRateLimiter):
    """Runs the analysis of top gainers and losers and returns the results.

    This uses the injected API, cache, and rate limiter instances.

    Args:
        config (dict): The configuration for the analysis.
        cg_client (CoinGeckoAPI): The CoinGecko API client.
        data_cache_instance (DataCache): The data cache instance.
        rate_limiter_instance (BinanceRateLimiter): The rate limiter
            instance.

    Returns:
        tuple: A tuple containing the top gainers, top losers, and a
            status message.
    """
    token_config = config.get('token_analysis_config', {})
    top_n = token_config.get('top_n', 20)
    min_market_cap = token_config.get('min_market_cap', 5000000)
    min_volume_24h = token_config.get('min_volume_24h', 500000)

    cg = cg_client
    data_cache = data_cache_instance
    rate_limiter = rate_limiter_instance

    if not cg:
        logging.error("Cliente CoinGecko não fornecido. Falha na conexão com a API.")
        raise ConnectionError("Falha na conexão com a API da CoinGecko. Cliente CoinGecko não fornecido.")

    cache_key_markets = {'method': 'get_coins_markets', 'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 250, 'page': 1}
    market_data = data_cache.get(cache_key_markets) # Tenta obter do cache

    if not market_data: # Se não estiver no cache, faz a requisição
        rate_limiter.wait_if_needed() # Aplica rate limiting
        try:
            market_data = cg.get_coins_markets(
                vs_currency='usd', order='market_cap_desc', per_page=250, page=1
            )
            if market_data: # Só cacheia se os dados não forem vazios
                data_cache.set(cache_key_markets, market_data)
        except Exception as e:
            logging.error(f"Erro ao buscar dados de mercado para Token Movers: {e}")
            return None, None, f"Erro ao buscar dados da API: {e}"

    if not market_data: # Verifica novamente se market_data está vazio após a tentativa de busca
        return None, None, "A API não retornou dados de mercado ou ocorreu um erro na busca."

    df = pd.DataFrame(market_data)
    required_cols = ['id', 'symbol', 'name', 'current_price', 'market_cap', 'total_volume', 'price_change_percentage_24h']

    # Garante que todas as colunas necessárias existem antes de prosseguir
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        error_msg = f"Dados da API incompletos. Faltam colunas: {missing_cols}"
        logging.error(error_msg)
        raise ValueError(error_msg)

    df = df[required_cols].copy() # Usar .copy() para evitar SettingWithCopyWarning
    df.dropna(inplace=True)

    initial_count = len(df)
    df_filtered = df[(df['market_cap'] >= min_market_cap) & (df['total_volume'] >= min_volume_24h)].copy() # Usar .copy()
    filtered_count = len(df_filtered)

    # Formata os números para o padrão brasileiro (ponto como separador de milhar)
    mcap_str = f"{min_market_cap:,.0f}".replace(',', '.')
    vol_str = f"{min_volume_24h:,.0f}".replace(',', '.')

    status_message = (f"Filtros Usados: Top {top_n}, Cap. Mínima ${mcap_str}, Vol. Mínimo (24h) ${vol_str}\n"
                      f"Resultado: {initial_count} tokens iniciais -> {filtered_count} tokens restantes após filtros.")

    if df_filtered.empty:
        return pd.DataFrame(), pd.DataFrame(), status_message + "\n\nNenhum token atende aos critérios de filtro definidos."

    top_gainers = df_filtered.nlargest(top_n, 'price_change_percentage_24h').copy()
    top_losers = df_filtered.nsmallest(top_n, 'price_change_percentage_24h').copy()

    return top_gainers, top_losers, status_message

# Para testes diretos (opcional) - Este bloco não será executado quando importado
if __name__ == "__main__":
    print("Este módulo não é destinado a ser executado diretamente sem injeção de dependências.")