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
            logging.info(f"  -> ALERT TRIGGERED: {condition_key} at {timestamp} with price {current_price}")
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
            rsi_target = conditions['rsi_sobrevendido'].get('value', 30)
            logging.debug(f"[{timestamp}] Checking RSI Sobrevendido: Value={rsi_value:.2f}, Target=<={rsi_target}")
            if rsi_value <= rsi_target:
                msg = f"RSI em Sobrevenda ({rsi_value:.2f})"
                triggered_alerts.append(create_alert('rsi_sobrevendido', msg))

        if 'rsi_sobrecomprado' in conditions and conditions['rsi_sobrecomprado']['enabled']:
            rsi_value = rsi_series.iloc[i]
            rsi_target = conditions['rsi_sobrecomprado'].get('value', 70)
            logging.debug(f"[{timestamp}] Checking RSI Sobrecomprado: Value={rsi_value:.2f}, Target=>={rsi_target}")
            if rsi_value >= rsi_target:
                msg = f"RSI em Sobrecompra ({rsi_value:.2f})"
                triggered_alerts.append(create_alert('rsi_sobrecomprado', msg))

        # Check Bollinger Bands alerts
        if 'bollinger_abaixo' in conditions and conditions['bollinger_abaixo']['enabled']:
            bb_lower = lower_band.iloc[i]
            logging.debug(f"[{timestamp}] Checking Bollinger Abaixo: Price={current_price:.2f}, Lower Band={bb_lower:.2f}")
            if current_price < bb_lower:
                triggered_alerts.append(create_alert('bollinger_abaixo', "Preço Abaixo da Banda de Bollinger"))

        if 'bollinger_acima' in conditions and conditions['bollinger_acima']['enabled']:
            bb_upper = upper_band.iloc[i]
            logging.debug(f"[{timestamp}] Checking Bollinger Acima: Price={current_price:.2f}, Upper Band={bb_upper:.2f}")
            if current_price > bb_upper:
                triggered_alerts.append(create_alert('bollinger_acima', "Preço Acima da Banda de Bollinger"))

        # Check MACD Cross alerts
        if 'macd_cruz_alta' in conditions and conditions['macd_cruz_alta']['enabled']:
            macd_signal = macd_cross_series.iloc[i]
            logging.debug(f"[{timestamp}] Checking MACD Alta: Signal='{macd_signal}'")
            if macd_signal == "Cruzamento de Alta":
                triggered_alerts.append(create_alert('macd_cruz_alta', "MACD: Cruzamento de Alta"))

        if 'macd_cruz_baixa' in conditions and conditions['macd_cruz_baixa']['enabled']:
            macd_signal = macd_cross_series.iloc[i]
            logging.debug(f"[{timestamp}] Checking MACD Baixa: Signal='{macd_signal}'")
            if macd_signal == "Cruzamento de Baixa":
                triggered_alerts.append(create_alert('macd_cruz_baixa', "MACD: Cruzamento de Baixa"))

        # Check EMA Cross alerts (Golden/Death)
        if 'mme_cruz_dourada' in conditions and conditions['mme_cruz_dourada']['enabled']:
            ema_50_prev, ema_200_prev = emas[50].iloc[i-1], emas[200].iloc[i-1]
            ema_50_curr, ema_200_curr = emas[50].iloc[i], emas[200].iloc[i]
            logging.debug(f"[{timestamp}] Checking Golden Cross: Prev(50={ema_50_prev:.2f}, 200={ema_200_prev:.2f}), Curr(50={ema_50_curr:.2f}, 200={ema_200_curr:.2f})")
            if ema_50_prev < ema_200_prev and ema_50_curr > ema_200_curr:
                triggered_alerts.append(create_alert('mme_cruz_dourada', "MME: Cruz Dourada (50/200)"))

        if 'mme_cruz_morte' in conditions and conditions['mme_cruz_morte']['enabled']:
            ema_50_prev, ema_200_prev = emas[50].iloc[i-1], emas[200].iloc[i-1]
            ema_50_curr, ema_200_curr = emas[50].iloc[i], emas[200].iloc[i]
            logging.debug(f"[{timestamp}] Checking Death Cross: Prev(50={ema_50_prev:.2f}, 200={ema_200_prev:.2f}), Curr(50={ema_50_curr:.2f}, 200={ema_200_curr:.2f})")
            if ema_50_prev > ema_200_prev and ema_50_curr < ema_200_curr:
                triggered_alerts.append(create_alert('mme_cruz_morte', "MME: Cruz da Morte (50/200)"))

        # Check HiLo alerts
        if 'hilo_compra' in conditions and conditions['hilo_compra']['enabled']:
            hilo_signal = hilo_signal_series.iloc[i]
            logging.debug(f"[{timestamp}] Checking HiLo Compra: Signal='{hilo_signal}'")
            if hilo_signal == "HiLo Buy":
                triggered_alerts.append(create_alert('hilo_compra', "HiLo: Sinal de Compra"))

        if 'hilo_venda' in conditions and conditions['hilo_venda']['enabled']:
            hilo_signal = hilo_signal_series.iloc[i]
            logging.debug(f"[{timestamp}] Checking HiLo Venda: Signal='{hilo_signal}'")
            if hilo_signal == "HiLo Sell":
                triggered_alerts.append(create_alert('hilo_venda', "HiLo: Sinal de Venda"))


    logging.info(f"Found {len(triggered_alerts)} potential alerts for {symbol}.")
    return triggered_alerts