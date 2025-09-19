import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def generate_chart(df, alerts):
    if df.empty:
        return go.Figure()

    fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.1)

    fig.add_trace(go.Candlestick(x=df.index,
                                open=df['Open'],
                                high=df['High'],
                                low=df['Low'],
                                close=df['Close'],
                                name='trace 0'),
                  row=1, col=1)

    alert_points = df.loc[df.index.isin(alerts)]
    fig.add_trace(go.Scatter(x=alert_points.index,
                             y=alert_points['High'] * 1.05,  # Posição um pouco acima da vela
                             mode='markers',
                             marker=dict(color='red', size=10, symbol='triangle-up'),
                             name='Alerts'),
                  row=1, col=1)

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        showlegend=True,
        template='plotly_dark'
    )
    return fig

def fig_to_base64(fig):
    return fig.to_image(format="png")
