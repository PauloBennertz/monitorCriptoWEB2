import React, { useState, useEffect, useMemo } from 'react';
import { CryptoData, AlertConfigs, AlertConfig, BasicCoin, ALERT_DEFINITIONS, COOLDOWN_OPTIONS, DEFAULT_ALERT_CONFIG } from '../types';

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
                                            <button className="button button-add" onClick={() => onUpdateCoin(crypto.symbol, 'add')}>Adicionar</button>
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
