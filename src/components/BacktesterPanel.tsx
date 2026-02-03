import React, { useState } from 'react';
import Plot from 'react-plotly.js';
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
    
    // Novos estados para Estratégia
    const [strategy, setStrategy] = useState('SMA');
    const [hmaPeriod, setHmaPeriod] = useState(21);
    const [smaShort, setSmaShort] = useState(40);
    const [smaLong, setSmaLong] = useState(100);

    const [chartData, setChartData] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleRunBacktest = async () => {
        setIsLoading(true);
        setError(null);
        setChartData(null);

        // Monta o objeto de parâmetros baseado na estratégia escolhida
        let params = {};
        if (strategy === 'SMA') {
            params = { short_window: smaShort, long_window: smaLong };
        } else if (strategy === 'HMA') {
            params = { period: hmaPeriod };
        }
        // VWAP não precisa de parâmetros extras por enquanto

        try {
            const response = await fetch(`${API_BASE_URL}/api/backtest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol,
                    start_date: startDate,
                    end_date: endDate,
                    initial_capital: initialCapital,
                    strategy: strategy, // Envia a estratégia
                    parameters: params  // Envia os parâmetros
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
                    <h2>Backtester Pro</h2>
                    <button onClick={onClose} className="close-button">&times;</button>
                </div>
                <div className="modal-body">
                    <div className="backtester-form">
                        <div className="form-group">
                            <label>Symbol:</label>
                            <input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
                        </div>
                        
                        {/* Seletor de Estratégia */}
                        <div className="form-group">
                            <label>Estratégia:</label>
                            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                                <option value="SMA">Cruzamento SMA</option>
                                <option value="HMA">Tendência HMA</option>
                                <option value="VWAP">Tendência VWAP</option>
                            </select>
                        </div>

                        {/* Parâmetros Dinâmicos */}
                        {strategy === 'SMA' && (
                            <>
                                <div className="form-group">
                                    <label>SMA Curta:</label>
                                    <input type="number" value={smaShort} onChange={(e) => setSmaShort(Number(e.target.value))} />
                                </div>
                                <div className="form-group">
                                    <label>SMA Longa:</label>
                                    <input type="number" value={smaLong} onChange={(e) => setSmaLong(Number(e.target.value))} />
                                </div>
                            </>
                        )}

                        {strategy === 'HMA' && (
                            <div className="form-group">
                                <label>Período HMA:</label>
                                <input type="number" value={hmaPeriod} onChange={(e) => setHmaPeriod(Number(e.target.value))} />
                            </div>
                        )}
                        
                        {strategy === 'VWAP' && (
                             <div className="form-group" style={{fontStyle: 'italic', fontSize: '0.9em', color: '#888'}}>
                                VWAP usa o volume ponderado desde o início do período selecionado.
                            </div>
                        )}

                        <div className="form-group">
                            <label>Data Início:</label>
                            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label>Data Fim:</label>
                            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label>Capital Inicial ($):</label>
                            <input type="number" value={initialCapital} onChange={(e) => setInitialCapital(parseFloat(e.target.value))} />
                        </div>
                        
                        <button onClick={handleRunBacktest} disabled={isLoading} style={{marginTop: '20px'}}>
                            {isLoading ? 'Rodando Simulação...' : 'Executar Backtest'}
                        </button>
                    </div>
                    
                    <div className="backtester-chart">
                        {isLoading && <p>Carregando gráfico...</p>}
                        {error && <p style={{ color: 'red' }}>Erro: {error}</p>}
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