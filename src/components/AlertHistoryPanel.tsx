// src/components/AlertHistoryPanel.tsx
import React, { useState, useEffect } from 'react';
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

    useEffect(() => {
        if (isOpen) {
            setIsLoading(true);
            setError(null);
            fetch(`${API_BASE_URL}/api/alerts`)
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
        }
    }, [isOpen]);

    if (!isOpen) {
        return null;
    }

    const renderContent = () => {
        if (isLoading) {
            return <div className="loading-container">Carregando histórico...</div>;
        }
        if (error) {
            return <div className="error-container">{error}</div>;
        }
        if (history.length === 0) {
            return <p className="no-results-message">Nenhum alerta foi registrado ainda.</p>;
        }
        return (
            <div className="alert-history-list">
                {history.map(alert => (
                    <div key={alert.id} className="alert-history-item">
                        <div className="alert-history-header">
                            <span className="alert-history-symbol">{alert.snapshot.name} ({alert.symbol.replace('USDT', '')})</span>
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
        );
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content alert-history-panel" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">Histórico de Alertas</h2>
                    <button onClick={onClose} className="close-button" aria-label="Fechar">&times;</button>
                </div>
                <div className="modal-body">
                    {renderContent()}
                </div>
            </div>
        </div>
    );
};

export default AlertHistoryPanel;
