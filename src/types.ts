export interface CryptoData {
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

export interface Alert {
    id: string;
    symbol: string;
    condition: string;
    description: string;
    timestamp: string;
    snapshot: CryptoData;
}

export interface AlertConfig {
    enabled: boolean;
    cooldown: number; // in seconds
    blinking: boolean;
}

export interface AlertConfigs {
    [symbol: string]: {
        [alertType: string]: AlertConfig;
    };
}

export interface MutedAlert {
    symbol: string;
    alertType: string;
    muteUntil: number; // timestamp
}

export interface MarketAnalysisConfig {
    top_n: number;
    min_market_cap: number;
    display_limit: number;
    grid_layout_columns: number;
}

export type BasicCoin = Pick<CryptoData, 'symbol' | 'name'>;

export const ALERT_DEFINITIONS: Record<string, { name: string; description: string; backendKey: string }> = {
    RSI_SOBREVENDA: { name: 'RSI em Sobrevenda', description: 'Alerta quando o Índice de Força Relativa (RSI) entra em território de sobrevenda (abaixo de 30).', backendKey: 'rsi_sobrevendido' },
    RSI_SOBRECOMPRA: { name: 'RSI em Sobrecompra', description: 'Alerta quando o RSI entra em território de sobrecompra (acima de 70).', backendKey: 'rsi_sobrecomprado' },
    HILO_COMPRA: { name: 'Sinal de Compra HiLo', description: 'Dispara quando o indicador HiLo Activator gera um sinal de compra.', backendKey: 'hilo_compra' },
    CRUZ_DOURADA: { name: 'Cruz Dourada (MME)', description: 'Sinal de alta de longo prazo quando a MME de 50 períodos cruza acima da de 200.', backendKey: 'mme_cruz_dourada' },
    CRUZ_DA_MORTE: { name: 'Cruz da Morte (MME)', description: 'Sinal de baixa de longo prazo quando a MME de 50 períodos cruza abaixo da de 200.', backendKey: 'mme_cruz_morte' },
    MACD_ALTA: { name: 'Cruzamento de Alta (MACD)', description: 'Sinal de momentum de alta quando a linha MACD cruza para cima da linha de sinal.', backendKey: 'macd_cruz_alta' },
    MACD_BAIXA: { name: 'Cruzamento de Baixa (MACD)', description: 'Sinal de momentum de baixa quando a linha MACD cruza para baixo da linha de sinal.', backendKey: 'macd_cruz_baixa' },
};

export const COOLDOWN_OPTIONS = [
    { value: 300, label: '5 minutos' },
    { value: 900, label: '15 minutos' },
    { value: 3600, label: '1 hora' },
    { value: 14400, label: '4 horas' },
    { value: 86400, label: '24 horas' },
];

export const DEFAULT_ALERT_CONFIG: AlertConfig = {
    enabled: true,
    cooldown: 900, // 15 minutes
    blinking: true,
};

export const INDICATOR_TOOLTIPS: Record<string, Record<string, string>> = {
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

export const API_BASE_URL = 'http://localhost:8000';
