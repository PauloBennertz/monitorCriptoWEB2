import React, { useState } from 'react';

import { API_BASE_URL } from '../types';

interface BacktesterPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

const BacktesterPanel: React.FC<BacktesterPanelProps> = ({ isOpen, onClose }) => {
    const [symbol, setSymbol] = useState('BTCUSDT');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState('2024-01-01');
    const [initialCapital, setInitialCapital] = useState(100000);
    const [chartData, setChartData] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleRunBacktest = async () => {
        setIsLoading(true);
        setError(null);
        setChartData(null);

        try {
            const response = await fetch(`${API_BASE_URL}/api/backtest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol,
                    start_date: startDate,
                    end_date: endDate,
                    initial_capital: initialCapital,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to run backtest');
            }

            const data = await response.json();
            setChartData(data);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) {
        return null;
    }

    return (
        <div className="modal-overlay">
            <div className="modal-content" style={{ width: '80%', maxWidth: '1200px' }}>
                <div className="modal-header">
                    <h2>Backtester</h2>
                    <button onClick={onClose} className="close-button">&times;</button>
                </div>
                <div className="modal-body">
                    <div className="backtester-form">
                        <div className="form-group">
                            <label>Symbol:</label>
                            <input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label>Start Date:</label>
                            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label>End Date:</label>
                            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label>Initial Capital:</label>
                            <input type="number" value={initialCapital} onChange={(e) => setInitialCapital(parseFloat(e.target.value))} />
                        </div>
                        <button onClick={handleRunBacktest} disabled={isLoading}>
                            {isLoading ? 'Running...' : 'Run Backtest'}
                        </button>
                    </div>
                    <div className="backtester-chart">
                        {isLoading && <p>Loading chart...</p>}
                        {error && <p style={{ color: 'red' }}>Error: {error}</p>}
                        {chartData && (
                            <Plot
                                data={chartData.data}
                                layout={chartData.layout}
                                style={{ width: '100%', height: '100%' }}
                                config={{ responsive: true }}
                            />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BacktesterPanel;
