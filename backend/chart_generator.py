import logging

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logging.warning("Plotly is not installed. The backtesting chart generation will be disabled.")

import pandas as pd
from backend.indicators import calculate_bollinger_bands, calculate_emas

def get_signal_properties(signal_message):
    """
    Determines the properties for a signal annotation based on its message.
    Returns a tuple of (color, symbol, position).
    """
    buy_signals = [
        "Cruzamento de Alta (MACD)", "Cruz Dourada (MME 50/200)", "Sinal de Compra (HiLo)",
        "Preco Abaixo da Banda Bollinger", "RSI Sobrevenda"
    ]
    sell_signals = [
        "Cruzamento de Baixa (MACD)", "Cruz da Morte (MME 50/200)", "Sinal de Venda (HiLo)",
        "Preco Acima da Banda Bollinger", "RSI Sobrecompra"
    ]

    if any(signal in signal_message for signal in buy_signals):
        return 'green', 'arrow-up', 'bottom'
    if any(signal in signal_message for signal in sell_signals):
        return 'red', 'arrow-down', 'top'
    return 'blue', 'circle', 'middle'

def generate_chart(df: pd.DataFrame, signals: list):
    """
    Generates and displays a candlestick chart with trading signals and indicators.
    Returns a JSON representation of the chart or an error message if Plotly is not available.
    """
    if not PLOTLY_AVAILABLE:
        return {
            "error": "Plotly is not installed.",
            "message": "The chart could not be generated because the 'plotly' library is missing. "
                       "Please install it to use the backtesting feature: pip install plotly"
        }

    fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.1)

    fig.add_trace(go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Preço'
    ), row=1, col=1)

    df['bb_upper'], df['bb_lower'], df['bb_ma'] = calculate_bollinger_bands(df, period=20, std_dev=2)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_upper'], name='Banda Superior', line=dict(color='cyan', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_lower'], name='Banda Inferior', line=dict(color='cyan', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_ma'], name='Média Móvel (BB)', line=dict(color='yellow', width=1, dash='dash')))

    emas = calculate_emas(df, periods=[50, 200])
    if 50 in emas:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=emas[50], name='MME 50', line=dict(color='orange', width=2)))
    if 200 in emas:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=emas[200], name='MME 200', line=dict(color='purple', width=2)))

    for signal in signals:
        timestamp = signal['timestamp']
        message = signal['message']

        # Ensure the timestamp from the signal exists in the dataframe's index (timestamp)
        if timestamp not in df['timestamp'].values:
            continue

        color, symbol, position = get_signal_properties(message)

        y_anchor_series = df.loc[df['timestamp'] == timestamp, 'low' if position == 'bottom' else 'high']
        if y_anchor_series.empty:
            continue
        y_anchor = y_anchor_series.values[0]

        yshift = -10 if position == 'bottom' else 10 if position == 'top' else 0

        fig.add_annotation(
            x=timestamp, y=y_anchor, yshift=yshift,
            text="", showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2,
            arrowcolor=color, ax=0, ay=-30 if position == 'bottom' else 30,
            hovertext=message, font=dict(family="Courier New, monospace", size=12, color="#ffffff"),
            align="center", bordercolor="#c7c7c7", borderwidth=1, borderpad=4,
            bgcolor=color, opacity=0.8
        )

    fig.update_layout(
        title='Análise de Backtest com Sinais de Trading',
        yaxis_title='Preço (USDT)',
        xaxis_title='Data',
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig.to_json()
