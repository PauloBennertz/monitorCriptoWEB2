import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# We need to import the indicator calculation functions to use them here
from backend.indicators import calculate_bollinger_bands, calculate_emas

def get_signal_properties(signal_message):
    """
    Determines the properties for a signal annotation based on its message.
    Returns a tuple of (color, symbol, position).
    """
    # --- Define which signals are 'buy' (up arrow below price) ---
    buy_signals = [
        "Cruzamento de Alta (MACD)",
        "Cruz Dourada (MME 50/200)",
        "Sinal de Compra (HiLo)",
        "Preco Abaixo da Banda Bollinger",
        "RSI Sobrevenda"
    ]
    # --- Define which signals are 'sell' (down arrow above price) ---
    sell_signals = [
        "Cruzamento de Baixa (MACD)",
        "Cruz da Morte (MME 50/200)",
        "Sinal de Venda (HiLo)",
        "Preco Acima da Banda Bollinger",
        "RSI Sobrecompra"
    ]

    for signal in buy_signals:
        if signal in signal_message:
            return 'green', 'arrow-up', 'bottom'

    for signal in sell_signals:
        if signal in signal_message:
            return 'red', 'arrow-down', 'top'

    return 'blue', 'circle', 'middle' # Default for unknown signals

def generate_chart(df: pd.DataFrame, signals: list):
    """
    Generates and displays a candlestick chart with trading signals and indicators.

    Args:
        df (pd.DataFrame): DataFrame with historical price data.
        signals (list): A list of dictionaries, each representing a trading signal.
                        Expected keys: 'timestamp', 'message', 'price'.
    """
    fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.1)

    # 1. Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Preço'
    ), row=1, col=1)

    # 2. Calculate and add Bollinger Bands
    df['bb_upper'], df['bb_lower'], df['bb_ma'], _ = df.apply(
        lambda row: calculate_bollinger_bands(df.loc[:row.name]), axis=1, result_type='expand'
    ).T
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_upper'], name='Banda Superior', line=dict(color='cyan', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_lower'], name='Banda Inferior', line=dict(color='cyan', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_ma'], name='Média Móvel (BB)', line=dict(color='yellow', width=1, dash='dash')))


    # 3. Calculate and add EMAs
    emas = calculate_emas(df, periods=[50, 200])
    if 50 in emas:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=emas[50], name='MME 50', line=dict(color='orange', width=2)))
    if 200 in emas:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=emas[200], name='MME 200', line=dict(color='purple', width=2)))

    # 4. Add annotations for each signal
    for signal in signals:
        timestamp = signal['timestamp']
        message = signal['message']
        price = signal['price']

        color, symbol, position = get_signal_properties(message)

        if position == 'bottom':
            y_anchor = df.loc[df['timestamp'] == timestamp, 'low'].values[0]
            yshift = -10
        elif position == 'top':
            y_anchor = df.loc[df['timestamp'] == timestamp, 'high'].values[0]
            yshift = 10
        else: # middle
            y_anchor = price
            yshift = 0

        fig.add_annotation(
            x=timestamp,
            y=y_anchor,
            yshift=yshift,
            text="", # No text, just the arrow
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor=color,
            ax=0,
            ay= -30 if position == 'bottom' else 30, # Arrow direction
            hovertext=message, # Show signal message on hover
            font=dict(
                family="Courier New, monospace",
                size=12,
                color="#ffffff"
            ),
            align="center",
            bordercolor="#c7c7c7",
            borderwidth=1,
            borderpad=4,
            bgcolor=color,
            opacity=0.8
        )


    fig.update_layout(
        title='Análise de Backtest com Sinais de Trading',
        yaxis_title='Preço (USDT)',
        xaxis_title='Data',
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=700,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Display the chart in a new window
    fig.show()
