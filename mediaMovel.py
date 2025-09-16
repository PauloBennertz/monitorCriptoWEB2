import ccxt
import pandas as pd
import time
import os

# --- CONFIGURAÇÃO ---
symbol = 'BTC/USDT'      # Par de moedas que você quer analisar
timeframe = '1h'         # Timeframe do gráfico (1m, 5m, 15m, 1h, 4h, 1d)
periods = [17, 34, 72, 144] # Períodos das médias móveis exponenciais (EMA)
exchange_id = 'binance'  # ID da corretora (pode ser 'mercadobitcoin', 'coinbasepro', etc.)

# --- INICIALIZAÇÃO DA CORRETORA ---
try:
    exchange = getattr(ccxt, exchange_id)()
    print(f"Conectado com sucesso à corretora: {exchange.name}")
except Exception as e:
    print(f"Erro ao conectar com a corretora: {e}")
    exit()

def clear_screen():
    """Limpa a tela do terminal para uma visualização mais limpa."""
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_data_and_calculate_emas():
    """Busca os dados da corretora e calcula as EMAs."""
    try:
        # Busca os últimos 200 candles para garantir que a EMA mais longa (144) tenha dados suficientes
        limit = 200
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        # Converte os dados para um DataFrame do Pandas
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Converte o timestamp para um formato de data legível
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Calcula as EMAs para cada período especificado
        for period in periods:
            df[f'EMA_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        return df

    except Exception as e:
        print(f"Ocorreu um erro ao buscar ou processar os dados: {e}")
        return None

# --- LOOP PRINCIPAL ---
if __name__ == "__main__":
    while True:
        clear_screen()
        print(f"Buscando dados para {symbol} no timeframe de {timeframe}...")
        
        data_df = fetch_data_and_calculate_emas()
        
        if data_df is not None and not data_df.empty:
            # Pega a última linha do DataFrame (o candle mais recente)
            latest_data = data_df.iloc[-1]
            
            print("="*50)
            print(f"Última Atualização: {pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Último Candle: {latest_data['timestamp']}")
            print(f"Preço de Fechamento: ${latest_data['close']:.2f}")
            print("-"*50)
            print("Médias Móveis Exponenciais (EMAs):")
            
            for period in periods:
                print(f"  - EMA {period}: ${latest_data[f'EMA_{period}']:.2f}")
            
            print("="*50)
            print("Aguardando 60 segundos para a próxima atualização...")
            print("Pressione CTRL+C para sair.")
        
        time.sleep(60) # Espera 60 segundos antes de buscar os dados novamente