import React, { useState, useEffect, useCallback, useMemo } from 'react';
import CryptoCard from './components/CryptoCard';
import SettingsModal from './components/SettingsModal';
import AlertsPanel from './components/AlertsPanel';
import AlertHistoryPanel from './components/AlertHistoryPanel';
import BacktesterPanel from './components/BacktesterPanel';
import CryptoDetailModal from './components/CryptoDetailModal';
import AlertTicker from './components/AlertTicker'; // Import the new component
import './components/AlertTicker.css'; // Import the new stylesheet
import { CryptoData, Alert, MutedAlert, AlertConfigs, AlertConfig, BasicCoin, API_BASE_URL, ALERT_DEFINITIONS, DEFAULT_ALERT_CONFIG, MarketAnalysisConfig } from './types';
import { formatTime, countActiveIndicators } from './utils';

const App = () => {
    const [cryptoData, setCryptoData] = useState<CryptoData[]>([]);
    const [allCoins, setAllCoins] = useState<BasicCoin[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sortKey, setSortKey] = useState<keyof CryptoData | 'symbol' | 'active_alerts'>('market_cap');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
    const [mutedAlerts, setMutedAlerts] = useState<MutedAlert[]>([]);
    const [isSettingsModalOpen, setSettingsModalOpen] = useState(false);
    const [isAlertsPanelOpen, setAlertsPanelOpen] = useState(false);
    const [isHistoryPanelOpen, setHistoryPanelOpen] = useState(false);
    const [isBacktesterPanelOpen, setBacktesterPanelOpen] = useState(false);
    const [alertConfigs, setAlertConfigs] = useState<AlertConfigs>({});
    const [displayLimit, setDisplayLimit] = useState(20);
    const [gridLayoutColumns, setGridLayoutColumns] = useState(5);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [secondsToNextUpdate, setSecondsToNextUpdate] = useState(180);
    const [btcDominance, setBtcDominance] = useState<number | null>(null);
    const [isBlinkVisible, setIsBlinkVisible] = useState(true);
    const [selectedCoin, setSelectedCoin] = useState<CryptoData | null>(null);
    const REFRESH_INTERVAL_SECONDS = 180; // 3 minutes

    const handleCardClick = (coin: CryptoData) => {
        setSelectedCoin(coin);
    };

    const handleCloseModal = () => {
        setSelectedCoin(null);
    };

    useEffect(() => {
        const blinkInterval = setInterval(() => {
            setIsBlinkVisible(prev => !prev);
        }, 1500); // Sync with CSS animation time
        return () => clearInterval(blinkInterval);
    }, []);

    const fetchGlobalData = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/global_data`);
            if (!res.ok) throw new Error('Failed to fetch global market data');
            const data = await res.json();
            setBtcDominance(data.btc_dominance);
        } catch (err) {
            console.error("Failed to fetch BTC dominance:", err);
            // Non-fatal, so we don't set the main error state
        }
    }, []);

    const fetchCryptoData = useCallback(async (isInitialLoad = false) => {
        if (isInitialLoad) {
            setIsLoading(true);
        }

        // Fetch all tradable coins for the search modal (independent)
        if (isInitialLoad) {
            try {
                const allCoinsRes = await fetch(`${API_BASE_URL}/api/all_tradable_coins`);
                if (!allCoinsRes.ok) throw new Error('Failed to fetch all tradable coins');
                const allCoinsData: BasicCoin[] = await allCoinsRes.json();
                // A API agora retorna objetos completos, então podemos simplesmente usá-los.
                // Apenas garantimos que o nome seja capitalizado para consistência.
                const formattedCoins = allCoinsData.map(coin => ({
                    ...coin,
                    name: coin.name.charAt(0).toUpperCase() + coin.name.slice(1)
                }));
                setAllCoins(formattedCoins);
            } catch (err) {
                console.error("Could not fetch all tradable coins list:", err);
                // Non-fatal, the user just won't be able to add new coins.
            }
        }

        // Fetch main monitored data
        try {
            const configRes = await fetch(`${API_BASE_URL}/api/alert_configs`);
            if (!configRes.ok) throw new Error('Failed to fetch configuration');
            const config = await configRes.json();

            // Set display limit from fetched config, with a fallback
            const currentDisplayLimit = config.market_analysis_config?.display_limit ?? 20;
            setDisplayLimit(currentDisplayLimit);

            // Set grid layout from fetched config, with a fallback
            const currentGridLayout = config.market_analysis_config?.grid_layout_columns ?? 5;
            setGridLayoutColumns(currentGridLayout);

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
                                    blinking: conditions[beKey].blinking ?? DEFAULT_ALERT_CONFIG.blinking,
                                };
                            }
                        });
                    });
                }
                return newAlertConfigs;
            });

            const symbolsToMonitorRaw = config.cryptos_to_monitor.map((c: any) => c.symbol);
            // Slice the symbols to monitor based on the display limit
            const symbolsToMonitor = currentDisplayLimit > 0 ? symbolsToMonitorRaw.slice(0, currentDisplayLimit) : symbolsToMonitorRaw;


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
                setError(null); // Clear previous errors on success
            } else {
                setCryptoData([]);
                localStorage.removeItem('cryptoDataCache');
            }

            const fetchTime = new Date();
            setLastUpdated(fetchTime);
            localStorage.setItem('lastFetchTimestamp', fetchTime.getTime().toString());

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
        // Fetch global data once on initial load, independently of the main data fetch cycle.
        fetchGlobalData();
    }, [fetchGlobalData]);

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
                setIsLoading(false); // We can still show cached data while fetching new
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


    const handleConfigChange = useCallback(async (symbol: string, alertType: string, newConfig: AlertConfig) => {
        // Optimistic UI Update
        setAlertConfigs(prev => ({
            ...prev,
            [symbol]: {
                ...prev[symbol],
                [alertType]: newConfig,
            }
        }));

        try {
            // 1. Fetch the entire current configuration from the backend
            const configRes = await fetch(`${API_BASE_URL}/api/alert_configs`);
            if (!configRes.ok) throw new Error('Failed to fetch current configuration');
            const fullConfig = await configRes.json();

            // 2. Find the specific coin to update
            const coinToUpdate = fullConfig.cryptos_to_monitor.find((c: any) => c.symbol === symbol);
            if (!coinToUpdate) {
                throw new Error(`Coin ${symbol} not found in backend configuration.`);
            }

            // 3. Get the backend key for the alert type
            const backendKey = ALERT_DEFINITIONS[alertType]?.backendKey;
            if (!backendKey) {
                throw new Error(`Invalid alert type: ${alertType}`);
            }

            // 4. Update the 'enabled' and 'blinking' status for the specific condition
            if (coinToUpdate.alert_config.conditions[backendKey]) {
                coinToUpdate.alert_config.conditions[backendKey].enabled = newConfig.enabled;
                coinToUpdate.alert_config.conditions[backendKey].blinking = newConfig.blinking;
            } else {
                // If the condition doesn't exist for some reason, create it
                coinToUpdate.alert_config.conditions[backendKey] = {
                    enabled: newConfig.enabled,
                    blinking: newConfig.blinking
                };
            }

            // 5. POST the entire modified configuration back to the backend
            const saveRes = await fetch(`${API_BASE_URL}/api/alert_configs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(fullConfig),
            });

            if (!saveRes.ok) {
                const errorData = await saveRes.json();
                throw new Error(errorData.detail || 'Failed to save configuration');
            }

            console.log(`Successfully saved configuration for ${symbol}`);
            // Optionally, show a success message to the user

        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
            setError(`Failed to save settings: ${errorMessage}`); // Show error to the user
            console.error("Error saving configuration:", err);
            // Optionally, revert the optimistic UI update here
            fetchCryptoData(true); // Refetch to get the real state from the server
        }
    }, [fetchCryptoData]);

    const handleUpdateMonitoredCoin = useCallback(async (symbol: string, action: 'add' | 'remove') => {
        try {
            if (action === 'add') {
                // Optimistically add a loading placeholder
                const coinName = allCoins.find(c => c.symbol === symbol)?.name ?? symbol;
                const placeholder: CryptoData = {
                    symbol,
                    name: coinName,
                    price: 0,
                    price_change_24h: 0,
                    volume_24h: 0,
                    market_cap: 0,
                    rsi_value: 50,
                    bollinger_signal: 'Nenhum',
                    macd_signal: 'Nenhum',
                    mme_cross: 'Nenhum',
                    hilo_signal: 'Nenhum',
                    isLoading: true,
                };
                setCryptoData(prevData => [...prevData, placeholder]);

                const response = await fetch(`${API_BASE_URL}/api/monitored_coins`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to add monitored coin');
                }

                // Fetch data in the background to replace the placeholder
                await fetchCryptoData(false);

            } else { // remove
                // Optimistically remove the coin from the UI
                setCryptoData(prevData => prevData.filter(coin => coin.symbol !== symbol));
                setAlerts(prevAlerts => prevAlerts.filter(alert => alert.symbol !== symbol));

                const response = await fetch(`${API_BASE_URL}/api/monitored_coins/${symbol}`, {
                    method: 'DELETE',
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    // If the API call fails, revert the change by refetching
                    fetchCryptoData(true);
                    throw new Error(errorData.detail || 'Failed to remove monitored coin');
                }
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
            setError(errorMessage); // Display error to the user
            console.error(`Failed to ${action} coin ${symbol}:`, err);
            // On any error, refresh to sync with the server's true state
            fetchCryptoData(true);
        }
    }, [fetchCryptoData, allCoins]);

    const handleDisplayLimitChange = useCallback(async (newLimit: number) => {
        // Optimistic UI Update
        setDisplayLimit(newLimit);

        try {
            const configRes = await fetch(`${API_BASE_URL}/api/alert_configs`);
            if (!configRes.ok) throw new Error('Failed to fetch current configuration for update');
            const fullConfig = await configRes.json();

            // Ensure market_analysis_config exists
            if (!fullConfig.market_analysis_config) {
                fullConfig.market_analysis_config = {};
            }
            fullConfig.market_analysis_config.display_limit = newLimit;

            const saveRes = await fetch(`${API_BASE_URL}/api/alert_configs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(fullConfig),
            });

            if (!saveRes.ok) {
                const errorData = await saveRes.json();
                throw new Error(errorData.detail || 'Failed to save display limit setting');
            }

            console.log(`Display limit successfully saved: ${newLimit}`);
            // Trigger a data refresh to apply the new limit immediately
            await fetchCryptoData(false);

        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
            setError(`Failed to save settings: ${errorMessage}`);
            console.error("Error saving display limit:", err);
            // Re-fetch to sync with the actual server state in case of error
            await fetchCryptoData(true);
        }
    }, [fetchCryptoData]);

    const handleGridLayoutChange = useCallback(async (newCols: number) => {
        setGridLayoutColumns(newCols); // Optimistic UI Update

        try {
            const configRes = await fetch(`${API_BASE_URL}/api/alert_configs`);
            if (!configRes.ok) throw new Error('Failed to fetch current configuration for update');
            const fullConfig = await configRes.json();

            if (!fullConfig.market_analysis_config) {
                fullConfig.market_analysis_config = {};
            }
            fullConfig.market_analysis_config.grid_layout_columns = newCols;

            const saveRes = await fetch(`${API_BASE_URL}/api/alert_configs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(fullConfig),
            });

            if (!saveRes.ok) {
                const errorData = await saveRes.json();
                throw new Error(errorData.detail || 'Failed to save grid layout setting');
            }
            console.log(`Grid layout successfully saved: ${newCols}`);
            // No need to refetch data, the CSS will update automatically
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
            setError(`Failed to save settings: ${errorMessage}`);
            console.error("Error saving grid layout:", err);
            // Re-fetch config to revert optimistic update on error
            const configRes = await fetch(`${API_BASE_URL}/api/alert_configs`);
            const fullConfig = await configRes.json();
            setGridLayoutColumns(fullConfig.market_analysis_config?.grid_layout_columns ?? 5);
        }
    }, []);

    const handleOpenBacktester = () => {
        setBacktesterPanelOpen(true);
    };

    const sortedData = useMemo(() => {
        return [...cryptoData].sort((a, b) => {
            if (sortKey === 'active_alerts') {
                const aAlerts = countActiveIndicators(a);
                const bAlerts = countActiveIndicators(b);
                if (aAlerts > bAlerts) return -1;
                if (aAlerts < bAlerts) return 1;
                // As a secondary sort, use market cap
                return b.market_cap - a.market_cap;
            }
            if (a[sortKey] < b[sortKey]) return sortOrder === 'asc' ? -1 : 1;
            if (a[sortKey] > b[sortKey]) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });
    }, [cryptoData, sortKey, sortOrder]);

    // --- Sound Synthesis Function ---
    const playSound = (type: 'golden' | 'death' | 'default') => {
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        if (!audioContext) return;

        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        gainNode.gain.setValueAtTime(0, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.05); // Fade in

        if (type === 'golden') {
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(523.25, audioContext.currentTime); // C5
            gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.8);
        } else if (type === 'death') {
            oscillator.type = 'sawtooth';
            oscillator.frequency.setValueAtTime(329.63, audioContext.currentTime); // E4
            gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.8);
        } else { // default
            oscillator.type = 'triangle';
            oscillator.frequency.setValueAtTime(440.00, audioContext.currentTime); // A4
            gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.5);
        }

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 1);
    };

    const triggerAlert = useCallback((symbol: string, alertType: string, data: CryptoData) => {
        const now = Date.now();
        const isMuted = mutedAlerts.some(m => m.symbol === symbol && m.alertType === alertType && m.muteUntil > now);
        if (isMuted) return;

        const config = alertConfigs[symbol]?.[alertType] ?? DEFAULT_ALERT_CONFIG;
        if (!config.enabled) return;

        // Play sound based on alert type
        if (alertType === 'CRUZ_DOURADA') {
            playSound('golden');
        } else if (alertType === 'CRUZ_DA_MORTE') {
            playSound('death');
        } else {
            // Uncomment the line below to enable a default sound for all other alerts
            // playSound('default');
        }

        const newAlert: Alert = {
            id: `${symbol}-${alertType}-${now}`,
            symbol,
            condition: ALERT_DEFINITIONS[alertType].name,
            description: ALERT_DEFINITIONS[alertType].description,
            timestamp: new Date().toISOString(),
            snapshot: data,
        };

        // Save to persistent history on the backend (fire and forget)
        fetch(`${API_BASE_URL}/api/alerts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newAlert),
        }).catch(err => {
            console.error("Failed to save alert to history:", err);
        });

        setAlerts(prev => [newAlert, ...prev]);
        setMutedAlerts(prev => [...prev.filter(m => m.muteUntil > now), { symbol, alertType, muteUntil: now + config.cooldown * 1000 }]);

    }, [alertConfigs, mutedAlerts]);


    useEffect(() => {
        cryptoData.forEach(data => {
            const activeAlerts: { type: string, data: CryptoData }[] = [];

            if (data.rsi_value < 30) activeAlerts.push({ type: 'RSI_SOBREVENDA', data });
            if (data.rsi_value > 70) activeAlerts.push({ type: 'RSI_SOBRECOMPRA', data });
            if (data.hilo_signal === 'HiLo Buy') activeAlerts.push({ type: 'HILO_COMPRA', data });
            if (data.mme_cross === 'Cruz Dourada') activeAlerts.push({ type: 'CRUZ_DOURADA', data });
            if (data.mme_cross === 'Cruz da Morte') activeAlerts.push({ type: 'CRUZ_DA_MORTE', data });
            if (data.macd_signal === 'Cruzamento de Alta') activeAlerts.push({ type: 'MACD_ALTA', data });
            if (data.macd_signal === 'Cruzamento de Baixa') activeAlerts.push({ type: 'MACD_BAIXA', data });

            activeAlerts.forEach(alert => {
                triggerAlert(data.symbol, alert.type, alert.data);
            });
        });
    }, [cryptoData, triggerAlert]);


    useEffect(() => {
        const fortyFiveMinutesAgo = new Date(Date.now() - 45 * 60 * 1000);
        const filtered = alerts.filter(alert => new Date(alert.timestamp) > fortyFiveMinutesAgo);
        setRecentAlerts(filtered);
    }, [alerts]);

    return (
        <div className="app-container">
            <AlertTicker alerts={recentAlerts} />
            <header className="app-header">
                <div className="header-top">
                    <h1 className="header-title">Crypto Monitor Pro</h1>
                     <div className="header-actions">
                        <button className="manage-button" onClick={() => setHistoryPanelOpen(true)}>
                            Histórico
                        </button>
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
                    <div className="status-item"><span className="label">Dominância BTC:</span><span className="value btc-dominance">{btcDominance ? `${btcDominance.toFixed(1)}%` : 'N/A'}</span></div>
                    <div className="status-item"><span className="label">Status API:</span><span className={error ? 'api-error' : 'api-ok'}>{error ? 'ERRO' : 'OK'}</span></div>
                    <div className="status-item"><span className="label">Última Atualização:</span><span className="value">{lastUpdated ? lastUpdated.toLocaleTimeString('pt-BR') : 'Carregando...'}</span></div>
                    <div className="status-item"><span className="label">Próxima em:</span><span className="value">{formatTime(secondsToNextUpdate)}</span></div>
                </div>
            </header>
            <main className="main-content">
                {isLoading ? (
                    <div className="loading-container">Carregando dados do mercado...</div>
                ) : error ? (
                    <div className="error-container">{error}</div>
                ) : (
                    <>
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
                                        <option value="active_alerts">Alertas Ativos</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div
                            className="crypto-grid"
                            style={{ '--grid-columns': gridLayoutColumns } as React.CSSProperties}
                        >
                            {sortedData.map(crypto => (
                                <CryptoCard
                                    key={crypto.symbol}
                                    data={crypto}
                                    isBlinkVisible={isBlinkVisible}
                                    onClick={handleCardClick}
                                />
                            ))}
                        </div>
                    </>
                )}
            </main>
            <SettingsModal
                isOpen={isSettingsModalOpen}
                onClose={() => setSettingsModalOpen(false)}
                alertConfigs={alertConfigs}
                onConfigChange={handleConfigChange}
                allCoins={allCoins}
                monitoredCoins={cryptoData}
                onUpdateCoin={handleUpdateMonitoredCoin}
                displayLimit={displayLimit}
                onDisplayLimitChange={handleDisplayLimitChange}
                gridLayoutColumns={gridLayoutColumns}
                onGridLayoutChange={handleGridLayoutChange}
            />
            <AlertsPanel
                isOpen={isAlertsPanelOpen}
                onClose={() => setAlertsPanelOpen(false)}
                alerts={alerts}
                onClearAlerts={() => setAlerts([])}
            />
            <AlertHistoryPanel
                isOpen={isHistoryPanelOpen}
                onClose={() => setHistoryPanelOpen(false)}
            />
            <BacktesterPanel
                isOpen={isBacktesterPanelOpen}
                onClose={() => setBacktesterPanelOpen(false)}
            />
            {selectedCoin && (
                <CryptoDetailModal
                    coin={selectedCoin}
                    onClose={handleCloseModal}
                />
            )}
        </div>
    );
};

export default App;
