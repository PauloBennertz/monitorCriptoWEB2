import React, { useState, useEffect } from 'react';
import Tooltip from './Tooltip';
import { CryptoData, INDICATOR_TOOLTIPS } from '../types';
import { formatCurrency, formatLargeNumber, countActiveIndicators } from '../utils';

const getRsiData = (data: CryptoData) => {
    if (data.isLoading || data.rsi_value === undefined) return { className: '', text: 'N/A', tooltip: '' };
    if (data.rsi_value < 30) return { className: 'rsi-oversold', text: 'Sobrevenda', tooltip: INDICATOR_TOOLTIPS.rsi_value.oversold };
    if (data.rsi_value > 70) return { className: 'rsi-overbought', text: 'Sobrecompra', tooltip: INDICATOR_TOOLTIPS.rsi_value.overbought };
    return { className: 'rsi-neutral', text: 'Neutro', tooltip: INDICATOR_TOOLTIPS.rsi_value.neutral };
};

const LoadingCard = ({ symbol }: { symbol: string }) => (
    <div className="crypto-card loaading-placeholder">
        <div className="card-header">
            <span className="card-symbol">{symbol.replace('USDT', '')}</span>
            <span className="card-name">Carregando...</span>
        </div>
        <div className="card-price-section">
            <span className="card-price-label">Preço (USD)</span>
            <span className="card-price-value">--</span>
        </div>
        <div className="card-metrics">
            <div className="metric-item"><span className="metric-label">24h %</span><span className="metric-value">--</span></div>
            <div className="metric-item"><span className="metric-label">Volume 24h</span><span className="metric-value">--</span></div>
            <div className="metric-item"><span className="metric-label">Cap. Mercado</span><span className="metric-value">--</span></div>
            <div className="metric-item"><span className="metric-label">RSI</span><span className="metric-value">--</span></div>
            <div className="metric-item"><span className="metric-label">HMA</span><span className="metric-value">--</span></div>
            <div className="metric-item"><span className="metric-label">VWAP</span><span className="metric-value">--</span></div>
            <div className="metric-item"><span className="metric-label">MACD</span><span className="metric-value">--</span></div>
            <div className="metric-item"><span className="metric-label">HiLo</span><span className="metric-value">--</span></div>
        </div>
    </div>
);

interface CryptoCardProps {
    data: CryptoData;
    isBlinkVisible: boolean;
    onClick: (data: CryptoData) => void;
}

const CryptoCard = ({ data, isBlinkVisible, onClick }: CryptoCardProps) => {
    const [flashClass, setFlashClass] = useState('');

    useEffect(() => {
        if (data.isLoading || data.lastPrice === undefined) return;

        if (data.price > data.lastPrice) {
            setFlashClass('flash-green');
        } else if (data.price < data.lastPrice) {
            setFlashClass('flash-red');
        }

        const timer = setTimeout(() => setFlashClass(''), 700);
        return () => clearTimeout(timer);
    }, [data.price, data.lastPrice, data.isLoading]);

    if (data.isLoading) {
        return <LoadingCard symbol={data.symbol} />;
    }

    const rsiData = getRsiData(data);
    const activeIndicatorsCount = countActiveIndicators(data);

    let blinkingClass = '';
    if (isBlinkVisible) {
        if (activeIndicatorsCount === 1) {
            blinkingClass = 'blink-on-blue';
        } else if (activeIndicatorsCount > 1) {
            blinkingClass = 'blink-on-red';
        }
    }

    return (
        <div className={`crypto-card ${blinkingClass}`} onClick={() => onClick(data)}>
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
                
                {/* Indicador HMA com Tooltip */}
                <div className="metric-item">
                    <Tooltip text={data.hma_active ? INDICATOR_TOOLTIPS.hma.active : INDICATOR_TOOLTIPS.hma.inactive}>
                        <span className="metric-label">HMA</span>
                    </Tooltip>
                    <span className={`metric-value ${data.hma_active ? 'positive' : ''}`}>
                        {data.hma ? formatCurrency(data.hma) : 'N/A'}
                    </span>
                </div>

{/* Indicador VWAP com Tooltip */}
<div className="metric-item">
    <Tooltip text={data.vwap_active ? INDICATOR_TOOLTIPS.vwap.active : INDICATOR_TOOLTIPS.vwap.inactive}>
        <span className="metric-label">VWAP</span>
    </Tooltip>
    <span className={`metric-value ${data.vwap_active ? 'positive' : ''}`}>
        {data.vwap ? formatCurrency(data.vwap) : 'N/A'}
    </span>
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