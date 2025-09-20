import pandas as pd
import logging
import requests
import time
from datetime import datetime, timezone
from .chart_generator import generate_chart
from .indicators import calculate_sma
import numpy as np

BINANCE_API_URL = "https://api.binance.com/api/v3/klines"
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
                break
            all_data.extend(data)
            last_timestamp = data[-1][0]
            start_ms = last_timestamp + 1
            logging.info(f"Fetched {len(data)} records. Next start time: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error while fetching data for {symbol}: {e}")
            time.sleep(5)
            break
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break

    if not all_data:
        logging.warning("No data was fetched. Check the symbol and date range.")
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].set_index('timestamp')
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    df = df[df.index < end_date_dt]
    logging.info(f"Successfully fetched a total of {len(df)} records for the specified period.")
    return df

class MovingAverageCrossoverStrategy:
    def __init__(self, short_window=40, long_window=100):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0
        signals['short_mavg'] = calculate_sma(data['close'], self.short_window)
        signals['long_mavg'] = calculate_sma(data['close'], self.long_window)
        signals['signal'][self.short_window:] = np.where(signals['short_mavg'][self.short_window:] > signals['long_mavg'][self.short_window:], 1.0, 0.0)
        signals['positions'] = signals['signal'].diff()
        return signals['positions']

class Backtester:
    """
    A class to run a backtest on historical data using a provided strategy.
    """
    def __init__(self, historical_data: pd.DataFrame, strategy, initial_capital: float):
        """
        Initializes the Backtester.

        Args:
            historical_data (pd.DataFrame): DataFrame with 'timestamp', 'open', 'high', 'low', 'close', 'volume'.
            strategy: An object with a `generate_signals(data)` method that returns a Series of positions.
            initial_capital (float): The starting capital for the backtest.
        """
        self.data = historical_data.copy()
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.positions = None
        self.portfolio = None
        logging.info(f"Backtester initialized with initial capital: {self.initial_capital}")

    def _generate_positions(self):
        """
        Generates trading positions using the provided strategy.
        """
        if self.strategy:
            self.positions = self.strategy.generate_signals(self.data)
            logging.info("Generated positions from strategy.")
        else:
            # Create an empty positions series if no strategy is provided
            self.positions = pd.Series(index=self.data.index).fillna(0.0)
            logging.warning("No strategy provided. No positions will be taken.")

    def _simulate_portfolio(self):
        """
        Simulates the portfolio performance based on the generated positions.
        """
        self.portfolio = pd.DataFrame(index=self.data.index)
        self.portfolio['returns'] = self.data['close'].pct_change()
        self.portfolio['total'] = self.initial_capital
        self.portfolio['positions'] = self.positions.fillna(0)

        # A simple backtest: 1.0 means "buy/hold", -1.0 means "sell/short", 0 means "neutral"
        # We'll translate this to a holding state.
        self.portfolio['holdings'] = (self.portfolio['positions'].cumsum() * self.initial_capital)
        self.portfolio['cash'] = self.initial_capital - (self.data['close'] * self.portfolio['positions']).cumsum()
        self.portfolio['total'] = self.portfolio['cash'] + self.portfolio['holdings']
        self.portfolio['returns'] = self.portfolio['total'].pct_change()

        logging.info("Portfolio simulation complete.")

    def _extract_signals_for_charting(self):
        """
        Extracts signals from the positions Series to be used by the chart generator.
        """
        signals_list = []
        if self.positions is None:
            return signals_list

        # Get the timestamps where a position change occurs
        signal_points = self.positions[self.positions != 0]

        for timestamp, signal_type in signal_points.items():
            price = self.data.loc[timestamp, 'close']
            if signal_type > 0:
                message = f"Sinal de Compra a ${price:.2f}"
            elif signal_type < 0:
                message = f"Sinal de Venda a ${price:.2f}"
            else:
                continue # Skip neutral signals

            signals_list.append({
                'timestamp': timestamp,
                'message': message,
                'price': price
            })
        logging.info(f"Extracted {len(signals_list)} signals for charting.")
        return signals_list

    def run(self, coin_id: str):
        """
        Runs the backtest simulation and generates the chart.

        Args:
            coin_id (str): The identifier for the coin being backtested (e.g., 'BTCUSDT').

        Returns:
            A tuple containing the DataFrame with backtest data and the list of signals for charting.
        """
        try:
            logging.info(f"Running backtest for {coin_id}...")
            self._generate_positions()
            self._simulate_portfolio()
            charting_signals = self._extract_signals_for_charting()

            # The chart generator expects the timestamp to be a column, not the index
            chart_df = self.data.reset_index()

            return chart_df, charting_signals
        except Exception as e:
            logging.error(f"An error occurred during the backtest run: {e}", exc_info=True)
            return pd.DataFrame(), []

def run_backtest(historical_df, symbol, stop_event, pause_event, queue_put):
    """
    This function is designed to be called from the GUI thread.
    It runs the backtest and communicates progress via the queue.
    """
    strategy = MovingAverageCrossoverStrategy()
    backtester = Backtester(historical_df, strategy, initial_capital=10000)

    # The GUI seems to expect to iterate over something, let's simulate that
    # by just running the backtest and then returning the results.
    # The original GUI code seems to have some threading logic that might need rework,
    # but for now, let's just make it work.

    queue_put(f"INFO: Running backtest for {symbol}...")

    if stop_event.is_set():
        queue_put("INFO: Backtest stopped by user.")
        return pd.DataFrame(), []

    # This is a simplified run. The original GUI code seems to imply a more iterative process.
    df, signals = backtester.run(symbol)

    for signal in signals:
        if stop_event.is_set():
            queue_put("INFO: Backtest stopped by user.")
            break
        while pause_event.is_set():
            time.sleep(1)
        queue_put(f"{signal['timestamp']} - {signal['message']}")

    queue_put("INFO: Backtest finished.")
    return df, signals
