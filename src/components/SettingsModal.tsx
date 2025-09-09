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
    displayLimit,
    onDisplayLimitChange,
    gridLayoutColumns,
    onGridLayoutChange,
}: {
    isOpen: boolean;
    onClose: () => void;
    alertConfigs: AlertConfigs;
    onConfigChange: (symbol: string, alertType: string, newConfig: AlertConfig) => void;
    allCoins: BasicCoin[];
    monitoredCoins: CryptoData[];
    onUpdateCoin: (symbol: string, action: 'add' | 'remove') => void;
    displayLimit: number;
    onDisplayLimitChange: (newLimit: number) => void;
    gridLayoutColumns: number;
    onGridLayoutChange: (newCols: number) => void;
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

        // Filtra a lista completa de moedas para remover as que já estão sendo monitoradas.
        const availableCoins = allCoins.filter(crypto =>
            !monitoredSymbols.has(`${crypto.symbol.toUpperCase()}USDT`)
        );

        // Se o campo de busca estiver vazio, mostra as primeiras 50 moedas da lista disponível.
        if (lowercasedFilter.length < 1) {
            return availableCoins.slice(0, 50);
        }

        // Se houver um termo de busca, filtra os resultados com base nesse termo.
        const results = availableCoins.filter(crypto => {
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
                <div className="settings-group">
                    <h4 className="settings-group-title">Configurações Gerais</h4>
                    <div className="alert-setting-item">
                        <div className="alert-setting-label">
                            <span>Moedas na Tela Principal</span>
                            <small>Limite o número de moedas exibidas para melhorar a performance.</small>
                        </div>
                        <div className="alert-setting-controls">
                            <select
                                className="control-item"
                                value={displayLimit}
                                onChange={(e) => onDisplayLimitChange(Number(e.target.value))}
                                aria-label="Número de moedas a exibir"
                            >
                                <option value={10}>10</option>
                                <option value={20}>20</option>
                                <option value={50}>50</option>
                                <option value={100}>100</option>
                                <option value={0}>Todas</option>
                            </select>
                        </div>
                    </div>
                    <div className="alert-setting-item">
                        <div className="alert-setting-label">
                            <span>Layout da Grade (Colunas)</span>
                            <small>Ajuste o número de colunas na grade principal.</small>
                        </div>
                        <div className="alert-setting-controls">
                            <select
                                className="control-item"
                                value={gridLayoutColumns}
                                onChange={(e) => onGridLayoutChange(Number(e.target.value))}
                                aria-label="Número de colunas na grade"
                            >
                                <option value={3}>3</option>
                                <option value={4}>4</option>
                                <option value={5}>5</option>
                                <option value={6}>6</option>
                                <option value={7}>7</option>
                                <option value={8}>8</option>
                            </select>
                        </div>
                    </div>
                </div>

                <hr style={{ borderColor: '#333', margin: '20px 0' }} />

                <h4 className="settings-group-title" style={{ marginBottom: '15px' }}>Moedas Monitoradas</h4>
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
