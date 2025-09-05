import pandas as pd
import numpy as np

def calculate_sma(series, period):
    """Calcula a Média Móvel Simples (SMA) para uma série de dados."""
    return series.rolling(window=period).mean()

def calculate_ema(series, period):
    """Calcula a Média Móvel Exponencial (EMA) para uma série de dados."""
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(df, period=14):
    """Calcula o Índice de Força Relativa (RSI) para um DataFrame."""
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
    """Calcula as Bandas de Bollinger para um DataFrame."""
    if df is None or df.empty or len(df) < period: return 0, 0, 0, 0
    sma = df['close'].rolling(window=period).mean().iloc[-1]
    std = df['close'].rolling(window=period).std().iloc[-1]
    if pd.isna(sma) or pd.isna(std): return 0, 0, sma, std
    return sma + (std * std_dev), sma - (std * std_dev), sma, std

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calcula o sinal de cruzamento do MACD (Convergência/Divergência de Médias Móveis)."""
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
    """Calcula as Médias Móveis Exponenciais (EMAs) para uma lista de períodos."""
    emas = {}
    if df is None or df.empty: return emas
    for period in periods:
        if len(df) >= period: emas[period] = df['close'].ewm(span=period, adjust=False).mean()
    return emas

def calculate_hilo_signals(df, length=34, ma_type="EMA", offset=0, simple_hilo=True):
    """
    Calcula os sinais do indicador HiLo traduzido do Pine Script.
    Retorna uma tupla (sinal_compra, sinal_venda) onde o sinal é True ou False.
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