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
    using an efficient vectorized approach.
    """
    logging.info(f"Starting historical alert analysis for {symbol} from {start_date} to {end_date}.")

    historical_df = fetch_historical_data(symbol, start_date, end_date, interval='1h')
    if historical_df.empty:
        logging.warning(f"No historical data found for {symbol} in the given date range.")
        return []

    conditions = alert_config.get('conditions', {})
    all_alerts = []

    # --- 1. Calculate all indicators at once ---
    rsi_series, _, _ = calculate_rsi(historical_df)
    upper_band, lower_band, _ = calculate_bollinger_bands(historical_df)
    macd_cross_series = calculate_macd(historical_df, return_series=True)
    emas = calculate_emas(historical_df, periods=[50, 200])
    _, _, hilo_signal_series = calculate_hilo_signals(historical_df, return_series=True)

    # --- 2. Define a helper to process triggers ---
    def process_triggers(mask, condition_key_template, message_template):
        triggered_points = historical_df.loc[mask]
        for timestamp, row in triggered_points.iterrows():
            # Allow formatting with period if applicable
            period = getattr(row, 'period', '')
            condition_key = condition_key_template.format(period=period)
            message = message_template.format(price=row['close'], rsi=rsi_series.loc[timestamp], period=period)

            all_alerts.append({
                "timestamp": timestamp.isoformat(),
                "symbol": symbol,
                "condition": condition_key,
                "description": message,
                "snapshot": {"price": row['close']},
            })

    # --- 3. Generate and process triggers for each condition ---
    if conditions.get('rsi_sobrevendido', {}).get('enabled'):
        mask = rsi_series <= conditions.get('rsi_sobrevendido', {}).get('value', 30)
        process_triggers(mask, 'rsi_sobrevendido', "RSI em Sobrevenda ({rsi:.2f})")

    if conditions.get('rsi_sobrecomprado', {}).get('enabled'):
        mask = rsi_series >= conditions.get('rsi_sobrecomprado', {}).get('value', 70)
        process_triggers(mask, 'rsi_sobrecomprado', "RSI em Sobrecompra ({rsi:.2f})")

    if conditions.get('bollinger_abaixo', {}).get('enabled'):
        process_triggers(historical_df['close'] < lower_band, 'bollinger_abaixo', "Preço Abaixo da Banda de Bollinger")

    if conditions.get('bollinger_acima', {}).get('enabled'):
        process_triggers(historical_df['close'] > upper_band, 'bollinger_acima', "Preço Acima da Banda de Bollinger")

    if conditions.get('macd_cruz_alta', {}).get('enabled'):
        process_triggers(macd_cross_series == "Cruzamento de Alta", 'macd_cruz_alta', "MACD: Cruzamento de Alta")

    if conditions.get('macd_cruz_baixa', {}).get('enabled'):
        process_triggers(macd_cross_series == "Cruzamento de Baixa", 'macd_cruz_baixa', "MACD: Cruzamento de Baixa")

    if 50 in emas and 200 in emas:
        if conditions.get('mme_cruz_dourada', {}).get('enabled'):
            mask = (emas[50].shift(1) < emas[200].shift(1)) & (emas[50] > emas[200])
            process_triggers(mask, 'mme_cruz_dourada', "MME: Cruz Dourada (50/200)")
        if conditions.get('mme_cruz_morte', {}).get('enabled'):
            mask = (emas[50].shift(1) > emas[200].shift(1)) & (emas[50] < emas[200])
            process_triggers(mask, 'mme_cruz_morte', "MME: Cruz da Morte (50/200)")

    if conditions.get('hilo_compra', {}).get('enabled'):
        process_triggers(hilo_signal_series == "HiLo Buy", 'hilo_compra', "HiLo: Sinal de Compra")
    if conditions.get('hilo_venda', {}).get('enabled'):
        process_triggers(hilo_signal_series == "HiLo Sell", 'hilo_venda', "HiLo: Sinal de Venda")

    mme_cross_periods = [17, 34, 72, 144]
    if conditions.get('media_movel_cima', {}).get('enabled'):
        for period in mme_cross_periods:
            series = calculate_media_movel_cross(historical_df, period=period, return_series=True)
            mask = series == "Cruzamento de Alta"
            # Add period to the df to access it in the helper
            historical_df['period'] = period
            process_triggers(mask, 'media_movel_cima_{period}', "Preço cruzou MME {period} para cima")

    if conditions.get('media_movel_baixo', {}).get('enabled'):
        for period in mme_cross_periods:
            series = calculate_media_movel_cross(historical_df, period=period, return_series=True)
            mask = series == "Cruzamento de Baixa"
            historical_df['period'] = period
            process_triggers(mask, 'media_movel_baixo_{period}', "Preço cruzou MME {period} para baixo")

    # --- 4. De-duplicate and sort final alerts ---
    if not all_alerts:
        return []

    alerts_df = pd.DataFrame(all_alerts).drop_duplicates(subset=['timestamp', 'description']).sort_values(by='timestamp')

    logging.info(f"Found {len(alerts_df)} potential alerts for {symbol}.")
    return alerts_df.to_dict('records')