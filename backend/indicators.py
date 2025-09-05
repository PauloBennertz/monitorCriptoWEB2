import pandas as pd
import numpy as np

def calculate_sma(series, period):
    """Calculates the Simple Moving Average (SMA) for a data series.

    Args:
        series (pd.Series): The data series.
        period (int): The period for the SMA.

    Returns:
        pd.Series: The SMA series.
    """
    return series.rolling(window=period).mean()

def calculate_ema(series, period):
    """Calculates the Exponential Moving Average (EMA) for a data series.

    Args:
        series (pd.Series): The data series.
        period (int): The period for the EMA.

    Returns:
        pd.Series: The EMA series.
    """
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(df, period=14):
    """Calculates the Relative Strength Index (RSI) for a DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame with the price data.
        period (int, optional): The period for the RSI. Defaults to 14.

    Returns:
        tuple: A tuple containing the RSI, average gain, and average loss.
    """
    if df is None or df.empty or len(df) < period + 1: return 0, 0, 0
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    avg_gain, avg_loss = gain.iloc[-1], loss.iloc[-1]
    if pd.isna(avg_loss) or avg_loss == 0: return 100, avg_gain if not pd.isna(avg_gain) else 0, 0
    if pd.isna(avg_gain): return 0, 0, avg_loss
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs)), avg_gain, avg_loss

def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Calculates the Bollinger Bands for a DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame with the price data.
        period (int, optional): The period for the Bollinger Bands.
            Defaults to 20.
        std_dev (int, optional): The number of standard deviations.
            Defaults to 2.

    Returns:
        tuple: A tuple containing the upper band, lower band, SMA, and
            standard deviation.
    """
    if df is None or df.empty or len(df) < period: return 0, 0, 0, 0
    sma = df['close'].rolling(window=period).mean().iloc[-1]
    std = df['close'].rolling(window=period).std().iloc[-1]
    if pd.isna(sma) or pd.isna(std): return 0, 0, sma, std
    return sma + (std * std_dev), sma - (std * std_dev), sma, std

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calculates the MACD (Moving Average Convergence Divergence) crossover signal.

    Args:
        df (pd.DataFrame): The DataFrame with the price data.
        fast (int, optional): The fast period for the MACD. Defaults to 12.
        slow (int, optional): The slow period for the MACD. Defaults to 26.
        signal (int, optional): The signal period for the MACD. Defaults to 9.

    Returns:
        str: The MACD crossover signal ("Cruzamento de Alta",
            "Cruzamento de Baixa", "Nenhum", or "N/A").
    """
    if df is None or len(df) < slow + signal: return "N/A"
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    if len(macd) < 2 or len(signal_line) < 2: return "Nenhum"
    if macd.iloc[-2] < signal_line.iloc[-2] and macd.iloc[-1] > signal_line.iloc[-1]: return "Cruzamento de Alta"
    if macd.iloc[-2] > signal_line.iloc[-2] and macd.iloc[-1] < signal_line.iloc[-1]: return "Cruzamento de Baixa"
    return "Nenhum"

def calculate_emas(df, periods=[50, 200]):
    """Calculates the Exponential Moving Averages (EMAs) for a list of periods.

    Args:
        df (pd.DataFrame): The DataFrame with the price data.
        periods (list, optional): A list of periods for the EMAs.
            Defaults to [50, 200].

    Returns:
        dict: A dictionary of EMAs for each period.
    """
    emas = {}
    if df is None or df.empty: return emas
    for period in periods:
        if len(df) >= period: emas[period] = df['close'].ewm(span=period, adjust=False).mean()
    return emas

def calculate_hilo_signals(df, length=34, ma_type="EMA", offset=0, simple_hilo=True):
    """Calculates the HiLo indicator signals translated from Pine Script.

    Args:
        df (pd.DataFrame): The DataFrame with the price data.
        length (int, optional): The period for the HiLo indicator.
            Defaults to 34.
        ma_type (str, optional): The type of moving average to use ("EMA"
            or "SMA"). Defaults to "EMA".
        offset (int, optional): The offset for the moving averages.
            Defaults to 0.
        simple_hilo (bool, optional): Whether to use the simple HiLo
            logic. Defaults to True.

    Returns:
        A tuple (buy_signal, sell_signal, signal_text) where the signal
            is True or False.
    """
    if df is None or df.empty or len(df) < length + offset + 1:
        return False, False, None

    if ma_type == "EMA":
        hima = calculate_ema(df['high'], length).shift(offset)
        loma = calculate_ema(df['low'], length).shift(offset)
    else: # "SMA"
        hima = calculate_sma(df['high'], length).shift(offset)
        loma = calculate_sma(df['low'], length).shift(offset)

    # Lógica de "crossover" e "crossunder"
    # Buy signal: close crosses above hima (the high moving average)
    buy_signal = (df['close'].iloc[-2] <= hima.iloc[-2]) and (df['close'].iloc[-1] > hima.iloc[-1])

    # Sell signal: close crosses below loma (the low moving average)
    sell_signal = (df['close'].iloc[-2] >= loma.iloc[-2]) and (df['close'].iloc[-1] < loma.iloc[-1])

    return buy_signal, sell_signal, "HiLo Buy" if buy_signal else ("HiLo Sell" if sell_signal else "Nenhum")