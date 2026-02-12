from datetime import timedelta
import pandas as pd
import logging
from .data_fetcher import fetch_historical_data
from .indicators import (
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_macd,
    calculate_emas,
    calculate_hilo_signals,
    calculate_media_movel_cross,
    calculate_hma, 
    calculate_vwap,
)

logging.basicConfig(level=logging.INFO)


async def analyze_historical_alerts(symbol: str, start_date: str, end_date: str, alert_config: dict, timeframes_config: dict = None, interval: str = '1h', parameters: dict = None):
    """
    Analyzes historical data for a symbol to find when alert conditions would have been met,
    using a highly efficient and vectorized pandas approach.
    """
    logging.info(f"Starting vectorized historical alert analysis for {symbol} from {start_date} to {end_date} with interval {interval}.")

    if parameters is None:
        parameters = {}

    # Extract parameters with defaults
    rsi_period = parameters.get('rsi_period', 14)
    rsi_overbought = parameters.get('rsi_overbought', 75)
    rsi_oversold = parameters.get('rsi_oversold', 30)

    macd_fast = parameters.get('macd_fast', 12)
    macd_slow = parameters.get('macd_slow', 26)
    macd_signal = parameters.get('macd_signal', 9)

    bb_period = parameters.get('bb_period', 20)
    bb_std = parameters.get('bb_std', 2.0)

    historical_df = await fetch_historical_data(symbol, start_date, end_date, interval=interval)
    if historical_df.empty:
        logging.warning(f"No historical data found for {symbol} in the given date range.")
        return [], pd.DataFrame()

    conditions = alert_config.get('conditions', {})
    alert_dfs = [] # List to hold DataFrames of alerts for each condition

    # --- 1. Calculate all indicators at once ---
    rsi_series = calculate_rsi(historical_df, period=rsi_period)[0]
    upper_band, lower_band, _ = calculate_bollinger_bands(historical_df, period=bb_period, std_dev=bb_std)
    macd_cross_series = calculate_macd(historical_df, fast=macd_fast, slow=macd_slow, signal=macd_signal, return_series=True)
    emas = calculate_emas(historical_df, periods=[50, 200])
    hilo_signal_series = calculate_hilo_signals(historical_df, return_series=True)[2]
    hma_series = calculate_hma(historical_df['close'], period=21)
    vwap_series = calculate_vwap(historical_df)

    # --- 2. Define a helper to create an alert DataFrame from a mask ---
    def create_alert_df(mask, condition_key, description_template):
        if mask.any():
            triggered_df = historical_df.loc[mask].copy()
            triggered_df['condition'] = condition_key
            # Handle potential formatting in description
            if '{rsi}' in description_template:
                rsi_values = rsi_series.loc[mask].map('{:.2f}'.format)
                triggered_df['description'] = [description_template.format(rsi=r) for r in rsi_values]
            elif '{period}' in description_template:
                 triggered_df['description'] = description_template.format(period=triggered_df.name)
            else:
                triggered_df['description'] = description_template
            return triggered_df
        return None

    # --- 3. Generate alerts for each condition ---
    # Use parameters from GUI if available, otherwise fallback to config or defaults

    if conditions.get('rsi_sobrevendido', {}).get('enabled'):
        mask = rsi_series <= rsi_oversold
        df = create_alert_df(mask, 'rsi_sobrevendido', 'RSI em Sobrevenda ({rsi})')
        if df is not None: alert_dfs.append(df)

    if conditions.get('rsi_sobrecomprado', {}).get('enabled'):
        mask = rsi_series >= rsi_overbought
        df = create_alert_df(mask, 'rsi_sobrecomprado', 'RSI em Sobrecompra ({rsi})')
        if df is not None: alert_dfs.append(df)

    if conditions.get('bollinger_abaixo', {}).get('enabled'):
        mask = historical_df['close'] < lower_band
        df = create_alert_df(mask, 'bollinger_abaixo', 'Preço Abaixo da Banda de Bollinger')
        if df is not None: alert_dfs.append(df)

    if conditions.get('bollinger_acima', {}).get('enabled'):
        mask = historical_df['close'] > upper_band
        df = create_alert_df(mask, 'bollinger_acima', 'Preço Acima da Banda de Bollinger')
        if df is not None: alert_dfs.append(df)

    if conditions.get('macd_cruz_alta', {}).get('enabled'):
        # MACD Buy Signal requires RSI < Oversold Threshold
        mask = (macd_cross_series == "Cruzamento de Alta") & (rsi_series < rsi_oversold)
        df = create_alert_df(mask, 'macd_cruz_alta', 'MACD: Cruzamento de Alta')
        if df is not None: alert_dfs.append(df)

    if conditions.get('macd_cruz_baixa', {}).get('enabled'):
        mask = macd_cross_series == "Cruzamento de Baixa"
        df = create_alert_df(mask, 'macd_cruz_baixa', 'MACD: Cruzamento de Baixa')
        if df is not None: alert_dfs.append(df)

    if 50 in emas and 200 in emas:
        if conditions.get('mme_cruz_dourada', {}).get('enabled'):
            mask = (emas[50].shift(1) < emas[200].shift(1)) & (emas[50] > emas[200])
            df = create_alert_df(mask, 'mme_cruz_dourada', 'MME: Cruz Dourada (50/200)')
            if df is not None: alert_dfs.append(df)
        if conditions.get('mme_cruz_morte', {}).get('enabled'):
            mask = (emas[50].shift(1) > emas[200].shift(1)) & (emas[50] < emas[200])
            df = create_alert_df(mask, 'mme_cruz_morte', 'MME: Cruz da Morte (50/200)')
            if df is not None: alert_dfs.append(df)

    if conditions.get('hilo_compra', {}).get('enabled'):
        mask = hilo_signal_series == "HiLo Buy"
        df = create_alert_df(mask, 'hilo_compra', 'HiLo: Sinal de Compra')
        if df is not None: alert_dfs.append(df)

    if conditions.get('hilo_venda', {}).get('enabled'):
        mask = hilo_signal_series == "HiLo Sell"
        df = create_alert_df(mask, 'hilo_venda', 'HiLo: Sinal de Venda')
        if df is not None: alert_dfs.append(df)

    mme_cross_periods = [17, 34, 72, 144]
    if conditions.get('media_movel_cima', {}).get('enabled'):
        for period in mme_cross_periods:
            series = calculate_media_movel_cross(historical_df, period=period, return_series=True)
            mask = series == "Cruzamento de Alta"
            df = create_alert_df(mask, f'media_movel_cima_{period}', f"Preço cruzou MME {period} para cima")
            if df is not None: alert_dfs.append(df)

    if conditions.get('media_movel_baixo', {}).get('enabled'):
        for period in mme_cross_periods:
            series = calculate_media_movel_cross(historical_df, period=period, return_series=True)
            mask = series == "Cruzamento de Baixa"
            df = create_alert_df(mask, f'media_movel_baixo_{period}', f"Preço cruzou MME {period} para baixo")
            if df is not None: alert_dfs.append(df)

    # --- 4. Combine, format, and de-duplicate all alerts ---
    if not alert_dfs:
        return [], historical_df

    final_alerts_df = pd.concat(alert_dfs).sort_index()
    final_alerts_df.reset_index(inplace=True) # make timestamp a column
    final_alerts_df.drop_duplicates(subset=['timestamp', 'description'], inplace=True)

    # Format the output to the expected list of dictionaries
    final_alerts_df['snapshot'] = final_alerts_df.apply(lambda row: {'price': row['close']}, axis=1)
    final_alerts_df['timestamp'] = final_alerts_df['timestamp'].apply(lambda x: x.isoformat())
    final_alerts_df['symbol'] = symbol

    output_columns = ['timestamp', 'symbol', 'condition', 'description', 'snapshot']

    result = final_alerts_df[output_columns].to_dict('records')

    logging.info(f"Found {len(result)} potential alerts for {symbol}.")

    # Convert result to DataFrame for hit rate calculation
    if result:
        alerts_df = pd.DataFrame(result)
        if timeframes_config is None:
            timeframes_config = {
                '15m': 15, '30m': 30, '1h': 60, '4h': 240, '24h': 1440
            }
        alerts_df = await calculate_hit_rate(alerts_df, symbol, timeframes_config)
        result = alerts_df.to_dict('records')

    return result, historical_df

SIGNAL_TYPE_MAPPING = {
    'rsi_sobrevendido': 'buy',
    'bollinger_abaixo': 'buy',
    'macd_cruz_alta': 'buy',
    'mme_cruz_dourada': 'buy',
    'hilo_compra': 'buy',
    'media_movel_cima': 'buy',
    # --- NOVOS SINAIS ADICIONADOS ---
    'hma_cruz_alta': 'buy',
    'vwap_cruz_alta': 'buy',

    'rsi_sobrecomprado': 'sell',
    'bollinger_acima': 'sell',
    'macd_cruz_baixa': 'sell',
    'mme_cruz_morte': 'sell',
    'hilo_venda': 'sell',
    'media_movel_baixo': 'sell',
    # --- NOVOS SINAIS ADICIONADOS ---
    'hma_cruz_baixa': 'sell',
    'vwap_cruz_baixa': 'sell',
}

async def calculate_hit_rate(alerts_df: pd.DataFrame, symbol: str, timeframes_config: dict):
    """
    Calculates the hit rate of alerts by analyzing price movements after each alert.
    Optimized to fetch future data in a single batch.
    """
    if alerts_df.empty:
        return alerts_df

    logging.info(f"Optimized hit rate calculation for {len(alerts_df)} alerts for {symbol}...")

    timeframes_minutes = timeframes_config

    # Initialize results columns
    for tf in timeframes_minutes.keys():
        alerts_df[f'hit_{tf}'] = None
        alerts_df[f'pct_change_{tf}'] = None

    alerts_df['timestamp'] = pd.to_datetime(alerts_df['timestamp'])

    # --- Optimization: Fetch all required future data in one go ---
    min_alert_time = alerts_df['timestamp'].min()
    max_alert_time = alerts_df['timestamp'].max()

    future_start_date = min_alert_time.strftime('%Y-%m-%d')
    future_end_date = (max_alert_time + timedelta(days=2)).strftime('%Y-%m-%d')

    logging.info(f"Fetching 1-minute data from {future_start_date} to {future_end_date} for analysis.")
    future_df = await fetch_historical_data(symbol, future_start_date, future_end_date, interval='1m')

    if future_df.empty:
        logging.warning("Could not fetch future data for hit rate analysis. Aborting and returning.")
        alerts_df['hit_rate_calculated'] = False
        return alerts_df

    alerts_df['hit_rate_calculated'] = True
    # --- End Optimization ---

    for index, alert in alerts_df.iterrows():
        alert_time = alert['timestamp']
        start_price = alert['snapshot']['price']
        condition = alert['condition']

        signal_type = next((stype for key, stype in SIGNAL_TYPE_MAPPING.items() if condition.startswith(key)), None)
        if not signal_type:
            continue

        for tf_name, tf_minutes in timeframes_minutes.items():
            future_time = alert_time + timedelta(minutes=tf_minutes)

            # Find the closest price point in the pre-fetched future data
            future_price_series = future_df[future_df.index >= future_time]

            if not future_price_series.empty:
                future_price = future_price_series.iloc[0]['close']
                pct_change = ((future_price - start_price) / start_price) * 100 if start_price != 0 else 0

                hit = (signal_type == 'buy' and pct_change > 0) or \
                      (signal_type == 'sell' and pct_change < 0)

                alerts_df.loc[index, f'hit_{tf_name}'] = hit
                alerts_df.loc[index, f'pct_change_{tf_name}'] = round(pct_change, 2)

    return alerts_df