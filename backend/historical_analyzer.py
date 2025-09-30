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
    Analyzes historical data for a symbol to find when alert conditions would have been met.

    Args:
        symbol (str): The cryptocurrency symbol (e.g., 'BTCUSDT').
        start_date (str): The start date for analysis (YYYY-MM-DD).
        end_date (str): The end date for analysis (YYYY-MM-DD).
        alert_config (dict): A dictionary containing the alert conditions to check.

    Returns:
        list: A list of dictionaries, where each dictionary represents a triggered alert.
    """
    logging.info(f"Starting historical alert analysis for {symbol} from {start_date} to {end_date}.")

    # Fetch historical data
    historical_df = fetch_historical_data(symbol, start_date, end_date, interval='1h')
    if historical_df.empty:
        logging.warning(f"No historical data found for {symbol} in the given date range.")
        return []

    triggered_alerts = []
    conditions = alert_config.get('conditions', {})

    # --- Calculate all indicators at once for efficiency ---
    rsi_series, _, _ = calculate_rsi(historical_df)
    upper_band, lower_band, _ = calculate_bollinger_bands(historical_df)
    macd_cross_series = calculate_macd(historical_df, return_series=True)
    emas = calculate_emas(historical_df, periods=[50, 200])
    _, _, hilo_signal_series = calculate_hilo_signals(historical_df, return_series=True)

    # Calculate MME Cross signals if needed
    mme_cross_periods = [17, 34, 72, 144]
    mme_cross_signals = {}
    if conditions.get('media_movel_cima', {}).get('enabled') or conditions.get('media_movel_baixo', {}).get('enabled'):
        for period in mme_cross_periods:
            mme_cross_signals[period] = calculate_media_movel_cross(historical_df, period=period, return_series=True)

    # --- Iterate through each candle to check for alerts ---
    for i in range(1, len(historical_df)):
        timestamp = historical_df.index[i]
        current_price = historical_df['close'].iloc[i]

        # Helper to create alert dictionary with the correct 'snapshot' structure
        def create_alert(condition_key, message):
            logging.info(f"  -> ALERT TRIGGERED: {condition_key} at {timestamp} with price {current_price}")
            return {
                "timestamp": timestamp.isoformat(),
                "symbol": symbol,
                "condition": condition_key,
                "description": message,
                "snapshot": {"price": current_price},
            }

        # Check RSI alerts
        if conditions.get('rsi_sobrevendido', {}).get('enabled'):
            rsi_value = rsi_series.iloc[i]
            if rsi_value <= conditions.get('rsi_sobrevendido', {}).get('value', 30):
                triggered_alerts.append(create_alert('rsi_sobrevendido', f"RSI em Sobrevenda ({rsi_value:.2f})"))

        if conditions.get('rsi_sobrecomprado', {}).get('enabled'):
            rsi_value = rsi_series.iloc[i]
            if rsi_value >= conditions.get('rsi_sobrecomprado', {}).get('value', 70):
                triggered_alerts.append(create_alert('rsi_sobrecomprado', f"RSI em Sobrecompra ({rsi_value:.2f})"))

        # Check Bollinger Bands alerts
        if conditions.get('bollinger_abaixo', {}).get('enabled') and current_price < lower_band.iloc[i]:
            triggered_alerts.append(create_alert('bollinger_abaixo', "Preço Abaixo da Banda de Bollinger"))
        if conditions.get('bollinger_acima', {}).get('enabled') and current_price > upper_band.iloc[i]:
            triggered_alerts.append(create_alert('bollinger_acima', "Preço Acima da Banda de Bollinger"))

        # Check MACD Cross alerts
        if conditions.get('macd_cruz_alta', {}).get('enabled') and macd_cross_series.iloc[i] == "Cruzamento de Alta":
            triggered_alerts.append(create_alert('macd_cruz_alta', "MACD: Cruzamento de Alta"))
        if conditions.get('macd_cruz_baixa', {}).get('enabled') and macd_cross_series.iloc[i] == "Cruzamento de Baixa":
            triggered_alerts.append(create_alert('macd_cruz_baixa', "MACD: Cruzamento de Baixa"))

        # Check EMA Cross alerts (Golden/Death)
        if conditions.get('mme_cruz_dourada', {}).get('enabled'):
            if emas[50].iloc[i-1] < emas[200].iloc[i-1] and emas[50].iloc[i] > emas[200].iloc[i]:
                triggered_alerts.append(create_alert('mme_cruz_dourada', "MME: Cruz Dourada (50/200)"))
        if conditions.get('mme_cruz_morte', {}).get('enabled'):
            if emas[50].iloc[i-1] > emas[200].iloc[i-1] and emas[50].iloc[i] < emas[200].iloc[i]:
                triggered_alerts.append(create_alert('mme_cruz_morte', "MME: Cruz da Morte (50/200)"))

        # Check HiLo alerts
        if conditions.get('hilo_compra', {}).get('enabled') and hilo_signal_series.iloc[i] == "HiLo Buy":
            triggered_alerts.append(create_alert('hilo_compra', "HiLo: Sinal de Compra"))
        if conditions.get('hilo_venda', {}).get('enabled') and hilo_signal_series.iloc[i] == "HiLo Sell":
            triggered_alerts.append(create_alert('hilo_venda', "HiLo: Sinal de Venda"))

        # Check MME Cross alerts
        if conditions.get('media_movel_cima', {}).get('enabled'):
            for period, series in mme_cross_signals.items():
                if series.iloc[i] == "Cruzamento de Alta":
                    triggered_alerts.append(create_alert(f'media_movel_cima_{period}', f"Preço cruzou MME {period} para cima"))
        if conditions.get('media_movel_baixo', {}).get('enabled'):
            for period, series in mme_cross_signals.items():
                if series.iloc[i] == "Cruzamento de Baixa":
                    triggered_alerts.append(create_alert(f'media_movel_baixo_{period}', f"Preço cruzou MME {period} para baixo"))

    # De-duplicate and sort alerts
    unique_alerts = list({alert['description']: alert for alert in triggered_alerts}.values())
    sorted_alerts = sorted(unique_alerts, key=lambda x: x['timestamp'])

    logging.info(f"Found {len(sorted_alerts)} potential alerts for {symbol}.")
    return sorted_alerts