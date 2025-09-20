import plotly.graph_objects as go
import pandas as pd

def generate_chart(df, alerts):
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title_text="No data to display")
        fig.show()
        return

    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'],
                                           open=df['open'],
                                           high=df['high'],
                                           low=df['low'],
                                           close=df['close'],
                                           name='Price')])

    # Sort alerts by timestamp to handle overlaps systematically
    alerts.sort(key=lambda a: a['timestamp'])

    last_x_pos = None
    last_y_offset = -40

    for alert in alerts:
        current_x_pos = alert['timestamp']
        ay_offset = -40

        # Check if the current alert is close in time to the last one
        if last_x_pos is not None:
            # Assuming timestamps are pandas Timestamps
            time_difference = pd.to_timedelta(current_x_pos - last_x_pos).total_seconds()
            # If alerts are within 6 hours of each other, alternate the y-offset
            if time_difference < 6 * 3600:
                ay_offset = last_y_offset - 30 if last_y_offset < -40 else -70

        fig.add_annotation(
            x=current_x_pos,
            y=alert['price'],
            text=alert['message'],
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=ay_offset,
            bgcolor="rgba(255, 255, 255, 0.7)",
            font=dict(
                family="sans-serif",
                size=12,
                color="#000000"
            ),
            align="center",
            bordercolor="#c7c7c7",
            borderwidth=2,
            borderpad=4,
        )

        fig.add_trace(go.Scatter(
            x=[current_x_pos],
            y=[alert['price']],
            mode='markers',
            marker=dict(
                color='red',
                size=10,
                symbol='triangle-down' if 'venda' in alert['message'].lower() else 'triangle-up'
            ),
            showlegend=False
        ))

        last_x_pos = current_x_pos
        last_y_offset = ay_offset


    fig.update_layout(
        title_text="Backtest Results",
        xaxis_rangeslider_visible=False,
        template='plotly_dark'
    )

    fig.show()
