import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL, BasicCoin, Alert, ALERT_DEFINITIONS } from '../types';
import ResultsTable from './ResultsTable';

interface HistoricalAnalysisPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

interface AnalysisParams {
    symbol: string;
    startDate: string;
    endDate: string;
}

const initialAlertConditions = Object.keys(ALERT_DEFINITIONS).reduce((acc, key) => {
    acc[key] = true;
    return acc;
}, {} as { [key: string]: boolean });


const HistoricalAnalysisPanel: React.FC<HistoricalAnalysisPanelProps> = ({ isOpen, onClose }) => {
    const [allCoins, setAllCoins] = useState<BasicCoin[]>([]);
    const [symbol, setSymbol] = useState('');
    const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [results, setResults] = useState<Alert[]>([]);
    const [analysisParams, setAnalysisParams] = useState<AnalysisParams | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filteredCoins, setFilteredCoins] = useState<BasicCoin[]>([]);
    const [isCoinListVisible, setIsCoinListVisible] = useState(false);
    const [alertConditions, setAlertConditions] = useState(initialAlertConditions);

    const fetchAllCoins = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/all_tradable_coins`);
            if (!res.ok) throw new Error('Failed to fetch coin list');
            const data: BasicCoin[] = await res.json();
            setAllCoins(data);
        } catch (err) {
            setError('Could not load coin list for selection.');
            console.error(err);
        }
    }, []);

    useEffect(() => {
        if (isOpen) fetchAllCoins();
    }, [isOpen, fetchAllCoins]);

    useEffect(() => {
        if (searchTerm.length > 1) {
            const filtered = allCoins.filter(coin =>
                coin.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                coin.symbol.toLowerCase().includes(searchTerm.toLowerCase())
            );
            setFilteredCoins(filtered.slice(0, 100));
            setIsCoinListVisible(true);
        } else {
            setFilteredCoins([]);
            setIsCoinListVisible(false);
        }
    }, [searchTerm, allCoins]);

    const handleCoinSelect = (selectedCoin: BasicCoin) => {
        setSymbol(selectedCoin.symbol + 'USDT');
        setSearchTerm(`${selectedCoin.name} (${selectedCoin.symbol})`);
        setIsCoinListVisible(false);
    };

    const handleAlertConditionChange = (alertKey: string) => {
        setAlertConditions(prev => ({ ...prev, [alertKey]: !prev[alertKey] }));
    };

    const handleRunAnalysis = async () => {
        if (!symbol || !startDate || !endDate) {
            setError('Por favor, selecione uma moeda e um intervalo de datas.');
            return;
        }
        setIsLoading(true);
        setError(null);
        setResults([]);
        setAnalysisParams(null);

        const selectedAlertsConfig = Object.entries(alertConditions)
            .reduce((acc, [key, value]) => {
                const backendKey = ALERT_DEFINITIONS[key]?.backendKey;
                if (backendKey) {
                    acc[backendKey] = { enabled: value, blinking: true };
                }
                return acc;
            }, {} as { [key: string]: { enabled: boolean; blinking: boolean } });

        try {
            const response = await fetch(`${API_BASE_URL}/api/historical_alerts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    start_date: startDate,
                    end_date: endDate,
                    alert_config: { conditions: selectedAlertsConfig }
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao executar a análise histórica');
            }

            const data = await response.json();
            setResults(data.alerts);
            setAnalysisParams({ symbol, startDate, endDate });

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Ocorreu um erro desconhecido.');
        } finally {
            setIsLoading(false);
        }
    };
    
    const handleDownload = async (format: 'image' | 'html') => {
        if (!analysisParams || results.length === 0) {
            setError('Execute uma análise primeiro para gerar o gráfico.');
            return;
        }

        const endpoint = format === 'image' ? 'chart_image' : 'chart_html';
        const url = `${API_BASE_URL}/api/historical_analysis/${endpoint}`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: analysisParams.symbol,
                    start_date: analysisParams.startDate,
                    end_date: analysisParams.endDate,
                    alerts: results.map(r => ({
                        timestamp: r.timestamp,
                        price: r.snapshot.price,
                        condition: r.condition,
                    })),
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao gerar o gráfico.');
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `${analysisParams.symbol}_analysis_${new Date().toISOString().split('T')[0]}.${format === 'image' ? 'png' : 'html'}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Ocorreu um erro desconhecido ao gerar o gráfico.');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content historical-analysis-panel" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Análise Histórica de Alertas</h2>
                    <button onClick={onClose} className="close-button">&times;</button>
                </div>
                <div className="modal-body">
                    <div className="form-section">
                        <div className="form-group" style={{ position: 'relative' }}>
                            <label htmlFor="coin-search">Digite a Moeda</label>
                            <input
                                type="text"
                                id="coin-search"
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                placeholder="Ex: Bitcoin ou BTC"
                                onFocus={() => searchTerm.length > 1 && setIsCoinListVisible(true)}
                            />
                            {isCoinListVisible && (
                                <ul className="coin-search-results">
                                    {filteredCoins.length > 0 ? (
                                        filteredCoins.map(coin => (
                                            <li key={coin.id} onClick={() => handleCoinSelect(coin)}>
                                                {coin.name} ({coin.symbol})
                                            </li>
                                        ))
                                    ) : (
                                        <li>Nenhum resultado</li>
                                    )}
                                </ul>
                            )}
                        </div>
                        <div className="form-group">
                            <label htmlFor="start-date">Data de Início</label>
                            <input type="date" id="start-date" value={startDate} onChange={e => setStartDate(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label htmlFor="end-date">Data de Fim</label>
                            <input type="date" id="end-date" value={endDate} onChange={e => setEndDate(e.target.value)} />
                        </div>
                    </div>

                    <div className="alert-selection-section">
                        <h4>Selecione os Alertas para Simular</h4>
                        <div className="checkbox-grid">
                            {Object.entries(ALERT_DEFINITIONS).map(([key, def]) => (
                                <div key={key} className="checkbox-item">
                                    <input
                                        type="checkbox"
                                        id={`alert-${key}`}
                                        checked={alertConditions[key]}
                                        onChange={() => handleAlertConditionChange(key)}
                                    />
                                    <label htmlFor={`alert-${key}`}>{def.name}</label>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="form-section" style={{ marginTop: '20px' }}>
                        <button onClick={handleRunAnalysis} disabled={isLoading} className="button button-primary">
                            {isLoading ? 'A analisar...' : 'Executar Análise'}
                        </button>
                    </div>

                    {isLoading && <div className="loading-container">A executar análise...</div>}
                    {error && <div className="error-container">{error}</div>}

                    {results.length > 0 && !isLoading && (
                        <>
                            <div className="download-section" style={{ margin: '20px 0', padding: '15px', border: '1px solid #444', borderRadius: '5px', backgroundColor: '#2c2c2e' }}>
                                <h4>Download do Gráfico da Análise</h4>
                                <p>Baixe o resultado da simulação acima como um gráfico interativo (HTML) ou imagem (PNG).</p>
                                <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                                    <button onClick={() => handleDownload('html')} className="button button-primary">
                                        Baixar Gráfico Interativo (HTML)
                                    </button>
                                    <button onClick={() => handleDownload('image')} className="button">
                                        Baixar Gráfico como Imagem (PNG)
                                    </button>
                                </div>
                            </div>
                            {/* Corrigindo a prop passada para a tabela */}
                            <ResultsTable alerts={results} />
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default HistoricalAnalysisPanel;