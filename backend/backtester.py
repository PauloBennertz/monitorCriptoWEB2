import requests
import pandas as pd
from datetime import datetime, timezone
import time
import logging
import sys
import os
import argparse



# Passo 1: Ativar a busca de dados reais (MUITO IMPORTANTE)
# Como o meu ambiente de desenvolvimento tinha restrições de rede, eu deixei o script usando dados de teste para poder construí-lo. Para que ele funcione com dados reais da corretora Binance, você precisa fazer uma pequena edição no arquivo backend/backtester.py:

# Abra o arquivo backend/backtester.py em um editor de texto.

# Procure a linha que está comentada (começa com #):

# # historical_df = fetch_historical_data(args.symbol, args.start, args.end, args.interval)
# Descomente esta linha, ou seja, apague o # do início.

# Logo abaixo, você verá um bloco de código de teste. Apague ou comente todo este bloco:

# # --- MOCK DATA FOR DEVELOPMENT ---
# # ... (apague todo o conteúdo até)
# # --- END OF MOCK DATA BLOCK ---
# Passo 2: Executar o Script pelo Terminal
# Depois de fazer a edição acima, você pode usar o script da seguinte forma:

# Abra o seu terminal e navegue até a pasta raiz do projeto.

# Execute o comando abaixo, substituindo os valores pelos que você deseja analisar.

# python3 backend/backtester.py --symbol <SÍMBOLO> --start <DATA_DE_INÍCIO> --end <DATA_DE_FIM>
# Exemplos de Uso:
# Para analisar o Bitcoin (BTC) durante todo o ano de 2022:

# python3 backend/backtester.py --symbol BTCUSDT --start 2022-01-01 --end 2022-12-31
# Para analisar a Ethereum (ETH) no primeiro trimestre de 2023, com intervalo de 4 horas:

# python3 backend/backtester.py --symbol ETHUSDT --start 2023-01-01 --end 2023-03-31 --interval 4h
# Parâmetros do Comando:
# --symbol: (Obrigatório) O símbolo da moeda (ex: BTCUSDT).
# --start: (Obrigatório) A data de início no formato AAAA-MM-DD.
# --end: (Obrigatório) A data de fim no formato AAAA-MM-DD.
# --interval: (Opcional) O intervalo das velas. Padrão: 1h. Outros exemplos: 15m, 4h, 1d.





# Add the project root to the Python path to allow for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend import robust_services
    from backend.indicators import (
        calculate_rsi, calculate_bollinger_bands, calculate_macd,
        calculate_emas, calculate_hilo_signals
    )
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure the script is run from the project's root directory or that the backend package is in the Python path.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BINANCE_API_URL = "https://api.binance.com/api/v3/klines"
# Binance API returns a maximum of 1000 results per request
MAX_LIMIT = 1000

def date_to_milliseconds(date_str):
    """Converts a YYYY-MM-DD string to milliseconds since epoch."""
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

def fetch_historical_data(symbol, start_date, end_date, interval='1h'):
    """
    Fetches historical k-line data from Binance for a given symbol and date range.
    Handles pagination to retrieve all data in the specified range.
    """
    logging.info(f"Fetching historical data for {symbol} from {start_date} to {end_date} with {interval} interval.")

    start_ms = date_to_milliseconds(start_date)
    end_ms = date_to_milliseconds(end_date)

    all_data = []

    while start_ms < end_ms:
        robust_services.rate_limiter.wait_if_needed()
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_ms,
            'endTime': end_ms,
            'limit': MAX_LIMIT
        }

        try:
            response = requests.get(BINANCE_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if not data:
                # No more data available for the period
                break

            all_data.extend(data)

            # The next request should start after the last timestamp we received.
            last_timestamp = data[-1][0]
            start_ms = last_timestamp + 1

            logging.info(f"Fetched {len(data)} records. Next start time: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error while fetching data for {symbol}: {e}")
            time.sleep(5) # Wait before potentially retrying or exiting
            break
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break

    if not all_data:
        logging.warning("No data was fetched. Check the symbol and date range.")
        return pd.DataFrame()

    # Create DataFrame
    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])

    # Convert data types
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Keep only necessary columns and rename open_time for clarity
    df = df[['open_time', 'open', 'high', 'low', 'close', 'volume']].rename(columns={'open_time': 'timestamp'})

    # Filter again to ensure we are within the requested end_date (Binance endTime is inclusive)
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    df = df[df['timestamp'] < end_date_dt]

    logging.info(f"Successfully fetched a total of {len(df)} records for the specified period.")
    return df

def main():
    """Main function to run the backtester from the command line."""
    parser = argparse.ArgumentParser(
        description="A command-line tool to backtest cryptocurrency trading strategies.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--symbol", type=str, required=True, help="The cryptocurrency symbol to backtest (e.g., BTCUSDT).")
    parser.add_argument("--start", type=str, required=True, help="Start date for the backtest in YYYY-MM-DD format.")
    parser.add_argument("--end", type=str, required=True, help="End date for the backtest in YYYY-MM-DD format.")
    parser.add_argument("--interval", type=str, default='1h', help="The interval for the k-lines (e.g., 15m, 1h, 4h, 1d).")

    args = parser.parse_args()

    # --- REAL IMPLEMENTATION ---
    # The following line will be used in a real environment.
    # Due to network restrictions in this sandbox, it's temporarily commented out.
    # historical_df = fetch_historical_data(args.symbol, args.start, args.end, args.interval)

    # --- MOCK DATA FOR DEVELOPMENT ---
    # This block is used to simulate data fetching when the API is not accessible.
    # It will be removed once the script is run in a non-restricted environment.
    logging.warning("--- USING MOCK DATA! The live Binance API is currently inaccessible. ---")
    date_range = pd.date_range(start=args.start, end=args.end, freq=args.interval, tz='UTC')
    mock_data = {
        'timestamp': date_range,
        'open': 40000 + pd.Series(range(len(date_range))) * 10,
        'high': 40500 + pd.Series(range(len(date_range))) * 10,
        'low': 39800 + pd.Series(range(len(date_range))) * 10,
        'close': 40200 + pd.Series(range(len(date_range))) * 5,
        'volume': 100 + pd.Series(range(len(date_range)))
    }
    historical_df = pd.DataFrame(mock_data)
    # --- END OF MOCK DATA BLOCK ---

    if historical_df.empty:
        logging.error(f"Could not retrieve data for {args.symbol}. Exiting.")
        return

    print(f"\nBacktesting for {args.symbol} from {args.start} to {args.end} with {args.interval} interval...")

    run_backtest(historical_df, args.symbol)


def run_backtest(df, symbol, output_callback=None):
    """
    Runs the backtest on the given DataFrame.
    Iterates through the data, calculates indicators, and checks for signals.
    Results are passed to the output_callback function.
    """
    # If no callback is provided, default to printing to the console for command-line use.
    if output_callback is None:
        output_callback = print

    logging.info(f"Starting backtest for {symbol} with {len(df)} records.")

    min_periods = 226
    if len(df) < min_periods:
        error_msg = f"Not enough data. Need at least {min_periods} records, got {len(df)}."
        logging.error(error_msg)
        output_callback(f"ERRO: {error_msg}")
        return

    output_callback("\n--- Backtest Results ---")

    # State tracking to only report a signal when the state changes
    active_signals = set()

    # Iterate through the data, starting from the point where we have enough data.
    for i in range(min_periods, len(df)):
        # Use i+1 to ensure the current candle is included in the window
        df_window = df.iloc[:i+1]
        current_row = df_window.iloc[-1]
        timestamp = current_row['timestamp']

        # --- Calculate all indicators for the current window ---
        rsi_value, _, _ = calculate_rsi(df_window)
        upper_band, lower_band, _, _ = calculate_bollinger_bands(df_window)
        macd_signal = calculate_macd(df_window)
        _, _, hilo_signal = calculate_hilo_signals(df_window)

        emas = calculate_emas(df_window, periods=[50, 200])
        mme_cross = "Nenhum"
        if 50 in emas and 200 in emas and len(emas[50]) > 1 and len(emas[200]) > 1:
            # Check for a crossover at the very last point in the series
            if emas[50].iloc[-2] < emas[200].iloc[-2] and emas[50].iloc[-1] > emas[200].iloc[-1]:
                mme_cross = "Cruz Dourada"
            elif emas[50].iloc[-2] > emas[200].iloc[-2] and emas[50].iloc[-1] < emas[200].iloc[-1]:
                mme_cross = "Cruz da Morte"

        # --- Define all possible signals and their current state ---
        signals_to_check = {
            "RSI Sobrecompra (>= 70)": rsi_value >= 70,
            "RSI Sobrevenda (<= 30)": rsi_value <= 30,
            "Cruzamento de Alta (MACD)": macd_signal == "Cruzamento de Alta",
            "Cruzamento de Baixa (MACD)": macd_signal == "Cruzamento de Baixa",
            "Cruz Dourada (MME 50/200)": mme_cross == "Cruz Dourada",
            "Cruz da Morte (MME 50/200)": mme_cross == "Cruz da Morte",
            "Sinal de Compra (HiLo)": hilo_signal == "HiLo Buy",
            "Sinal de Venda (HiLo)": hilo_signal == "HiLo Sell",
            "Preco Acima da Banda Bollinger": upper_band > 0 and current_row['close'] > upper_band,
            "Preco Abaixo da Banda Bollinger": lower_band > 0 and current_row['close'] < lower_band,
        }

        # --- Compare current state with previous state to find new alerts ---
        for signal, is_active in signals_to_check.items():
            if is_active and signal not in active_signals:
                # A new signal has been triggered
                message = f"{timestamp.strftime('%d/%m/%Y %H:%M:%S')} {symbol} - {signal}"
                output_callback(message)
                active_signals.add(signal)
            elif not is_active and signal in active_signals:
                # A signal is no longer active, so we remove it from the set.
                active_signals.remove(signal)

    output_callback("--- Backtest Complete ---")
    logging.info("Backtesting loop finished.")


if __name__ == '__main__':
    main()
