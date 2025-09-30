import pandas as pd
import logging
from .backtester import fetch_historical_data
from .indicators import (
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_macd,
    calculate_emas,
    calculate_hilo_signals,
    calculate_media_movel_cross,
)

logging.basicConfig(level=logging.INFO)


def analyze_historical_alerts(symbol: str, start_date: str, end_date: str, alert_config: dict):
    """
    Analyzes historical data for a symbol to find when alert conditions would have been met,
    using a highly efficient and vectorized pandas approach.
    """
    logging.info(f"Starting vectorized historical alert analysis for {symbol} from {start_date} to {end_date}.")

    historical_df = fetch_historical_data(symbol, start_date, end_date, interval='1h')
    if historical_df.empty:
        logging.warning(f"No historical data found for {symbol} in the given date range.")
        return []

    conditions = alert_config.get('conditions', {})
    alert_dfs = [] # List to hold DataFrames of alerts for each condition

    # --- 1. Calculate all indicators at once ---
    rsi_series = calculate_rsi(historical_df)[0]
    upper_band, lower_band, _ = calculate_bollinger_bands(historical_df)
    macd_cross_series = calculate_macd(historical_df, return_series=True)
    emas = calculate_emas(historical_df, periods=[50, 200])
    hilo_signal_series = calculate_hilo_signals(historical_df, return_series=True)[2]

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
    if conditions.get('rsi_sobrevendido', {}).get('enabled'):
        mask = rsi_series <= conditions.get('rsi_sobrevendido', {}).get('value', 30)
        df = create_alert_df(mask, 'rsi_sobrevendido', 'RSI em Sobrevenda ({rsi})')
        if df is not None: alert_dfs.append(df)

    if conditions.get('rsi_sobrecomprado', {}).get('enabled'):
        mask = rsi_series >= conditions.get('rsi_sobrecomprado', {}).get('value', 70)
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
        mask = macd_cross_series == "Cruzamento de Alta"
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
        return []

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
    return result