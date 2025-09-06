import React from 'react';
import { Alert } from '../types';
import { formatTimeAgo } from '../utils';
import './AlertTicker.css';

interface AlertTickerProps {
    alerts: Alert[];
}

const AlertTicker: React.FC<AlertTickerProps> = ({ alerts }) => {
    return (
        <div className="alert-ticker-container">
            <div className="alert-ticker-content">
                {alerts.length > 0 ? (
                    alerts.map((alert, index) => (
                        <span key={alert.id} className="alert-item">
                            {formatTimeAgo(alert.timestamp)} - <span className="alert-symbol">{alert.symbol}</span> - {alert.condition}
                            {index < alerts.length - 1 && <span className="separator">|</span>}
                        </span>
                    ))
                ) : (
                    <span className="alert-item">Nenhum alerta recente.</span>
                )}
            </div>
        </div>
    );
};

export default AlertTicker;
