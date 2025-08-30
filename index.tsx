import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { GoogleGenAI, GenerateContentResponse } from "@google/genai";

// --- TYPES ---
interface CryptoData {
  symbol: string;
  name: string;
  price: number;
  lastPrice?: number;
  price_change_24h: number;
  volume_24h: number;
  market_cap: number;
  rsi_value: number;
  bollinger_signal: string;
  macd_signal:string;
  mme_cross: string;
  hilo_signal: string;
}

interface Alert {
  id: string;
  symbol: string;
  condition: string;
  description: string;
  timestamp: string;
  snapshot: CryptoData;
}

interface AlertConfig {
  enabled: boolean;
  cooldown: number; // in seconds
}

interface AlertConfigs {
  [symbol: string]: {
    [alertType: string]: AlertConfig;
  };
}

interface MutedAlert {
  symbol: string;
  alertType: string;
  muteUntil: number; // timestamp
}

interface GroundingChunk {
  web: {
    uri: string;
    title: string;
  };
}

// --- ALERT CONFIGURATION CONSTANTS ---
const ALERT_DEFINITIONS: Record<string, { name: string; description: string }> = {
    PRECO_ACIMA_ETH: { name: 'Preço Alvo Atingido (ETH)', description: 'Dispara quando o preço do Ethereum (ETH) ultrapassa um limiar pré-definido.' },
    FUGA_CAPITAL: { name: 'Queda Súbita com Volume', description: 'Detecta uma queda de preço acentuada acompanhada por um aumento significativo no volume de negociação.' },
    HILO_COMPRA: { name: 'Sinal de Compra HiLo', description: 'Dispara quando o indicador HiLo Activator gera um sinal de compra.' },
    RSI_SOBREVENDA: { name: 'RSI em Sobrevenda', description: 'Alerta quando o Índice de Força Relativa (RSI) entra em território de sobrevenda (abaixo de 30).' },
    RSI_SOBRECOMPRA: { name: 'RSI em Sobrecompra', description: 'Alerta quando o RSI entra em território de sobrecompra (acima de 70).' },
    CRUZ_DOURADA: { name: 'Cruz Dourada (MME)', description: 'Sinal de alta de longo prazo quando a MME de 50 períodos cruza acima da de 200.' },
    CRUZ_DA_MORTE: { name: 'Cruz da Morte (MME)', description: 'Sinal de baixa de longo prazo quando a MME de 50 períodos cruza abaixo da de 200.' },
    MACD_ALTA: { name: 'Cruzamento de Alta (MACD)', description: 'Sinal de momentum de alta quando a linha MACD cruza para cima da linha de sinal.' },
    MACD_BAIXA: { name: 'Cruzamento de Baixa (MACD)', description: 'Sinal de momentum de baixa quando a linha MACD cruza para baixo da linha de sinal.' },
};

const COOLDOWN_OPTIONS = [
    { value: 300, label: '5 minutos' },
    { value: 900, label: '15 minutos' },
    { value: 3600, label: '1 hora' },
    { value: 14400, label: '4 horas' },
    { value: 86400, label: '24 horas' },
];

const MUTE_OPTIONS = [
    { value: 3600, label: '1 hora' },
    { value: 14400, label: '4 horas' },
    { value: 86400, label: '24 horas' },
];

const DEFAULT_ALERT_CONFIG: AlertConfig = {
    enabled: true,
    cooldown: 900, // 15 minutes
};

// --- TOOLTIP DEFINITIONS ---
const INDICATOR_TOOLTIPS: Record<string, Record<string, string>> = {
    rsi_value: {
        oversold: 'RSI (Índice de Força Relativa) abaixo de 30. Sugere que o ativo pode estar desvalorizado.',
        overbought: 'RSI (Índice de Força Relativa) acima de 70. Sugere que o ativo pode estar supervalorizado.',
        neutral: 'RSI em território neutro (entre 30 e 70).',
    },
    bollinger_signal: {
        'Abaixo da Banda': 'O preço está relativamente baixo, indicando uma possível condição de sobrevenda.',
        'Acima da Banda': 'O preço está relativamente alto, indicando uma condição de sobrecompra.',
        'Nenhum': 'O preço está dentro das bandas de volatilidade normais.'
    },
    macd_signal: {
        'Cruzamento de Alta': 'Sinal de alta do MACD. A linha MACD cruzou para cima da linha de sinal.',
        'Cruzamento de Baixa': 'Sinal de baixa do MACD. A linha MACD cruzou para baixo da linha de sinal.',
        'Nenhum': 'Nenhum cruzamento de MACD detectado.'
    },
    mme_cross: {
        'Cruz Dourada': 'Cruz Dourada (MME 50 cruzou para cima da 200). Forte sinal de tendência de alta.',
        'Cruz da Morte': 'Cruz da Morte (MME 50 cruzou para baixo da 200). Forte sinal de tendência de baixa.',
        'Nenhum': 'Nenhum cruzamento de médias móveis significativo.'
    },
    hilo_signal: {
        'HiLo Buy': 'Sinal de compra do indicador HiLo. O preço cruzou acima da média móvel das máximas.',
        'HiLo Sell': 'Sinal de venda do indicador HiLo. O preço cruzou abaixo da média móvel das mínimas.',
        'Nenhum': 'Nenhum sinal do indicador HiLo.'
    }
};


// --- EXPANDED MOCK DATA POOL ---
const ALL_MOCK_CRYPTO_DATA: CryptoData[] = [
  { symbol: 'BTCUSDT', name: 'Bitcoin', price: 68134.75, price_change_24h: 1.5, volume_24h: 35_000_000_000, market_cap: 1_350_000_000_000, rsi_value: 65, bollinger_signal: 'Nenhum', macd_signal: 'Cruzamento de Alta', mme_cross: 'Nenhum', hilo_signal: 'HiLo Buy' },
  { symbol: 'ETHUSDT', name: 'Ethereum', price: 3550.21, price_change_24h: -0.8, volume_24h: 18_000_000_000, market_cap: 426_000_000_000, rsi_value: 45, bollinger_signal: 'Nenhum', macd_signal: 'Nenhum', mme_cross: 'Nenhum', hilo_signal: 'Nenhum' },
  { symbol: 'SOLUSDT', name: 'Solana', price: 165.80, price_change_24h: 5.2, volume_24h: 2_500_000_000, market_cap: 76_000_000_000, rsi_value: 72, bollinger_signal: 'Acima da Banda', macd_signal: 'Cruzamento de Alta', mme_cross: 'Nenhum', hilo_signal: 'HiLo Buy' },
  { symbol: 'XRPUSDT', name: 'XRP', price: 0.5234, price_change_24h: -2.1, volume_24h: 1_200_000_000, market_cap: 29_000_000_000, rsi_value: 28, bollinger_signal: 'Abaixo da Banda', macd_signal: 'Cruzamento de Baixa', mme_cross: 'Cruz da Morte', hilo_signal: 'HiLo Sell' },
  { symbol: 'DOGEUSDT', name: 'Dogecoin', price: 0.1588, price_change_24h: 3.5, volume_24h: 900_000_000, market_cap: 23_000_000_000, rsi_value: 55, bollinger_signal: 'Nenhum', macd_signal: 'Nenhum', mme_cross: 'Nenhum', hilo_signal: 'Nenhum' },
  { symbol: 'ADAUSDT', name: 'Cardano', price: 0.4567, price_change_24h: -1.5, volume_24h: 400_000_000, market_cap: 16_000_000_000, rsi_value: 35, bollinger_signal: 'Nenhum', macd_signal: 'Cruzamento de Baixa', mme_cross: 'Nenhum', hilo_signal: 'Nenhum' },
  { symbol: 'AVAXUSDT', name: 'Avalanche', price: 36.70, price_change_24h: 6.8, volume_24h: 600_000_000, market_cap: 14_500_000_000, rsi_value: 68, bollinger_signal: 'Nenhum', macd_signal: 'Cruzamento de Alta', mme_cross: 'Nenhum', hilo_signal: 'HiLo Buy' },
  { symbol: 'LINKUSDT', name: 'Chainlink', price: 17.85, price_change_24h: 0.5, volume_24h: 350_000_000, market_cap: 10_500_000_000, rsi_value: 51, bollinger_signal: 'Nenhum', macd_signal: 'Nenhum', mme_cross: 'Nenhum', hilo_signal: 'Nenhum' },
];

const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD' }).format(value);
};

const formatLargeNumber = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 2 }).format(value);
};

const Tooltip = ({ text, children }: { text: string; children: React.ReactNode }) => (
    <div className="tooltip">
        {children}
        <span className="tooltiptext">{text}</span>
    </div>
);

const CryptoCard = ({ data }: { data: CryptoData }) => {
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


    const getRsiData = () => {
        if (data.rsi_value < 30) return { className: 'rsi-oversold', text: 'Sobrevenda', tooltip: INDICATOR_TOOLTIPS.rsi_value.oversold };
        if (data.rsi_value > 70) return { className: 'rsi-overbought', text: 'Sobrecompra', tooltip: INDICATOR_TOOLTIPS.rsi_value.overbought };
        return { className: 'rsi-neutral', text: 'Neutro', tooltip: INDICATOR_TOOLTIPS.rsi_value.neutral };
    };

    const rsiData = getRsiData();

    return (
        <div className="crypto-card">
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
                    <span className={`metric-value rsi-value ${rsiData.className}`}>{rsiData.text} ({data.rsi_value})</span>
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

const SettingsModal = ({
    isOpen,
    onClose,
    alertConfigs,
    onConfigChange
}: {
    isOpen: boolean;
    onClose: () => void;
    alertConfigs: AlertConfigs;
    onConfigChange: (symbol: string, alertType: string, newConfig: AlertConfig) => void;
}) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCryptoSymbol, setSelectedCryptoSymbol] = useState<string | null>(null);

    useEffect(() => {
        if (!isOpen) {
            // Reset state when modal is closed
            setTimeout(() => {
                setSelectedCryptoSymbol(null);
                setSearchTerm('');
            }, 300); // Delay to allow for closing animation
        }
    }, [isOpen]);

    const filteredCryptos = useMemo(() => {
        if (!searchTerm.trim()) {
            return ALL_MOCK_CRYPTO_DATA;
        }
        const lowercasedFilter = searchTerm.toLowerCase().trim();
        return ALL_MOCK_CRYPTO_DATA.filter(
            crypto =>
                crypto.name.toLowerCase().includes(lowercasedFilter) ||
                crypto.symbol.toLowerCase().replace('usdt', '').includes(lowercasedFilter)
        );
    }, [searchTerm]);

    const selectedCrypto = useMemo(() => {
        if (!selectedCryptoSymbol) return null;
        return ALL_MOCK_CRYPTO_DATA.find(c => c.symbol === selectedCryptoSymbol);
    }, [selectedCryptoSymbol]);


    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    {selectedCrypto && (
                        <button onClick={() => setSelectedCryptoSymbol(null)} className="back-button" aria-label="Voltar">
                            &larr;
                        </button>
                    )}
                    <h2 className="modal-title">
                        {selectedCrypto ? `${selectedCrypto.name} (${selectedCrypto.symbol.replace('USDT', '')})` : 'Gerenciar Alertas'}
                    </h2>
                    <button onClick={onClose} className="close-button" aria-label="Fechar">&times;</button>
                </div>

                {selectedCrypto ? (
                    <div className="modal-body">
                        <h4 className="settings-group-title">Selecione os Alertas</h4>
                        <div className="settings-group">
                            {Object.entries(ALERT_DEFINITIONS).map(([alertType, alertDef]) => {
                                const config = alertConfigs[selectedCrypto.symbol]?.[alertType] ?? DEFAULT_ALERT_CONFIG;
                                return (
                                    <div key={alertType} className="alert-setting-item">
                                        <div className="alert-setting-label">
                                            <span>{alertDef.name}</span>
                                            <small>{alertDef.description}</small>
                                        </div>
                                        <div className="alert-setting-controls">
                                            <label className="switch">
                                                <input
                                                    type="checkbox"
                                                    checked={config.enabled}
                                                    onChange={(e) => onConfigChange(selectedCrypto.symbol, alertType, { ...config, enabled: e.target.checked })}
                                                />
                                                <span className="slider round"></span>
                                            </label>
                                            <select
                                                value={config.cooldown}
                                                onChange={(e) => onConfigChange(selectedCrypto.symbol, alertType, { ...config, cooldown: Number(e.target.value) })}
                                                disabled={!config.enabled}
                                                aria-label={`Cooldown para ${alertDef.name}`}
                                            >
                                                {COOLDOWN_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                                            </select>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ) : (
                    <>
                         <div className="modal-search-container">
                            <input
                                type="search"
                                placeholder="Buscar cripto por nome ou símbolo..."
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                className="modal-search-input"
                                aria-label="Buscar criptomoeda"
                            />
                        </div>
                        <div className="modal-body">
                           <div className="crypto-selection-list">
                                {filteredCryptos.length > 0 ? (
                                    filteredCryptos.map(crypto => (
                                        <button key={crypto.symbol} className="crypto-selection-item" onClick={() => setSelectedCryptoSymbol(crypto.symbol)}>
                                            <span>{crypto.name} <span className="crypto-symbol-light">({crypto.symbol.replace('USDT', '')})</span></span>
                                            <span className="chevron">&rsaquo;</span>
                                        </button>
                                    ))
                                ) : (
                                    <p className="no-results-message">Nenhuma criptomoeda encontrada para "{searchTerm}".</p>
                                )}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};


const AlertsPanel = ({ isOpen, onClose, alerts, onClearAlerts }) => {
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

const App = () => {
    const [cryptoData, setCryptoData] = useState<CryptoData[]>(ALL_MOCK_CRYPTO_DATA);
    const [sortKey, setSortKey] = useState<keyof CryptoData | 'symbol'>('market_cap');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [mutedAlerts, setMutedAlerts] = useState<MutedAlert[]>([]);
    const [isSettingsModalOpen, setSettingsModalOpen] = useState(false);
    const [isAlertsPanelOpen, setAlertsPanelOpen] = useState(false);

    const [alertConfigs, setAlertConfigs] = useState<AlertConfigs>(() => {
        try {
            const savedConfigs = localStorage.getItem('cryptoAlertConfigs');
            return savedConfigs ? JSON.parse(savedConfigs) : {};
        } catch (error) {
            console.error("Failed to parse alert configs from localStorage", error);
            return {};
        }
    });

    const handleConfigChange = (symbol: string, alertType: string, newConfig: AlertConfig) => {
        setAlertConfigs(prev => {
            const newConfigs = {
                ...prev,
                [symbol]: {
                    ...prev[symbol],
                    [alertType]: newConfig,
                }
            };
            localStorage.setItem('cryptoAlertConfigs', JSON.stringify(newConfigs));
            return newConfigs;
        });
    };

    const sortedData = useMemo(() => {
        const sorted = [...cryptoData].sort((a, b) => {
            if (a[sortKey] < b[sortKey]) return sortOrder === 'asc' ? -1 : 1;
            if (a[sortKey] > b[sortKey]) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });
        return sorted;
    }, [cryptoData, sortKey, sortOrder]);


    useEffect(() => {
        const interval = setInterval(() => {
            setCryptoData(prevData =>
                prevData.map(coin => {
                    const priceChange = coin.price * (Math.random() - 0.5) * 0.01; // up to 0.5% change
                    const newPrice = Math.max(0, coin.price + priceChange);
                    return { ...coin, lastPrice: coin.price, price: newPrice };
                })
            );
        }, 2000); // Update every 2 seconds

        return () => clearInterval(interval);
    }, []);

    const triggerAlert = useCallback((symbol: string, alertType: string, data: CryptoData) => {
        const now = Date.now();
        const isMuted = mutedAlerts.some(m => m.symbol === symbol && m.alertType === alertType && m.muteUntil > now);
        if (isMuted) return;

        const config = alertConfigs[symbol]?.[alertType] ?? DEFAULT_ALERT_CONFIG;
        if (!config.enabled) return;

        const newAlert: Alert = {
            id: `${symbol}-${alertType}-${now}`,
            symbol,
            condition: ALERT_DEFINITIONS[alertType].name,
            description: ALERT_DEFINITIONS[alertType].description,
            timestamp: new Date().toLocaleTimeString('pt-BR'),
            snapshot: data,
        };

        setAlerts(prev => [newAlert, ...prev]);
        setMutedAlerts(prev => [...prev.filter(m => m.muteUntil > now), { symbol, alertType, muteUntil: now + config.cooldown * 1000 }]);

    }, [alertConfigs, mutedAlerts]);


    useEffect(() => {
        cryptoData.forEach(data => {
            if (data.rsi_value < 30) triggerAlert(data.symbol, 'RSI_SOBREVENDA', data);
            if (data.rsi_value > 70) triggerAlert(data.symbol, 'RSI_SOBRECOMPRA', data);
            if (data.hilo_signal === 'HiLo Buy') triggerAlert(data.symbol, 'HILO_COMPRA', data);
            if (data.mme_cross === 'Cruz Dourada') triggerAlert(data.symbol, 'CRUZ_DOURADA', data);
            if (data.mme_cross === 'Cruz da Morte') triggerAlert(data.symbol, 'CRUZ_DA_MORTE', data);
            if (data.macd_signal === 'Cruzamento de Alta') triggerAlert(data.symbol, 'MACD_ALTA', data);
            if (data.macd_signal === 'Cruzamento de Baixa') triggerAlert(data.symbol, 'MACD_BAIXA', data);
        });
    }, [cryptoData, triggerAlert]);

    return (
        <div className="app-container">
            <header className="app-header">
                <div className="header-top">
                    <h1 className="header-title">Crypto Monitor Pro</h1>
                     <div className="header-actions">
                        <div className="alerts-button-container">
                             <button className="manage-button" onClick={() => setAlertsPanelOpen(true)}>
                                Notificações
                             </button>
                             {alerts.length > 0 && <span className="alert-badge">{alerts.length}</span>}
                        </div>
                        <button className="manage-button" onClick={() => setSettingsModalOpen(true)}>
                            Gerenciar Alertas
                        </button>
                    </div>
                </div>
                <div className="header-status-bar">
                    <div className="status-item"><span className="label">Moedas:</span><span className="value">{cryptoData.length}</span></div>
                    <div className="status-item"><span className="label">Capitalização Total:</span><span className="value">{formatLargeNumber(cryptoData.reduce((acc, c) => acc + c.market_cap, 0))}</span></div>
                    <div className="status-item"><span className="label">Dominância BTC:</span><span className="value btc-dominance">45.8%</span></div>
                    <div className="status-item"><span className="label">Status API:</span><span className="api-ok">OK</span></div>
                </div>
            </header>
            <main className="main-content">
                <div className="content-header">
                    <h2 className="content-title">Visão Geral do Mercado</h2>
                    <div className="content-actions">
                         <div className="sort-container">
                            <label htmlFor="sort-select">Ordenar por:</label>
                            <select
                                id="sort-select"
                                value={sortKey}
                                onChange={(e) => setSortKey(e.target.value as keyof CryptoData | 'symbol')}
                            >
                                <option value="market_cap">Capitalização de Mercado</option>
                                <option value="price">Preço</option>
                                <option value="price_change_24h">Variação 24h</option>
                                <option value="volume_24h">Volume 24h</option>
                                <option value="symbol">Nome</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div className="crypto-grid">
                    {sortedData.map(crypto => (
                        <CryptoCard key={crypto.symbol} data={crypto} />
                    ))}
                </div>
            </main>
            <SettingsModal
                isOpen={isSettingsModalOpen}
                onClose={() => setSettingsModalOpen(false)}
                alertConfigs={alertConfigs}
                onConfigChange={handleConfigChange}
            />
            <AlertsPanel
                isOpen={isAlertsPanelOpen}
                onClose={() => setAlertsPanelOpen(false)}
                alerts={alerts}
                onClearAlerts={() => setAlerts([])}
            />
        </div>
    );
};

const root = createRoot(document.getElementById('root')!);
root.render(<App />);