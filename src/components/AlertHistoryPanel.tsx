// src/components/AlertHistoryPanel.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { Alert, API_BASE_URL } from '../types';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface AlertHistoryPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

const AlertHistoryPanel: React.FC<AlertHistoryPanelProps> = ({ isOpen, onClose }) => {
    const [history, setHistory] = useState<Alert[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    const fetchHistory = (start?: string, end?: string) => {
        setIsLoading(true);
        setError(null);

        let url = `${API_BASE_URL}/api/alerts`;
        const params = new URLSearchParams();
        if (start) {
            params.append('start_date', start);
        }
        if (end) {
            params.append('end_date', end);
        }
        const queryString = params.toString();
        if (queryString) {
            url += `?${queryString}`;
        }

        fetch(url)
            .then(res => {
                if (!res.ok) {
                    throw new Error('Falha ao buscar o histórico de alertas.');
                }
                return res.json();
            })
            .then((data: Alert[]) => {
                setHistory(data);
            })
            .catch(err => {
                setError(err.message || 'Um erro desconhecido ocorreu.');
            })
            .finally(() => {
                setIsLoading(false);
            });
    };

    useEffect(() => {
        if (isOpen) {
            fetchHistory();
        }
    }, [isOpen]);

    const groupedHistory = useMemo(() => {
        return history.reduce((acc, alert) => {
            const key = alert.symbol;
            if (!acc[key]) {
                acc[key] = [];
            }
            acc[key].push(alert);
            return acc;
        }, {} as Record<string, Alert[]>);
    }, [history]);

    if (!isOpen) {
        return null;
    }

    const handleClearHistory = async () => {
        if (!window.confirm('Tem certeza de que deseja apagar todo o histórico de alertas? Esta ação não pode ser desfeita.')) {
            return;
        }

        setIsLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE_URL}/api/alerts/history`, {
                method: 'DELETE',
            });
            if (!res.ok) {
                throw new Error('Falha ao limpar o histórico.');
            }
            setHistory([]); // Clear history on the frontend
        } catch (err) {
            setError(err.message || 'Um erro desconhecido ocorreu ao tentar limpar o histórico.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleFilter = () => {
        if (!startDate || !endDate) {
            setError("Por favor, selecione as datas de início e fim.");
            return;
        }
        fetchHistory(startDate, endDate);
    };

    const handleClearFilter = () => {
        setStartDate('');
        setEndDate('');
        // Fetches the full, unfiltered history
        fetchHistory();
    };

    const renderContent = () => {
        if (isLoading) {
            return <div className="loading-container">Carregando histórico...</div>;
        }
        if (error) {
            return <div className="error-container">{error}</div>;
        }
        if (history.length === 0) {
            return <p className="no-results-message">Nenhum alerta encontrado para o período selecionado.</p>;
        }
        return (
            <div className="alert-history-list">
                {Object.entries(groupedHistory).map(([symbol, alerts]) => (
                    <div key={symbol} className="currency-group">
                        <h3 className="currency-group-title">{symbol.replace('USDT', '')}</h3>
                        {alerts.map(alert => (
                            <div key={alert.id} className="alert-history-item">
                                <div className="alert-history-header">
                                    <span className="alert-history-symbol">{alert.snapshot.name}</span>
                                    <span className="alert-history-timestamp" title={new Date(alert.timestamp).toLocaleString('pt-BR')}>
                                        {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true, locale: ptBR })}
                                    </span>
                                </div>
                                <div className="alert-history-body">
                                    {alert.condition}
                                </div>
                                <div className="alert-history-details">
                                    Preço no momento do alerta: $ {alert.snapshot.price.toFixed(2)}
                                </div>
                            </div>
                        ))}
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content alert-history-panel" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">Histórico de Alertas</h2>
                    <button onClick={onClose} className="close-button" aria-label="Fechar">&times;</button>
                </div>
                <div className="filter-container">
                    <div className="filter-item">
                        <label htmlFor="start-date">De:</label>
                        <input
                            type="date"
                            id="start-date"
                            value={startDate}
                            onChange={e => setStartDate(e.target.value)}
                        />
                    </div>
                    <div className="filter-item">
                        <label htmlFor="end-date">Até:</label>
                        <input
                            type="date"
                            id="end-date"
                            value={endDate}
                            onChange={e => setEndDate(e.target.value)}
                        />
                    </div>
                    <button onClick={handleFilter} className="button" disabled={isLoading}>
                        Filtrar
                    </button>
                    <button onClick={handleClearFilter} className="button button-secondary" disabled={isLoading}>
                        Limpar
                    </button>
                </div>
                <div className="modal-body">
                    {renderContent()}
                </div>
                <div className="modal-footer">
                    <button
                        onClick={handleClearHistory}
                        className="button button-danger"
                        disabled={isLoading || history.length === 0}
                    >
                        Limpar Histórico
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AlertHistoryPanel;
