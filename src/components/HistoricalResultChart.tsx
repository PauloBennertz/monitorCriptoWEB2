import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';

interface HistoricalResultChartProps {
  symbol: string;
  startDate: string;
  endDate: string;
  alerts: any[]; // Alerts from the analysis
}

const HistoricalResultChart: React.FC<HistoricalResultChartProps> = ({ symbol, startDate, endDate, alerts }) => {
  const [priceData, setPriceData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPriceData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const query = new URLSearchParams({ symbol, start_date: startDate, end_date: endDate });
        const response = await fetch(`http://localhost:8000/api/historical_data?${query.toString()}`);
        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || 'Failed to fetch historical price data.');
        }
        const data = await response.json();
        setPriceData(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPriceData();
  }, [symbol, startDate, endDate]);

  if (isLoading) {
    return <div>Loading chart data...</div>;
  }

  if (error) {
    return <div style={{ color: 'red' }}>Error loading chart: {error}</div>;
  }

  // Prepare data for Plotly
  const trace = {
    x: priceData.map(d => d.timestamp),
    close: priceData.map(d => d.close),
    high: priceData.map(d => d.high),
    low: priceData.map(d => d.low),
    open: priceData.map(d => d.open),
    type: 'candlestick',
    name: symbol,
  };

  // Prepare annotations for alerts
  const annotations = alerts.map(alert => ({
    x: alert.timestamp,
    y: alert.price,
    yref: 'y',
    text: alert.condition.substring(0, 3), // Short text for the marker
    hovertext: alert.description,
    showarrow: true,
    arrowhead: 2,
    ax: 0,
    ay: -30,
    bgcolor: 'rgba(255, 0, 0, 0.6)',
    font: { color: 'white', size: 10 },
    borderpad: 2,
  }));

  return (
    <Plot
      data={[trace]}
      layout={{
        title: `Preços Históricos e Alertas para ${symbol}`,
        xaxis: {
          title: 'Data',
          type: 'date',
          rangeslider: { visible: false },
        },
        yaxis: { title: 'Preço (USD)' },
        annotations: annotations,
        paper_bgcolor: '#2c2c2c',
        plot_bgcolor: '#2c2c2c',
        font: {
          color: '#fff'
        }
      }}
      style={{ width: '100%', height: '500px' }}
      config={{ responsive: true }}
    />
  );
};

export default HistoricalResultChart;