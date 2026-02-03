import pandas as pd
import logging
import time
import numpy as np
from .indicators import calculate_sma, calculate_hma, calculate_vwap


class MovingAverageCrossoverStrategy:
    def __init__(self, short_window=40, long_window=100):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0
        signals['short_mavg'] = calculate_sma(data['close'], self.short_window)
        signals['long_mavg'] = calculate_sma(data['close'], self.long_window)
        signals.loc[signals.index[self.long_window:], 'signal'] = np.where(
            signals['short_mavg'][self.long_window:] > signals['long_mavg'][self.long_window:], 1.0, 0.0
        )
        signals['positions'] = signals['signal'].diff()
        return signals['positions']

class HMAStrategy:
    """
    Estratégia baseada na Hull Moving Average (HMA).
    Compra quando o preço fecha ACIMA da HMA.
    Vende quando o preço fecha ABAIXO da HMA.
    """
    def __init__(self, period=21):
        self.period = period

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0
        
        # Calcula a HMA usando a função existente em indicators.py
        hma = calculate_hma(data['close'], self.period)
        
        # Lógica: Preço > HMA = 1 (Comprado), Preço < HMA = 0 (Neutro/Vendido)
        # Começamos a verificar após o período necessário para o cálculo
        signals.loc[signals.index[self.period:], 'signal'] = np.where(
            data['close'][self.period:] > hma[self.period:], 1.0, 0.0
        )
        
        signals['positions'] = signals['signal'].diff()
        return signals['positions']

class VWAPStrategy:
    """
    Estratégia baseada no VWAP (Volume Weighted Average Price).
    Compra quando o preço cruza ACIMA do VWAP.
    Vende quando o preço cruza ABAIXO do VWAP.
    """
    def __init__(self):
        # VWAP geralmente não tem parametros fixos além do inicio da contagem (que será o inicio do backtest)
        pass

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0
        
        # Calcula o VWAP usando a função existente em indicators.py
        vwap = calculate_vwap(data)
        
        # O VWAP precisa de volume. Se não houver volume, retorna vazio.
        if vwap is None or vwap.empty:
            logging.warning("VWAP calculation failed due to missing volume data.")
            return signals['signal']

        signals['signal'] = np.where(data['close'] > vwap, 1.0, 0.0)
        
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