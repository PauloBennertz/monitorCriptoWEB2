import React, { useState, useEffect, useMemo } from 'react';
import { CryptoData, AlertConfigs, AlertConfig, BasicCoin, ALERT_DEFINITIONS, COOLDOWN_OPTIONS, DEFAULT_ALERT_CONFIG } from '../types';

/**
 * A modal for managing and configuring alerts for cryptocurrencies.
 *
 * @param {object} props - The component props.
 * @param {boolean} props.isOpen - Whether the modal is open.
 * @param {Function} props.onClose - The function to call when the modal is closed.
 * @param {AlertConfigs} props.alertConfigs - The current alert configurations.
 * @param {Function} props.onConfigChange - The function to call when an alert configuration is changed.
 * @param {BasicCoin[]} props.allCoins - The list of all available coins.
 * @param {CryptoData[]} props.monitoredCoins - The list of currently monitored coins.
 * @param {Function} props.onUpdateCoin - The function to call when a coin is added or removed from the monitored list.
 * @returns {JSX.Element | null} The rendered component, or null if it is not open.
 */
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
        const lowercasedFilter = searchTerm.toLowerCase().trim();

        // Se o campo de busca estiver vazio, não retorna nada para evitar sobrecarga.
        if (lowercasedFilter.length < 1) {
            return [];
        }

        const results = allCoins.filter(crypto => {
            const isMonitored = monitoredSymbols.has(`${crypto.symbol.toUpperCase()}USDT`);
            if (isMonitored) return false;

            return crypto.name.toLowerCase().includes(lowercasedFilter) ||
                   crypto.symbol.toLowerCase().includes(lowercasedFilter);
        });

        // Limita o número de resultados para 50 para manter a UI responsiva.
        return results.slice(0, 50);
    }, [searchTerm, allCoins, monitoredSymbols]);

    const selectedCrypto = useMemo(() => {
        if (!selectedCryptoSymbol) return null;
        // Find by the base symbol, ignoring 'USDT'
        return monitoredCoins.find(c => c.symbol === selectedCryptoSymbol);
    }, [selectedCryptoSymbol, monitoredCoins]);

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
                                        <div className="control-item">
                                            <label className="switch">
                                                <input
                                                    type="checkbox"
                                                    checked={config.enabled}
                                                    onChange={(e) => onConfigChange(selectedCrypto.symbol, alertType, { ...config, enabled: e.target.checked })}
                                                />
                                                <span className="slider round"></span>
                                            </label>
                                        </div>
                                        <div className="control-item">
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    className="blinking-checkbox"
                                                    checked={config.blinking ?? true}
                                                    disabled={!config.enabled}
                                                    onChange={(e) => onConfigChange(selectedCrypto.symbol, alertType, { ...config, blinking: e.target.checked })}
                                                />
                                                Piscar
                                            </label>
                                        </div>
                                        <div className="control-item">
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
                                    <div key={crypto.id} className="crypto-selection-item add-item">
                                        <span>{crypto.name} <span className="crypto-symbol-light">({crypto.symbol.toUpperCase()})</span></span>
                                        <button
                                            className="button button-add"
                                            onClick={() => onUpdateCoin(`${crypto.symbol.toUpperCase()}USDT`, 'add')}
                                        >
                                            Adicionar
                                        </button>
                                    </div>
                                ))
                            ) : (
                                searchTerm.trim().length > 0
                                    ? <p className="no-results-message">Nenhuma criptomoeda encontrada para "{searchTerm}".</p>
                                    : <p className="no-results-message">Digite para buscar uma moeda.</p>
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
                                <button className="button manage-button" onClick={() => handleSelectCrypto(crypto.symbol)}>Configurar Alertas</button>
                                <button className="button button-danger" onClick={() => onUpdateCoin(crypto.symbol, 'remove')}>Remover</button>
                            </div>
                        </div>
                    ))}
                </div>
                <div className="modal-footer">
                    <button className="button button-add" onClick={() => setView('add')}>
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

export default SettingsModal;
