import React, { useState, useEffect } from 'react';
import { Coin } from '../types'; // Keeping the import just in case 'Coin' is still needed for context, though 'coins' state is removed
import ResultsTable from './ResultsTable';
import HistoricalResultChart from './HistoricalResultChart'; // Import the chart component

// Basic styling for the panel - can be moved to a CSS file later
const panelStyles: React.CSSProperties = {
  position: 'fixed',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: '80%',
  maxWidth: '1000px',
  height: '80vh',
  backgroundColor: '#2c2c2c',
  border: '1px solid #555',
  borderRadius: '8px',
  boxShadow: '0 4px 15px rgba(0, 0, 0, 0.5)',
  zIndex: 1000,
  display: 'flex',
  flexDirection: 'column',
  padding: '20px',
  color: '#fff',
};

const closeButtonStyles: React.CSSProperties = {
  position: 'absolute',
  top: '10px',
  right: '10px',
  background: 'transparent',
  border: 'none',
  color: '#fff',
  fontSize: '24px',
  cursor: 'pointer',
};

interface HistoricalAnalysisPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// A simplified version of the main app's alert definitions for the form
const ALERT_OPTIONS = {
  rsi_sobrevendido: { name: 'RSI Sobrevendido', hasValue: true, defaultValue: 30 },
  rsi_sobrecomprado: { name: 'RSI Sobrecomprado', hasValue: true, defaultValue: 70 },
  hilo_compra: { name: 'HiLo Sinal de Compra', hasValue: false },
  hilo_venda: { name: 'HiLo Sinal de Venda', hasValue: false },
  mme_cruz_dourada: { name: 'MME Cruz Dourada', hasValue: false },
  mme_cruz_morte: { name: 'MME Cruz da Morte', hasValue: false },
  macd_cruz_alta: { name: 'MACD Cruz de Alta', hasValue: false },
  macd_cruz_baixa: { name: 'MACD Cruz de Baixa', hasValue: false },
};

const formContainerStyles: React.CSSProperties = {
  display: 'flex',
  gap: '20px',
  marginBottom: '20px',
};

const columnStyles: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
};

const HistoricalAnalysisPanel: React.FC<HistoricalAnalysisPanelProps> = ({ isOpen, onClose }) => {
  // REMOVIDO: const [coins, setCoins] = useState<Coin[]>([]);
  // ALTERADO: Inicializa com um par comum para dar o exemplo de formato.
  const [selectedCoin, setSelectedCoin] = useState<string>('BTCUSDT');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [alertConfig, setAlertConfig] = useState(() => {
    const initialConfig: any = {};
    Object.keys(ALERT_OPTIONS).forEach((key) => {
      const option = ALERT_OPTIONS[key as keyof typeof ALERT_OPTIONS];
      initialConfig[key] = {
        enabled: true,
        value: option.defaultValue,
      };
    });
    return initialConfig;
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchPerformed, setSearchPerformed] = useState<boolean>(false);
  const [showChart, setShowChart] = useState<boolean>(false);

  // REMOVIDO: useEffect para fetchCoins

  const handleAlertConfigChange = (key: string, field: 'enabled' | 'value', value: boolean | string) => {
    setAlertConfig(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: field === 'enabled' ? value : Number(value),
      },
    }));
  };

  const handleAnalysisSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setShowChart(false); // Hide chart on new analysis
    setIsLoading(true);
    setError(null);
    setResults([]);

    const backendAlertConfig = {
      conditions: Object.keys(alertConfig).reduce((acc, key) => {
        acc[key] = {
          enabled: alertConfig[key].enabled,
          ...(alertConfig[key].value !== undefined && { value: Number(alertConfig[key].value) })
        };
        return acc;
      }, {} as any),
    };

    try {
      const response = await fetch('http://localhost:8000/api/historical_alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: selectedCoin,
          start_date: startDate,
          end_date: endDate,
          alert_config: backendAlertConfig,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'An unknown error occurred');
      }

      const data = await response.json();
      setResults(data.alerts);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch analysis results.');
    } finally {
      setIsLoading(false);
      setSearchPerformed(true); // Mark that a search has been performed
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div style={panelStyles}>
      <button onClick={onClose} style={closeButtonStyles}>&times;</button>
      <h2>Análise Histórica de Alertas</h2>

      <form onSubmit={handleAnalysisSubmit}>
        <div style={formContainerStyles}>
          <div style={columnStyles}>
            <label>Moeda (Ex: BTCUSDT):</label>
            {/* SUBSTITUÍDO: O campo de seleção (select) foi substituído pelo campo de texto (input) */}
            <input
              type="text"
              value={selectedCoin}
              onChange={(e) => setSelectedCoin(e.target.value.toUpperCase())}
              required
              placeholder="Ex: XRPUSDT"
              style={{ padding: '8px', borderRadius: '4px' }}
            />
            <label>Data de Início:</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required style={{ padding: '8px', borderRadius: '4px' }}/>
            <label>Data de Fim:</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required style={{ padding: '8px', borderRadius: '4px' }}/>
          </div>

          <div style={columnStyles}>
            <label>Condições de Alerta:</label>
            <div style={{ maxHeight: '150px', overflowY: 'auto', padding: '10px', border: '1px solid #555', borderRadius: '4px' }}>
              {Object.entries(ALERT_OPTIONS).map(([key, option]) => (
                <div key={key} style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
                  <input
                    id={`checkbox-${key}`}
                    type="checkbox"
                    checked={alertConfig[key].enabled}
                    onChange={(e) => handleAlertConfigChange(key, 'enabled', e.target.checked)}
                  />
                  <label htmlFor={`checkbox-${key}`} style={{ marginLeft: '5px' }}>{option.name}</label>
                  {option.hasValue && (
                    <input
                      type="number"
                      value={alertConfig[key].value ?? ''}
                      onChange={(e) => handleAlertConfigChange(key, 'value', e.target.value)}
                      disabled={!alertConfig[key].enabled}
                      style={{ width: '60px', marginLeft: 'auto', padding: '4px' }}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
        <button type="submit" disabled={isLoading} style={{ padding: '10px 20px', cursor: 'pointer' }}>
          {isLoading ? 'Analisando...' : 'Analisar'}
        </button>
      </form>

      <div style={{ marginTop: '20px', flex: 1, overflowY: 'auto' }}>
        {isLoading && <p>Carregando resultados...</p>}
        {error && <p style={{ color: 'red' }}>Erro: {error}</p>}
        {searchPerformed && !isLoading && !error && (
          <div>
            {showChart ? (
              <HistoricalResultChart
                symbol={selectedCoin}
                startDate={startDate}
                endDate={endDate}
                alerts={results}
              />
            ) : (
              <ResultsTable alerts={results} />
            )}
            {results.length > 0 && (
              <button
                onClick={() => setShowChart(prev => !prev)}
                style={{ marginTop: '20px', padding: '10px 20px', cursor: 'pointer' }}
              >
                {showChart ? 'Mostrar Tabela de Resultados' : 'Gerar Gráfico com Alertas'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoricalAnalysisPanel;