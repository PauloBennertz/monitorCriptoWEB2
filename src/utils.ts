export const formatCurrency = (value: number) => {
    const options = {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 4,
    };
    return new Intl.NumberFormat('pt-BR', options).format(value);
};

import { CryptoData } from './types';

export const formatLargeNumber = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 2 }).format(value);
};

export const countActiveIndicators = (data: CryptoData): number => {
    const indicators = [
        data.bollinger_signal,
        data.macd_signal,
        data.mme_cross,
        data.hilo_signal,
    ];
    return indicators.filter(signal => signal !== 'Nenhum').length;
};

export const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
};

export const formatTimeAgo = (isoTimestamp: string): string => {
    const now = new Date();
    const alertTime = new Date(isoTimestamp);
    const seconds = Math.floor((now.getTime() - alertTime.getTime()) / 1000);

    if (seconds < 60) {
        return `Agora mesmo`;
    }

    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
        return `Há ${minutes} min`;
    }

    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        return `Há ${hours}h`;
    }

    const days = Math.floor(hours / 24);
    return `Há ${days}d`;
};
