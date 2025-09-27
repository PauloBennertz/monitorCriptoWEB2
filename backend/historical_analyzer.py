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
    # RSI
    rsi_series, _, _ = calculate_rsi(historical_df)
    # Bollinger Bands
    upper_band, lower_band, _ = calculate_bollinger_bands(historical_df)
    # MACD
    macd_cross_series = calculate_macd(historical_df, return_series=True)
    # EMAs for Golden/Death Cross
    emas = calculate_emas(historical_df, periods=[50, 200])
    # HiLo
    _, _, hilo_signal_series = calculate_hilo_signals(historical_df, return_series=True)


    # --- Iterate through each candle to check for alerts ---
    for i in range(1, len(historical_df)):
        timestamp = historical_df.index[i]
        current_price = historical_df['close'].iloc[i]

        # Helper to create alert dictionary
        def create_alert(condition_key, message):
            return {
                "timestamp": timestamp.isoformat(),
                "symbol": symbol,
                "condition": condition_key,
                "description": message,
                "price": current_price,
            }

        # Check RSI alerts
        if 'rsi_sobrevendido' in conditions and conditions['rsi_sobrevendido']['enabled']:
            rsi_value = rsi_series.iloc[i]
            if rsi_value <= conditions['rsi_sobrevendido'].get('value', 30):
                msg = f"RSI em Sobrevenda ({rsi_value:.2f})"
                triggered_alerts.append(create_alert('rsi_sobrevendido', msg))

        if 'rsi_sobrecomprado' in conditions and conditions['rsi_sobrecomprado']['enabled']:
            rsi_value = rsi_series.iloc[i]
            if rsi_value >= conditions['rsi_sobrecomprado'].get('value', 70):
                msg = f"RSI em Sobrecompra ({rsi_value:.2f})"
                triggered_alerts.append(create_alert('rsi_sobrecomprado', msg))

        # Check Bollinger Bands alerts
        if 'bollinger_abaixo' in conditions and conditions['bollinger_abaixo']['enabled']:
            if current_price < lower_band.iloc[i]:
                triggered_alerts.append(create_alert('bollinger_abaixo', "Preço Abaixo da Banda de Bollinger"))

        if 'bollinger_acima' in conditions and conditions['bollinger_acima']['enabled']:
            if current_price > upper_band.iloc[i]:
                triggered_alerts.append(create_alert('bollinger_acima', "Preço Acima da Banda de Bollinger"))

        # Check MACD Cross alerts
        if 'macd_cruz_alta' in conditions and conditions['macd_cruz_alta']['enabled']:
            if macd_cross_series.iloc[i] == "Cruzamento de Alta":
                triggered_alerts.append(create_alert('macd_cruz_alta', "MACD: Cruzamento de Alta"))

        if 'macd_cruz_baixa' in conditions and conditions['macd_cruz_baixa']['enabled']:
            if macd_cross_series.iloc[i] == "Cruzamento de Baixa":
                triggered_alerts.append(create_alert('macd_cruz_baixa', "MACD: Cruzamento de Baixa"))

        # Check EMA Cross alerts (Golden/Death)
        if 'mme_cruz_dourada' in conditions and conditions['mme_cruz_dourada']['enabled']:
            # Golden Cross: short EMA crosses above long EMA
            if emas[50].iloc[i-1] < emas[200].iloc[i-1] and emas[50].iloc[i] > emas[200].iloc[i]:
                triggered_alerts.append(create_alert('mme_cruz_dourada', "MME: Cruz Dourada (50/200)"))

        if 'mme_cruz_morte' in conditions and conditions['mme_cruz_morte']['enabled']:
            # Death Cross: short EMA crosses below long EMA
            if emas[50].iloc[i-1] > emas[200].iloc[i-1] and emas[50].iloc[i] < emas[200].iloc[i]:
                triggered_alerts.append(create_alert('mme_cruz_morte', "MME: Cruz da Morte (50/200)"))

        # Check HiLo alerts
        if 'hilo_compra' in conditions and conditions['hilo_compra']['enabled']:
            if hilo_signal_series.iloc[i] == "HiLo Buy":
                triggered_alerts.append(create_alert('hilo_compra', "HiLo: Sinal de Compra"))

        if 'hilo_venda' in conditions and conditions['hilo_venda']['enabled']:
            if hilo_signal_series.iloc[i] == "HiLo Sell":
                triggered_alerts.append(create_alert('hilo_venda', "HiLo: Sinal de Venda"))


    logging.info(f"Found {len(triggered_alerts)} potential alerts for {symbol}.")
    return triggered_alerts