import pandas as pd
import numpy as np
import pandas_ta as ta


def calculate_sma(series, period):
    """Calcula a Média Móvel Simples (SMA) para uma série de dados."""
    return series.rolling(window=period).mean()

def calculate_ema(series, period):
    """Calcula a Média Móvel Exponencial (EMA) para uma série de dados."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(df, period=14):
    """Calcula o Índice de Força Relativa (RSI) para um DataFrame."""
    if df is None or df.empty or len(df) < period + 1:
        return pd.Series(np.nan, index=df.index), 0, 0

    # Use pandas_ta for a reliable RSI calculation with Wilder's smoothing (the default)
    rsi_series = ta.rsi(df['close'], length=period)

    # pandas_ta doesn't directly return avg_gain and avg_loss,
    # so we'll return 0,0 as placeholders.
    # The primary purpose of this function is the RSI series itself.
    return rsi_series, 0, 0

def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Calcula as Bandas de Bollinger para um DataFrame, retornando Series."""
    if df is None or df.empty or len(df) < period:
        # Retorna Series vazias ou com NaNs do mesmo tamanho do df de entrada
        nan_series = pd.Series(np.nan, index=df.index)
        return nan_series, nan_series, nan_series

    # Calcula a Média Móvel Simples
    sma = df['close'].rolling(window=period, min_periods=1).mean()

    # Calcula o Desvio Padrão
    std = df['close'].rolling(window=period, min_periods=1).std()

    # Calcula as bandas superior e inferior
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)

    return upper_band, lower_band, sma

def calculate_macd(df, fast=12, slow=26, signal=9, return_series=False):
    """
    Calcula o sinal de cruzamento do MACD (Convergência/Divergência de Médias Móveis).
    Se return_series=True, retorna uma Pandas Series com os sinais para todo o histórico.
    Para monitoramento ao vivo (return_series=False), retorna uma tupla contendo:
    (sinal_string, valor_macd, valor_linha_sinal, valor_histograma)
    """
    if df is None or len(df) < slow + signal:
        if return_series:
            return pd.Series("Nenhum", index=df.index)
        else:
            return "N/A", 0, 0, 0
        
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line

    # LÓGICA CORRIGIDA PARA HISTÓRICO
    if return_series:
        signals = pd.Series("Nenhum", index=df.index)
        # MACD Crossover logic for the entire series
        high_cross = (macd.shift(1) < signal_line.shift(1)) & (macd > signal_line)
        signals.loc[high_cross] = "Cruzamento de Alta"
        low_cross = (macd.shift(1) > signal_line.shift(1)) & (macd < signal_line)
        signals.loc[low_cross] = "Cruzamento de Baixa"
        return signals

    # LÓGICA PARA MONITORAMENTO AO VIVO
    signal_str = "Nenhum"
    if len(macd) >= 2 and len(signal_line) >= 2:
        if macd.iloc[-2] < signal_line.iloc[-2] and macd.iloc[-1] > signal_line.iloc[-1]:
            signal_str = "Cruzamento de Alta"
        elif macd.iloc[-2] > signal_line.iloc[-2] and macd.iloc[-1] < signal_line.iloc[-1]:
            signal_str = "Cruzamento de Baixa"

    # Retorna os valores mais recentes
    latest_macd = macd.iloc[-1] if not macd.empty else 0
    latest_signal_line = signal_line.iloc[-1] if not signal_line.empty else 0
    latest_histogram = histogram.iloc[-1] if not histogram.empty else 0

    return signal_str, latest_macd, latest_signal_line, latest_histogram

def calculate_emas(df, periods=[50, 200]):
    """Calcula as Médias Móveis Exponenciais (EMAs) para uma lista de períodos."""
    emas = {}
    if df is None or df.empty: return emas
    for period in periods:
        if len(df) >= period: emas[period] = df['close'].ewm(span=period, adjust=False).mean()
    return emas

def calculate_hilo_signals(df, length=34, ma_type="EMA", offset=0, simple_hilo=True, return_series=False):
    """
    Calcula os sinais do indicador HiLo traduzido do Pine Script.
    Retorna uma tupla (sinal_compra_bool, sinal_venda_bool, sinal_string_ou_series).
    """
    if df is None or df.empty or len(df) < length + offset + 1:
        signal_output = pd.Series("Nenhum", index=df.index) if return_series else None
        return False, False, signal_output

    if ma_type == "EMA":
        hima = calculate_ema(df['high'], length).shift(offset)
        loma = calculate_ema(df['low'], length).shift(offset)
    else: # "SMA"
        hima = calculate_sma(df['high'], length).shift(offset)
        loma = calculate_sma(df['low'], length).shift(offset)

    # Lógica de "crossover" e "crossunder" para toda a série
    buy_signals_series = (df['close'].shift(1) <= hima.shift(1)) & (df['close'] > hima)
    sell_signals_series = (df['close'].shift(1) >= loma.shift(1)) & (df['close'] < loma)
    
    # LÓGICA CORRIGIDA PARA HISTÓRICO
    if return_series:
        signals = pd.Series("Nenhum", index=df.index)
        signals.loc[buy_signals_series] = "HiLo Buy"
        signals.loc[sell_signals_series] = "HiLo Sell"
        return buy_signals_series, sell_signals_series, signals

    # LÓGICA ORIGINAL PARA MONITORAMENTO AO VIVO (PRESERVADA)
    # Buy signal: close crosses above hima (the high moving average)
    buy_signal = buy_signals_series.iloc[-1] if not buy_signals_series.empty else False

    # Sell signal: close crosses below loma (the low moving average)
    sell_signal = sell_signals_series.iloc[-1] if not sell_signals_series.empty else False

    return buy_signal, sell_signal, "HiLo Buy" if buy_signal else ("HiLo Sell" if sell_signal else "Nenhum")

def calculate_media_movel_cross(df, period=17, return_series=False):
    """
    Calcula o cruzamento do preço com uma Média Móvel Exponencial (EMA).
    Se return_series=True, retorna uma Pandas Series com os sinais para todo o histórico.
    """
    if df is None or len(df) < period + 1:
        return pd.Series("Nenhum", index=df.index) if return_series else "Nenhum"

    ema = calculate_ema(df['close'], period)

    # Lógica de "crossover" e "crossunder" para toda a série
    high_cross = (df['close'].shift(1) <= ema.shift(1)) & (df['close'] > ema)
    low_cross = (df['close'].shift(1) >= ema.shift(1)) & (df['close'] < ema)

    if return_series:
        signals = pd.Series("Nenhum", index=df.index)
        signals.loc[high_cross] = "Cruzamento de Alta"
        signals.loc[low_cross] = "Cruzamento de Baixa"
        return signals

    # Lógica para monitoramento ao vivo
    if len(df['close']) < 2 or len(ema) < 2:
        return "Nenhum"

    if high_cross.iloc[-1]:
        return "Cruzamento de Alta"
    if low_cross.iloc[-1]:
        return "Cruzamento de Baixa"

    return "Nenhum"

def calculate_hma(series, period):
    """
    Calcula a Hull Moving Average (HMA).
    A HMA resolve o problema de atraso das médias móveis comuns.
    """
    if len(series) < period:
        return pd.Series(np.nan, index=series.index)
    
    # Cálculo da HMA: WMA(2*WMA(n/2) - WMA(n)), sqrt(n))
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    
    def wma(s, p):
        return s.rolling(window=p).apply(lambda x: np.dot(x, np.arange(1, p + 1)) / np.arange(1, p + 1).sum(), raw=True)
    
    wma_half = wma(series, half_length)
    wma_full = wma(series, period)
    
    diff = 2 * wma_half - wma_full
    hma = wma(diff, sqrt_length)
    
    return hma

def calculate_vwap(df):
    """
    Calcula o VWAP (Volume Weighted Average Price).
    Mostra o preço médio ponderado pelo volume.
    """
    # Garante que os dados são numéricos
    v = df['volume'].astype(float)
    p = df['close'].astype(float)
    
    # O VWAP acumulado é a soma de (Preço * Volume) / Soma do Volume
    return (p * v).cumsum() / v.cumsum()