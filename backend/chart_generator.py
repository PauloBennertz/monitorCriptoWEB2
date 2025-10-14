import plotly.graph_objects as go
import pandas as pd
import plotly.io as pio

def _create_figure(df, alerts, symbol):
    """Função auxiliar para criar a figura base do gráfico, evitando duplicação de código."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title_text="Sem dados para exibir")
        return fig

    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                           open=df['open'],
                                           high=df['high'],
                                           low=df['low'],
                                           close=df['close'],
                                           name='Preço')])

    alerts.sort(key=lambda a: a['timestamp'])
    last_x_pos = None
    last_y_offset = -40

    for alert in alerts:
        current_x_pos = alert['timestamp']
        ay_offset = -40
        if last_x_pos is not None:
            time_difference = pd.to_timedelta(current_x_pos - last_x_pos).total_seconds()
            if time_difference < 6 * 3600:
                ay_offset = last_y_offset - 30 if last_y_offset < -40 else -70
        
        fig.add_annotation(
            x=current_x_pos, y=alert['price'], text=alert['message'], showarrow=True, arrowhead=1,
            ax=0, ay=ay_offset, bgcolor="rgba(255, 255, 255, 0.7)",
            font=dict(family="sans-serif", size=12, color="#000000"),
            align="center", bordercolor="#c7c7c7", borderwidth=2, borderpad=4,
        )
        fig.add_trace(go.Scatter(
            x=[current_x_pos], y=[alert['price']], mode='markers',
            marker=dict(
                color='red', size=10,
                symbol='triangle-down' if 'venda' in alert['message'].lower() or 'baixa' in alert['message'].lower() else 'triangle-up'
            ),
            showlegend=False
        ))
        last_x_pos = current_x_pos
        last_y_offset = ay_offset

    title_symbol = symbol if symbol else ''
    fig.update_layout(
        title_text=f"Resultados de Alertas para {title_symbol}",
        xaxis_rangeslider_visible=True, # Habilitado para melhor interatividade no HTML
        template='plotly_dark'
    )
    return fig

def generate_chart_image(df, alerts, output_path, symbol=None):
    """Gera um gráfico e o salva como uma imagem de ultra alta resolução."""
    fig = _create_figure(df, alerts, symbol)
    fig.update_layout(xaxis_rangeslider_visible=False) # Desabilitar para a imagem ficar mais limpa
    # Resolução 4K com escala 2x para garantir nitidez máxima no zoom
    fig.write_image(output_path, width=3840, height=2160, scale=2)
    print(f"Gráfico de ultra alta resolução salvo em: {output_path}")

def generate_interactive_chart_html(df, alerts, output_path, symbol=None):
    """Gera um gráfico e o salva como um arquivo HTML interativo."""
    fig = _create_figure(df, alerts, symbol)
    # Salva o gráfico como um arquivo HTML completo e independente
    pio.write_html(fig, file=output_path, auto_open=False, include_plotlyjs='cdn')
    print(f"Gráfico interativo salvo em: {output_path}")