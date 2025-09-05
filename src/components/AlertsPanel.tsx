import React from 'react';
import { Alert } from '../types';

/**
 * A panel that displays recent alerts.
 *
 * @param {object} props - The component props.
 * @param {boolean} props.isOpen - Whether the panel is open.
 * @param {Function} props.onClose - The function to call when the panel is closed.
 * @param {Alert[]} props.alerts - The list of alerts to display.
 * @param {Function} props.onClearAlerts - The function to call when the "Clear All" button is clicked.
 * @returns {JSX.Element | null} The rendered component, or null if it is not open.
 */
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
                        alerts.map(alert => (
                            <div key={alert.id} className="alert-item">
                                <div className="alert-header">
                                    <strong>{alert.symbol.replace('USDT','')} - {alert.condition}</strong>
                                    <span>{alert.timestamp}</span>
                                </div>
                                <p>{alert.description}</p>
                            </div>
                        ))
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
