import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { Alert, API_BASE_URL } from '../types';
import './ChartFullScreen.css';

// Interface to match the API response for coin details
interface CoinDetail {
    alerts: Alert[];
    chartData: any;
    indicatorsData: { [key: string]: { x: string[], y: number[], name: string } };
    annotations: any[];
}

const ChartFullScreen: React.FC = () => {
    const { coinSymbol } = useParams<{ coinSymbol: string }>();
    const [details, setDetails] = useState<CoinDetail | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [coinName, setCoinName] = useState<string>('');


    useEffect(() => {
        const fetchDetails = async () => {
            if (!coinSymbol) return;
            setIsLoading(true);
            setError(null);
            try {
                const response = await fetch(`${API_BASE_URL}/api/coin_details/${coinSymbol}`);
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to fetch coin details');
                }
                const data: CoinDetail = await response.json();
                setDetails(data);

                // Assuming the chartData contains the name, otherwise, we might need another way to get it
                // For now, let's just use the symbol. A proper implementation might need to fetch coin details.
                setCoinName(coinSymbol.replace('USDT', ''));

            } catch (err) {
                setError(err instanceof Error ? err.message : 'An unknown error occurred');
            } finally {
                setIsLoading(false);
            }
        };

        fetchDetails();
    }, [coinSymbol]);

    // This function can be simplified or removed if not needed for the full-screen view
    const getAdjustedAnnotations = (annotations: any[], chartData: any) => {
        if (!annotations || annotations.length === 0) return [];
        // Simplified adjustment for full-screen
        return annotations.map(ann => ({
            ...ann,
            ay: -40,
            yanchor: 'bottom',
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            bordercolor: '#c7c7c7',
            borderwidth: 1,
            font: { color: '#000', size: 12 },
        }));
    };

    const chartLayout = useMemo(() => ({
        title: `${coinName} - Full Screen Chart`,
        paper_bgcolor: '#1a1a1a',
        plot_bgcolor: '#1a1a1a',
        font: { color: '#f0f0f0' },
        xaxis: {
            rangeslider: { visible: true, bgcolor: '#333' }, // Enable range slider for better navigation
            gridcolor: '#444',
            linecolor: '#666',
            type: 'date',
        },
        yaxis: {
            title: 'Price (USD)',
            gridcolor: '#444',
            linecolor: '#666',
            autorange: true,
            fixedrange: false, // Allow zoom
        },
        yaxis2: {
            title: 'RSI',
            overlaying: 'y',
            side: 'right',
            range: [0, 100],
            showgrid: false,
            zeroline: false,
            linecolor: '#888',
            font: { color: '#888' },
        },
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.05,
            xanchor: 'right',
            x: 1,
        },
        autosize: true,
        annotations: details?.annotations && details.chartData ? getAdjustedAnnotations(details.annotations, details.chartData) : [],
    }), [coinName, details]);

    const chartData = useMemo(() => {
        const data: any[] = [];
        if (details?.chartData) {
            data.push({
                ...details.chartData,
                type: 'candlestick',
                increasing: { line: { color: '#00b589', width: 2 } },
                decreasing: { line: { color: '#f74668', width: 2 } },
                name: 'Price',
            });
        }

        if (details?.indicatorsData) {
            Object.values(details.indicatorsData).forEach(indicator => {
                const isRSI = indicator.name.includes('RSI');
                data.push({
                    x: indicator.x,
                    y: indicator.y,
                    name: indicator.name,
                    type: 'scatter',
                    mode: 'lines',
                    yaxis: isRSI ? 'y2' : 'y',
                    line: {
                        color: isRSI ? '#ffc107' : undefined, // Let Plotly decide other colors or set them
                        width: 1.5,
                        dash: isRSI ? 'dot' : 'solid',
                    }
                });
            });
        }
        return data;
    }, [details]);

    if (isLoading) {
        return <div className="fullscreen-loading">Loading chart...</div>;
    }

    if (error) {
        return <div className="fullscreen-error">Error: {error}</div>;
    }

    return (
        <div className="chart-fullscreen-container">
            <Plot
                data={chartData}
                layout={chartLayout}
                config={{ responsive: true, displaylogo: false, scrollZoom: true }}
                style={{ width: '100%', height: '100%' }}
            />
        </div>
    );
};

export default ChartFullScreen;
