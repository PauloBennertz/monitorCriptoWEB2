import React from 'react';
import { Alert } from '../types';
import './AlertTicker.css';

interface AlertTickerProps {
    alerts: Alert[];
}

const AlertTicker: React.FC<AlertTickerProps> = ({ alerts }) => {
    const tickerContent = alerts.length > 0
        ? alerts.map(alert => {
            const time = new Date(alert.timestamp).toLocaleTimeString('pt-BR');
            return `[${time}] ${alert.symbol}: ${alert.condition}`;
        }).join(' --- ')
        : 'Nenhum alerta recente.';

    return (
        <div className="alert-ticker-container">
            <div className="alert-ticker-content">
                {tickerContent}
            </div>
        </div>
    );
};

export default AlertTicker;
