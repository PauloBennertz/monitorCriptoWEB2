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

type BasicCoin = Pick<CryptoData, 'symbol' | 'name'>;

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


const API_BASE_URL = 'http://localhost:8000';

// --- HELPER FUNCTIONS ---
const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD' }).format(value);
};

const formatLargeNumber = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 2 }).format(value);
};

const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
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
    onConfigChange,
    allCoins,
    monitoredCoins,
    onUpdateCoin,
}: {
    isOpen: boolean;
    onClose: () => void;
    alertConfigs: AlertConfigs;
    onConfigChange: (symbol: string, alertType: string, newConfig: AlertConfig) => void;
    allCoins: BasicCoin[];
    monitoredCoins: CryptoData[];
    onUpdateCoin: (symbol: string, action: 'add' | 'remove') => void;
}) => {
    const [view, setView] = useState<'list' | 'add' | 'config'>('list');
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCryptoSymbol, setSelectedCryptoSymbol] = useState<string | null>(null);

    useEffect(() => {
        if (!isOpen) {
            setTimeout(() => {
                setView('list');
                setSelectedCryptoSymbol(null);
                setSearchTerm('');
            }, 300);
        }
    }, [isOpen]);

    const monitoredSymbols = useMemo(() => new Set(monitoredCoins.map(c => c.symbol)), [monitoredCoins]);

    const filteredAllCoins = useMemo(() => {
        if (!searchTerm.trim()) return [];
        const lowercasedFilter = searchTerm.toLowerCase().trim();
        return allCoins.filter(
            crypto =>
                crypto.name.toLowerCase().includes(lowercasedFilter) ||
                crypto.symbol.toLowerCase().replace('usdt', '').includes(lowercasedFilter)
        );
    }, [searchTerm, allCoins]);

    const selectedCrypto = useMemo(() => {
        if (!selectedCryptoSymbol) return null;
        return allCoins.find(c => c.symbol === selectedCryptoSymbol);
    }, [selectedCryptoSymbol, allCoins]);

    const handleSelectCrypto = (symbol: string) => {
        setSelectedCryptoSymbol(symbol);
        setView('config');
    };

    const handleBack = () => {
        if (view === 'config') {
            setSelectedCryptoSymbol(null);
            setView('list');
        } else if (view === 'add') {
            setView('list');
        }
    };

    if (!isOpen) return null;

    const renderContent = () => {
        if (view === 'config' && selectedCrypto) {
            return (
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
            );
        }

        if (view === 'add') {
            return (
                <>
                    <div className="modal-search-container">
                        <input
                            type="search"
                            placeholder="Buscar por nome ou símbolo..."
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            className="modal-search-input"
                            aria-label="Buscar criptomoeda"
                            autoFocus
                        />
                    </div>
                    <div className="modal-body">
                        <div className="crypto-selection-list">
                            {filteredAllCoins.length > 0 ? (
                                filteredAllCoins.map(crypto => (
                                    <div key={crypto.symbol} className="crypto-selection-item add-item">
                                        <span>{crypto.name} <span className="crypto-symbol-light">({crypto.symbol.replace('USDT', '')})</span></span>
                                        {monitoredSymbols.has(crypto.symbol) ? (
                                            <span className="add-status">Adicionado</span>
                                        ) : (
                                            <button className="add-button" onClick={() => onUpdateCoin(crypto.symbol, 'add')}>Adicionar</button>
                                        )}
                                    </div>
                                ))
                            ) : (
                                searchTerm && <p className="no-results-message">Nenhuma criptomoeda encontrada para "{searchTerm}".</p>
                            )}
                        </div>
                    </div>
                </>
            );
        }

        // Default view: 'list'
        return (
            <div className="modal-body">
                <div className="crypto-selection-list">
                    {monitoredCoins.map(crypto => (
                        <div key={crypto.symbol} className="crypto-selection-item managed-item">
                            <span>{crypto.name} <span className="crypto-symbol-light">({crypto.symbol.replace('USDT', '')})</span></span>
                            <div className="managed-item-buttons">
                                <button className="configure-button" onClick={() => handleSelectCrypto(crypto.symbol)}>Configurar Alertas</button>
                                <button className="remove-button" onClick={() => onUpdateCoin(crypto.symbol, 'remove')}>Remover</button>
                            </div>
                        </div>
                    ))}
                </div>
                <div className="modal-footer">
                    <button className="add-new-button" onClick={() => setView('add')}>
                        + Adicionar Nova Moeda
                    </button>
                </div>
            </div>
        );
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    {view !== 'list' && (
                        <button onClick={handleBack} className="back-button" aria-label="Voltar">
                            &larr;
                        </button>
                    )}
                    <h2 className="modal-title">
                        {view === 'config' && selectedCrypto ? `Configurar ${selectedCrypto.name}` :
                         view === 'add' ? 'Adicionar Moeda' :
                         'Moedas Monitoradas'}
                    </h2>
                    <button onClick={onClose} className="close-button" aria-label="Fechar">&times;</button>
                </div>
                {renderContent()}
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
    const [cryptoData, setCryptoData] = useState<CryptoData[]>([]);
    const [allCoins, setAllCoins] = useState<BasicCoin[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sortKey, setSortKey] = useState<keyof CryptoData | 'symbol'>('market_cap');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [mutedAlerts, setMutedAlerts] = useState<MutedAlert[]>([]);
    const [isSettingsModalOpen, setSettingsModalOpen] = useState(false);
    const [isAlertsPanelOpen, setAlertsPanelOpen] = useState(false);
    const [alertConfigs, setAlertConfigs] = useState<AlertConfigs>({});
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [secondsToNextUpdate, setSecondsToNextUpdate] = useState(180);
    const REFRESH_INTERVAL_SECONDS = 180; // 3 minutes

    const fetchCryptoData = useCallback(async (isInitialLoad = false) => {
        if (isInitialLoad) {
            setIsLoading(true);
        }
        try {
            const configRes = await fetch(`${API_BASE_URL}/api/alert_configs`);
            if (!configRes.ok) throw new Error('Failed to fetch configuration');
            const config = await configRes.json();

            setAlertConfigs(prevAlertConfigs => {
                const newAlertConfigs: AlertConfigs = {};
                if (config.cryptos_to_monitor) {
                    config.cryptos_to_monitor.forEach((crypto: any) => {
                        if (!crypto.alert_config || !crypto.alert_config.conditions) return;
                        const symbol = crypto.symbol;
                        newAlertConfigs[symbol] = {};
                        const conditions = crypto.alert_config.conditions;
                        const alertKeyMapping: { [key: string]: string } = {
                            'RSI_SOBREVENDA': 'rsi_sobrevendido', 'RSI_SOBRECOMPRA': 'rsi_sobrecomprado', 'HILO_COMPRA': 'hilo_compra',
                            'CRUZ_DOURADA': 'mme_cruz_dourada', 'CRUZ_DA_MORTE': 'mme_cruz_morte', 'MACD_ALTA': 'macd_cruz_alta', 'MACD_BAIXA': 'macd_cruz_baixa',
                        };
                        Object.entries(alertKeyMapping).forEach(([feKey, beKey]) => {
                            if (conditions[beKey]) {
                                newAlertConfigs[symbol][feKey] = {
                                    enabled: conditions[beKey].enabled,
                                    cooldown: prevAlertConfigs[symbol]?.[feKey]?.cooldown ?? DEFAULT_ALERT_CONFIG.cooldown,
                                };
                            }
                        });
                    });
                }
                return newAlertConfigs;
            });

            const symbolsToMonitor = config.cryptos_to_monitor.map((c: any) => c.symbol);

            if (symbolsToMonitor.length > 0) {
                const query = new URLSearchParams();
                symbolsToMonitor.forEach((s: string) => query.append('symbols', s));
                const dataRes = await fetch(`${API_BASE_URL}/api/crypto_data?${query.toString()}`);
                if (!dataRes.ok) throw new Error(`Failed to fetch crypto data: ${dataRes.statusText}`);
                const newData: CryptoData[] = await dataRes.json();

                setCryptoData(prevData => {
                    const prevDataMap = new Map(prevData.map(d => [d.symbol, d]));
                    return newData.map(d => ({ ...d, lastPrice: prevDataMap.get(d.symbol)?.price ?? d.price }));
                });
                localStorage.setItem('cryptoDataCache', JSON.stringify(newData));
            } else {
                setCryptoData([]);
                localStorage.removeItem('cryptoDataCache');
            }

            const fetchTime = new Date();
            setLastUpdated(fetchTime);
            localStorage.setItem('lastFetchTimestamp', fetchTime.getTime().toString());

            if (isInitialLoad) {
                const allCoinsRes = await fetch(`${API_BASE_URL}/api/all_tradable_coins`);
                if (!allCoinsRes.ok) throw new Error('Failed to fetch all tradable coins');
                const allCoinsData: string[] = await allCoinsRes.json();
                setAllCoins(allCoinsData.map(symbol => ({ symbol, name: symbol.replace('USDT', '') })));
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
            const finalMessage = `Falha ao buscar dados do mercado. Pode ser um problema com a API externa ou sua conexão. Detalhes: ${errorMessage}`;
            setError(finalMessage);
            console.error(err);
        } finally {
            if (isInitialLoad) {
                setIsLoading(false);
            }
        }
    }, []);

    useEffect(() => {
        let timeoutId: NodeJS.Timeout | undefined;
        let intervalId: NodeJS.Timeout | undefined;

        const startFetchingLoop = (delay: number) => {
            timeoutId = setTimeout(() => {
                fetchCryptoData(false);
                intervalId = setInterval(() => fetchCryptoData(false), REFRESH_INTERVAL_SECONDS * 1000);
            }, delay);
        };

        const cachedDataJSON = localStorage.getItem('cryptoDataCache');
        const cachedTimestamp = localStorage.getItem('lastFetchTimestamp');

        if (cachedDataJSON && cachedTimestamp) {
            const lastFetchTime = parseInt(cachedTimestamp, 10);
            const now = new Date().getTime();
            const ageInSeconds = (now - lastFetchTime) / 1000;

            if (ageInSeconds < REFRESH_INTERVAL_SECONDS) {
                console.log("Loading data from fresh cache.");
                setCryptoData(JSON.parse(cachedDataJSON));
                setLastUpdated(new Date(lastFetchTime));
                setIsLoading(false);
                const timeToWait = (REFRESH_INTERVAL_SECONDS - ageInSeconds) * 1000;
                startFetchingLoop(timeToWait);
            } else {
                fetchCryptoData(true); // Fetch immediately if cache is stale
                startFetchingLoop(REFRESH_INTERVAL_SECONDS * 1000);
            }
        } else {
            fetchCryptoData(true); // Fetch immediately if no cache
            startFetchingLoop(REFRESH_INTERVAL_SECONDS * 1000);
        }

        return () => {
            if (timeoutId) clearTimeout(timeoutId);
            if (intervalId) clearInterval(intervalId);
        };
    }, [fetchCryptoData]);

    useEffect(() => {
        const timerId = setInterval(() => {
            if (lastUpdated) {
                const now = new Date();
                const secondsSinceUpdate = Math.floor((now.getTime() - lastUpdated.getTime()) / 1000);
                const secondsRemaining = REFRESH_INTERVAL_SECONDS - secondsSinceUpdate;
                setSecondsToNextUpdate(secondsRemaining > 0 ? secondsRemaining : 0);
            }
        }, 1000);
        return () => clearInterval(timerId);
    }, [lastUpdated]);


    const handleConfigChange = (symbol: string, alertType: string, newConfig: AlertConfig) => {
        setAlertConfigs(prev => {
            const newConfigs = {
                ...prev,
                [symbol]: {
                    ...prev[symbol],
                    [alertType]: newConfig,
                }
            };
            console.log("Config changed, would post to backend:", newConfigs);
            // TODO: POST this to the backend to save the entire config
            return newConfigs;
        });
    };

    const handleUpdateMonitoredCoin = useCallback(async (symbol: string, action: 'add' | 'remove') => {
        try {
            let response;
            if (action === 'add') {
                response = await fetch(`${API_BASE_URL}/api/monitored_coins`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol }),
                });
            } else { // remove
                response = await fetch(`${API_BASE_URL}/api/monitored_coins/${symbol}`, {
                    method: 'DELETE',
                });
            }

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update monitored coin');
            }

            // Refresh all data to reflect the change
            await fetchCryptoData(true);

        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
            setError(errorMessage); // Display error to the user
            console.error(`Failed to ${action} coin ${symbol}:`, err);
        }
    }, [fetchCryptoData]);

    const sortedData = useMemo(() => {
        return [...cryptoData].sort((a, b) => {
            if (a[sortKey] < b[sortKey]) return sortOrder === 'asc' ? -1 : 1;
            if (a[sortKey] > b[sortKey]) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });
    }, [cryptoData, sortKey, sortOrder]);

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

    if (isLoading) {
        return <div className="loading-container">Carregando dados do mercado...</div>;
    }

    if (error) {
        return <div className="error-container">Erro ao carregar dados: {error}</div>;
    }

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
                    <div className="status-item"><span className="label">Dominância BTC:</span><span className="value btc-dominance">45.8%</span></div>
                    <div className="status-item"><span className="label">Status API:</span><span className="api-ok">OK</span></div>
                    <div className="status-item"><span className="label">Última Atualização:</span><span className="value">{lastUpdated ? lastUpdated.toLocaleTimeString('pt-BR') : 'Carregando...'}</span></div>
                    <div className="status-item"><span className="label">Próxima em:</span><span className="value">{formatTime(secondsToNextUpdate)}</span></div>
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
                allCoins={allCoins}
                monitoredCoins={cryptoData}
                onUpdateCoin={handleUpdateMonitoredCoin}
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