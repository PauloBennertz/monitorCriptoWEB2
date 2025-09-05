import React from 'react';
import { Alert } from '../types';

const AlertsPanel = ({ isOpen, onClose, alerts, onClearAlerts }: {
    isOpen: boolean;
    onClose: () => void;
    alerts: Alert[];
    onClearAlerts: () => void;
}) => {
    if (!isOpen) return null;

    return (
        <>
            <div className="panel-overlay" onClick={onClose}></div>
            <div className="alerts-panel">
                <div className="panel-header">
                    <h2>Notificações</h2>
                    <button onClick={onClose} className="close-button">&times;</button>
                </div>
                <div className="panel-body">
                    {alerts.length === 0 ? (
                        <p className="no-alerts">Nenhum alerta recente.</p>
                    ) : (
                        alerts.map(alert => {
                            const getAlertItemClass = (alert: Alert) => {
                                let baseClass = 'alert-item';
                                // The alert ID is structured as 'SYMBOL-TRIGGER_KEY-TIMESTAMP'
                                // This is a reliable way to check for the trigger type without changing the Alert interface.
                                if (alert.id.includes('CRUZ_DOURADA')) {
                                    return `${baseClass} alert-golden-cross`;
                                }
                                if (alert.id.includes('CRUZ_DA_MORTE')) {
                                    return `${baseClass} alert-death-cross`;
                                }
                                return baseClass;
                            };

                            return (
                                <div key={alert.id} className={getAlertItemClass(alert)}>
                                    <div className="alert-header">
                                        <strong>{alert.symbol.replace('USDT', '')} - {alert.condition}</strong>
                                        <span>{new Date(alert.timestamp).toLocaleTimeString('pt-BR')}</span>
                                    </div>
                                    <p>{alert.description}</p>
                                </div>
                            );
                        })
                    )}
                </div>
                <div className="panel-footer">
                    <button onClick={onClearAlerts} disabled={alerts.length === 0}>Limpar Tudo</button>
                </div>
            </div>
        </>
    );
};

export default AlertsPanel;
