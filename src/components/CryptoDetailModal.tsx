import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { CryptoData, Alert, API_BASE_URL } from '../types';
import { format } from 'date-fns';

interface CryptoDetailModalProps {
    coin: CryptoData;
    onClose: () => void;
}

interface CoinDetail {
    alerts: Alert[];
    chartData: any;
}

const CryptoDetailModal: React.FC<CryptoDetailModalProps> = ({ coin, onClose }) => {
    const [details, setDetails] = useState<CoinDetail | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchDetails = async () => {
            setIsLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/api/coin_details/${coin.symbol}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch coin details');
                }
                const data = await response.json();
                setDetails(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'An unknown error occurred');
            } finally {
                setIsLoading(false);
            }
        };

        fetchDetails();
    }, [coin.symbol]);

    const getAlertMarkers = () => {
        if (!details || !details.alerts || !details.chartData) {
            return {};
        }

        const alertTimes = details.alerts.map(alert => alert.timestamp);
        const alertPrices = details.alerts.map(alert => alert.snapshot.price);
        const alertTexts = details.alerts.map(alert => `${alert.condition} at ${format(new Date(alert.timestamp), 'HH:mm')}`);

        return {
            x: alertTimes,
            y: alertPrices,
            mode: 'markers',
            type: 'scatter',
            name: 'Alerts',
            text: alertTexts,
            marker: {
                color: 'red',
                size: 10,
                symbol: 'triangle-up'
            },
        };
    };

    const getAlertAnnotations = () => {
        if (!details || !details.alerts) {
            return [];
        }
        return details.alerts.map(alert => ({
            x: alert.timestamp,
            y: alert.snapshot.price,
            xref: 'x',
            yref: 'y',
            text: alert.condition.replace(/_/g, ' '), // Make condition more readable
            showarrow: true,
            arrowhead: 2,
            ax: 0,
            ay: -40, // Offset the text above the marker
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            bordercolor: '#c7c7c7',
            borderwidth: 1,
            font: {
                color: '#000',
                size: 12,
            }
        }));
    };

    const chartLayout = {
        title: {
            text: `${coin.name} (${coin.symbol.replace('USDT', '')}) - Price and Alerts`,
            font: {
                color: '#f8f9fa',
                size: 18,
            },
            x: 0.5,
            xanchor: 'center',
        },
        paper_bgcolor: '#343a40',
        plot_bgcolor: '#212529',
        font: {
            color: '#f8f9fa'
        },
        xaxis: {
            rangeslider: { visible: false },
            gridcolor: '#495057',
            linecolor: '#495057',
        },
        yaxis: {
            title: 'Price (USD)',
            gridcolor: '#495057',
            linecolor: '#495057',
        },
        legend: {
            font: {
                color: '#f8f9fa'
            }
        },
        showlegend: true,
        annotations: getAlertAnnotations(),
    };

    const styledChartData = details?.chartData ? {
        ...details.chartData,
        increasing: { line: { color: '#28a745' } },
        decreasing: { line: { color: '#dc3545' } },
        name: 'Price',
    } : null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>{coin.name} ({coin.symbol.replace('USDT', '')})</h2>
                    <button onClick={onClose} className="close-button">&times;</button>
                </div>
                <div className="modal-body">
                    {isLoading ? (
                        <div>Loading details...</div>
                    ) : error ? (
                        <div className="error-container">{error}</div>
                    ) : details ? (
                        <>
                            <div className="detail-section">
                                <h3>Last Alerts</h3>
                                <ul className="alert-list">
                                    {details.alerts.length > 0 ? (
                                        details.alerts.map(alert => (
                                            <li key={alert.id}>
                                                <strong>{alert.condition}</strong> - {format(new Date(alert.timestamp), 'dd/MM/yyyy HH:mm')}
                                                <small>Price: ${alert.snapshot.price.toFixed(2)}</small>
                                            </li>
                                        ))
                                    ) : (
                                        <p>No recent alerts for this coin.</p>
                                    )}
                                </ul>
                            </div>
                            <div className="detail-section">
                                <h3>Alerts Chart (Last 7 Days)</h3>
                                {styledChartData ? (
                                    <Plot
                                        data={[styledChartData, getAlertMarkers()]}
                                        layout={chartLayout}
                                        config={{ responsive: true }}
                                        className="plotly-chart"
                                    />
                                ) : (
                                    <p>No chart data available.</p>
                                )}
                            </div>
                        </>
                    ) : null}
                </div>
            </div>
        </div>
    );
};

export default CryptoDetailModal;
