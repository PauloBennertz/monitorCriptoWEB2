import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { CryptoData, Alert, API_BASE_URL } from '../types';
import { format } from 'date-fns';

interface CryptoDetailModalProps {
    coin: CryptoData;
    onClose: () => void;
}

// Updated interface to match the new API response
interface CoinDetail {
    alerts: Alert[];
    chartData: any;
    indicatorsData: { [key: string]: { x: string[], y: number[], name: string } };
    annotations: any[];
}

const CryptoDetailModal: React.FC<CryptoDetailModalProps> = ({ coin, onClose }) => {
    const [details, setDetails] = useState<CoinDetail | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFetchDetails = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE_URL}/api/coin_details/${coin.symbol}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch coin details');
            }
            const data: CoinDetail = await response.json();
            setDetails(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An unknown error occurred');
        } finally {
            setIsLoading(false);
        }
    };

    // Function to dynamically adjust annotation positions to avoid overlap
    const getAdjustedAnnotations = (annotations: any[], chartData: any) => {
        if (!annotations || annotations.length === 0) return [];

        let lastY = 0;
        let lastX = 0;
        const yOffset = (Math.max(...chartData.high) - Math.min(...chartData.low)) * 0.1; // 10% of price range

        return annotations.map((ann, index) => {
            let ay = -40; // Default vertical offset
            const currentX = new Date(ann.x).getTime();

            // If this annotation is close to the previous one, adjust its position
            if (index > 0 && Math.abs(currentX - lastX) < 3600 * 1000 * 6) { // 6 hours
                 // Alternate position
                ay = lastY > -60 ? -80 : -40;
            }

            lastY = ay;
            lastX = currentX;

            return {
                ...ann,
                ay: ay,
                yanchor: 'bottom',
                bgcolor: 'rgba(255, 255, 255, 0.85)',
                bordercolor: '#c7c7c7',
                borderwidth: 1,
                font: { color: '#000', size: 11 },
            };
        });
    };

    const chartLayout = {
        title: {
            text: `${coin.name} (${coin.symbol.replace('USDT', '')}) - Price and Indicators`,
            font: { color: '#f8f9fa', size: 20 },
            x: 0.5,
            xanchor: 'center',
        },
        paper_bgcolor: '#212529',
        plot_bgcolor: '#161a1d',
        font: { color: '#f8f9fa' },
        xaxis: {
            rangeslider: { visible: false },
            gridcolor: '#343a40',
            linecolor: '#495057',
            type: 'date',
        },
        yaxis: {
            title: 'Price (USD)',
            gridcolor: '#343a40',
            linecolor: '#495057',
            autorange: true,
            fixedrange: false // Allow zooming on y-axis
        },
        yaxis2: {
            title: 'RSI',
            overlaying: 'y',
            side: 'right',
            range: [0, 100],
            showgrid: false,
            zeroline: false,
            linecolor: '#6c757d',
            font: { color: '#6c757d' },
        },
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1,
            font: { color: '#f8f9fa' }
        },
        showlegend: true,
        autosize: true,
        // Use the adjusted annotations from the state
        annotations: details?.annotations && details.chartData ? getAdjustedAnnotations(details.annotations, details.chartData) : [],
    };

    const chartData = [];

    if (details?.chartData) {
        chartData.push({
            ...details.chartData,
            increasing: { line: { color: '#28a745', width: 2 } },
            decreasing: { line: { color: '#dc3545', width: 2 } },
            name: 'Price',
        });
    }

    if (details?.indicatorsData) {
        Object.values(details.indicatorsData).forEach(indicator => {
            if (indicator.name.includes('RSI')) {
                 chartData.push({
                    x: indicator.x,
                    y: indicator.y,
                    name: indicator.name,
                    type: 'scatter',
                    mode: 'lines',
                    yaxis: 'y2',
                    line: { color: '#ffc107', width: 1.5, dash: 'dot' }
                });
            } else {
                 chartData.push({
                    x: indicator.x,
                    y: indicator.y,
                    name: indicator.name,
                    type: 'scatter',
                    mode: 'lines',
                    line: { width: 1 }
                });
            }
        });
    }

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>{coin.name} ({coin.symbol.replace('USDT', '')})</h2>
                    <button onClick={onClose} className="close-button">&times;</button>
                </div>
                <div className="modal-body">
                    <div className="chart-area">
                        {isLoading && <div className="loading-container">Loading chart data...</div>}
                        {error && (
                            <div className="error-container">
                                <p>Error loading chart:</p>
                                <p><strong>{error}</strong></p>
                                <button onClick={handleFetchDetails} className="retry-button">Try Again</button>
                            </div>
                        )}
                        {details && chartData.length > 0 && (
                            <div className="chart-container">
                                <Plot
                                    data={chartData}
                                    layout={chartLayout}
                                    config={{ responsive: true, displaylogo: false }}
                                    style={{ width: '100%', height: '100%' }}
                                />
                            </div>
                        )}
                        {details && chartData.length === 0 && !isLoading && <p>No chart data available for this period.</p>}

                        {!isLoading && !error && !details && (
                            <div className="initial-chart-view">
                                <p>Click the button to generate the chart and view recent alerts.</p>
                                <button onClick={handleFetchDetails} className="generate-chart-button">
                                    Generate Chart
                                </button>
                            </div>
                        )}
                    </div>

                    {details && (
                         <div className="detail-section">
                            <h3>Recent Alerts (Last 7 Days)</h3>
                            <ul className="alert-list">
                                {details.alerts.length > 0 ? (
                                    details.alerts.map(alert => (
                                        <li key={alert.id}>
                                            <strong>{alert.condition.replace(/_/g, ' ')}</strong> - {format(new Date(alert.timestamp), 'dd/MM/yyyy HH:mm')}
                                            <small>Price: ${alert.snapshot.price.toFixed(4)}</small>
                                        </li>
                                    ))
                                ) : (
                                    <p>No recent alerts for this coin.</p>
                                )}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CryptoDetailModal;
