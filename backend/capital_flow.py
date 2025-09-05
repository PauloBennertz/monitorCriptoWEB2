# capital_flow.py (VERSÃO FINAL E FUNCIONAL)

import pandas as pd
from robust_services import DataCache, BinanceRateLimiter
from pycoingecko import CoinGeckoAPI
import time

def get_categories_data(cg_client, data_cache, rate_limiter):
    """Gets a list of all categories from CoinGecko with detailed data.

    Args:
        cg_client (CoinGeckoAPI): The CoinGecko API client.
        data_cache (DataCache): The data cache.
        rate_limiter (BinanceRateLimiter): The rate limiter.

    Returns:
        list: A list of categories with detailed data.
    """
    cache_key = {'method': 'get_coins_categories'}
    categories_data = data_cache.get(cache_key, ttl=3600) # Cache de 1 hora
    if categories_data:
        print("Dados de categorias obtidos do cache.")
        return categories_data

    print("Buscando novas categorias da API...")
    rate_limiter.wait_if_needed()
    try:
        categories_data = cg_client.get_coins_categories()
        data_cache.set(cache_key, categories_data)
        return categories_data
    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        return None

def analyze_capital_flow(categories_df, config):
    """Analyzes and aggregates the capital flow by category.

    Args:
        categories_df (pd.DataFrame): The DataFrame with the categories data.
        config (dict): The configuration for the analysis.

    Returns:
        pd.DataFrame: The DataFrame with the analysis results.
    """
    print("\nAnalisando fluxo de capital por categoria...")
    analysis_config = config.get('market_analysis_config', {})
    top_n = analysis_config.get('top_n', 25)
    min_market_cap = analysis_config.get('min_market_cap', 50000000)

    # Colunas essenciais que esperamos da API
    required_cols = ['market_cap', 'volume_24h']
    for col in required_cols:
        if col not in categories_df.columns:
            print(f"ERRO CRÍTICO: A coluna essencial '{col}' não foi encontrada nos dados da API.")
            return pd.DataFrame()

    # Filtra categorias sem dados de market cap e com base no valor mínimo
    categories_df = categories_df[categories_df['market_cap'].notna()]
    filtered_categories = categories_df[categories_df['market_cap'] >= min_market_cap]

    # Ordena as categorias pelo market cap e pega as Top N
    top_categories = filtered_categories.nlargest(top_n, 'market_cap').copy()

    if top_categories.empty:
        return pd.DataFrame()

    # Formata os números para melhor leitura
    top_categories['market_cap_formatted'] = top_categories['market_cap'].apply(lambda x: f"${x/1_000_000_000:.2f}B" if x >= 1_000_000_000 else f"${x/1_000_000:.2f}M")
    top_categories['volume_24h_formatted'] = top_categories['volume_24h'].apply(lambda x: f"${x/1_000_000_000:.2f}B" if x >= 1_000_000_000 else f"${x/1_000_000:.2f}M")

    return top_categories

def print_results(results_df):
    """Prints the analysis results in a formatted way.

    Args:
        results_df (pd.DataFrame): The DataFrame with the analysis results.
    """
    if results_df.empty:
        print("\nNenhuma categoria atendeu aos critérios para exibição.")
        return

    print("\n--- Análise de Fluxo de Capital por Categoria (Top N) ---")
    print("-" * 80)

    # MUDANÇA: Cabeçalho sem a coluna "Variação (24h)"
    header = f"{'Rank':<5} {'Categoria':<35} {'Market Cap':>20} {'Volume (24h)':>20}"
    print(header)
    print("-" * 80)

    for index, row in results_df.iterrows():
        rank = row.get('rank', 'N/A')
        name = row.get('name', 'N/A')
        mcap_formatted = row.get('market_cap_formatted', 'N/A')
        vol_formatted = row.get('volume_24h_formatted', 'N/A')

        # MUDANÇA: Linha sem a coluna de variação e com espaçamento ajustado
        line = (f"{rank:<5} {name:<35} "
                f"{mcap_formatted:>20} "
                f"{vol_formatted:>20}")
        print(line)

    print("-" * 80)
    print("\nAnálise concluída.")

def run_full_analysis(config, cg_client: CoinGeckoAPI, data_cache_instance: DataCache, rate_limiter_instance: BinanceRateLimiter):
    """Runs the full capital flow analysis process.

    Args:
        config (dict): The configuration for the analysis.
        cg_client (CoinGeckoAPI): The CoinGecko API client.
        data_cache_instance (DataCache): The data cache.
        rate_limiter_instance (BinanceRateLimiter): The rate limiter.
    """
    start_time = time.time()

    categories_data = get_categories_data(cg_client, data_cache_instance, rate_limiter_instance)
    if categories_data is None:
        print("Não foi possível obter os dados das categorias. Abortando análise.")
        return

    categories_df = pd.DataFrame(categories_data)
    # Adiciona o 'rank' para manter a ordem da API (que é por market cap)
    if 'rank' not in categories_df.columns:
      categories_df['rank'] = range(1, len(categories_df) + 1)

    analysis_results = analyze_capital_flow(categories_df, config)

    print_results(analysis_results)

    end_time = time.time()
    print(f"\nTempo total da análise: {end_time - start_time:.2f} segundos.")