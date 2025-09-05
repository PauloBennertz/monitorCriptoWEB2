import React, { useState, useEffect } from 'react';
import Tooltip from './Tooltip';
import { CryptoData, INDICATOR_TOOLTIPS } from '../types'; // Assuming types and constants are moved to a types file
import { formatCurrency, formatLargeNumber } from '../utils'; // Assuming helpers are moved to a utils file


    const [flashClass, setFlashClass] = useState('');

    useEffect(() => {
        if (data.lastPrice === undefined) return;

        if (data.price > data.lastPrice) {
            setFlashClass('flash-green');
        } else if (data.price < data.lastPrice) {
            setFlashClass('flash-red');
        }

        const timer = setTimeout(() => setFlashClass(''), 700);
        return () => clearTimeout(timer);
    }, [data.price, data.lastPrice]);

    const getBlinkingClass = () => {
        const indicators = [
            data.bollinger_signal,
            data.macd_signal,
            data.mme_cross,
            data.hilo_signal,
        ];
        const activeIndicators = indicators.filter(signal => signal !== 'Nenhum').length;

        if (activeIndicators === 1) {
            return 'blinking-blue';
        } else if (activeIndicators > 1) {
            return 'blinking-red';
        }
        return '';
    };

    const getRsiData = () => {
        if (data.rsi_value < 30) return { className: 'rsi-oversold', text: 'Sobrevenda', tooltip: INDICATOR_TOOLTIPS.rsi_value.oversold };
        if (data.rsi_value > 70) return { className: 'rsi-overbought', text: 'Sobrecompra', tooltip: INDICATOR_TOOLTIPS.rsi_value.overbought };
        return { className: 'rsi-neutral', text: 'Neutro', tooltip: INDICATOR_TOOLTIPS.rsi_value.neutral };
    };

    const rsiData = getRsiData();
    const blinkingClass = getBlinkingClass();

    return (
        <div className={`crypto-card ${blinkingClass}`}>
            <div className="card-header">
                <span className="card-symbol">{data.symbol.replace('USDT', '')}</span>
                <span className="card-name">{data.name}</span>
            </div>
            <div className="card-price-section">
                <span className="card-price-label">Preço (USD)</span>
                <span className={`card-price-value ${flashClass}`}>{formatCurrency(data.price)}</span>
            </div>
            <div className="card-metrics">
                <div className="metric-item">
                    <span className="metric-label">24h %</span>
                    <span className={`metric-value ${data.price_change_24h >= 0 ? 'positive' : 'negative'}`}>
                        {data.price_change_24h.toFixed(2)}%
                    </span>
                </div>
                <div className="metric-item">
                    <span className="metric-label">Volume 24h</span>
                    <span className="metric-value">{formatLargeNumber(data.volume_24h)}</span>
                </div>
                <div className="metric-item">
                    <span className="metric-label">Cap. Mercado</span>
                    <span className="metric-value">{formatLargeNumber(data.market_cap)}</span>
                </div>
                <div className="metric-item">
                    <Tooltip text={rsiData.tooltip}>
                        <span className="metric-label">RSI</span>
                    </Tooltip>
                    <span className={`metric-value rsi-value ${rsiData.className}`}>{rsiData.text} ({data.rsi_value.toFixed(2)})</span>
                </div>
                 <div className="metric-item">
                    <Tooltip text={INDICATOR_TOOLTIPS.bollinger_signal[data.bollinger_signal]}>
                        <span className="metric-label">Bandas B.</span>
                    </Tooltip>
                    <span className="metric-value">{data.bollinger_signal}</span>
                </div>
                 <div className="metric-item">
                     <Tooltip text={INDICATOR_TOOLTIPS.macd_signal[data.macd_signal]}>
                        <span className="metric-label">MACD</span>
                    </Tooltip>
                    <span className="metric-value">{data.macd_signal}</span>
                </div>
                 <div className="metric-item">
                     <Tooltip text={INDICATOR_TOOLTIPS.mme_cross[data.mme_cross]}>
                        <span className="metric-label">MME Cross</span>
                    </Tooltip>
                    <span className="metric-value">{data.mme_cross}</span>
                </div>
                <div className="metric-item">
                     <Tooltip text={INDICATOR_TOOLTIPS.hilo_signal[data.hilo_signal]}>
                        <span className="metric-label">HiLo</span>
                    </Tooltip>
                    <span className="metric-value">{data.hilo_signal}</span>
                </div>
            </div>
        </div>
    );
};

export default CryptoCard;
