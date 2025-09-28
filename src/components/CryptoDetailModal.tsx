import React, { useState, useEffect } from 'react';
import { CryptoData, Alert, API_BASE_URL } from '../types';
import { format } from 'date-fns';

interface CryptoDetailModalProps {
    coin: CryptoData;
    onClose: () => void;
}

interface CoinAlerts {
    alerts: Alert[];
}

const CryptoDetailModal: React.FC<CryptoDetailModalProps> = ({ coin, onClose }) => {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchAlertDetails = async () => {
            setIsLoading(true);
            setError(null);
            try {
                const response = await fetch(`${API_BASE_URL}/api/coin_details/${coin.symbol}`);
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to fetch coin alerts');
                }
                const data: CoinAlerts = await response.json();
                setAlerts(data.alerts);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'An unknown error occurred.');
            } finally {
                setIsLoading(false);
            }
        };
        fetchAlertDetails();
    }, [coin.symbol]);

    const handleDownloadImage = () => {
        const imageUrl = `${API_BASE_URL}/api/coin_details/${coin.symbol}/chart_image`;
        window.open(imageUrl, '_blank');
    };

    const handleDownloadHtml = () => {
        const htmlUrl = `${API_BASE_URL}/api/coin_details/${coin.symbol}/chart_html`;
        window.open(htmlUrl, '_blank');
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content crypto-detail-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">Detalhes de {coin.name} ({coin.symbol})</h2>
                    <button onClick={onClose} className="close-button">&times;</button>
                </div>
                <div className="modal-body">
                    <div className="detail-section">
                        <h3>Download do Gráfico de Alertas</h3>
                        <p>Use os botões abaixo para baixar o gráfico. A opção HTML é recomendada para uma análise interativa completa.</p>
                        <div className="download-buttons" style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                            <button onClick={handleDownloadHtml} className="button button-primary">Baixar Gráfico Interativo (HTML)</button>
                            <button onClick={handleDownloadImage} className="button">Baixar Gráfico como Imagem (PNG)</button>
                        </div>
                    </div>
                    <div className="detail-section">
                        <h3>Alertas Recentes (Últimos 7 dias)</h3>
                        {isLoading ? <p>A carregar alertas...</p> : error ? <p className="error-message">Erro: {error}</p> : (
                            <ul className="alert-list">
                                {alerts.length > 0 ? (
                                    alerts.map(alert => (
                                        <li key={alert.id}>
                                            <strong>{alert.condition.replace(/_/g, ' ')}</strong> - {format(new Date(alert.timestamp), 'dd/MM/yyyy HH:mm')}
                                            <small>Preço: ${alert.snapshot.price.toFixed(4)}</small>
                                        </li>
                                    ))
                                 ) : (
                                    <p>Nenhum alerta recente para esta moeda.</p>
                                )}
                            </ul>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CryptoDetailModal;