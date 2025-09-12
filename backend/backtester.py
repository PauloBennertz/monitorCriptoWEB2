import pandas as pd
import numpy as np
from .chart_generator import generate_chart # Adjusted import

class Backtester:
    def __init__(self, historical_data, strategy, initial_capital=100000):
        self.historical_data = historical_data
        self.strategy = strategy
        self.initial_capital = initial_capital
        # Ensure index is timezone-aware if historical_data's index is
        if isinstance(historical_data.index, pd.DatetimeIndex):
            self.positions = pd.DataFrame(index=historical_data.index).fillna(0.0)
            self.portfolio = pd.DataFrame(index=historical_data.index).fillna(0.0)
            self.signals = pd.DataFrame(index=historical_data.index)
        else:
            # Fallback for non-datetime index, though less ideal
            self.positions = pd.DataFrame(index=range(len(historical_data))).fillna(0.0)
            self.portfolio = pd.DataFrame(index=range(len(historical_data))).fillna(0.0)
            self.signals = pd.DataFrame(index=range(len(historical_data)))


    def _generate_signals(self):
        """Generates trading signals using the provided strategy."""
        self.signals['signal'] = self.strategy.generate_signals(self.historical_data)
        # Ensure 'price' is available for backtesting logic
        if 'close' in self.historical_data:
            self.signals['price'] = self.historical_data['close']
        else:
            # Handle cases where 'close' might not be the price column
            # This is a fallback and might need adjustment based on actual data structure
            self.signals['price'] = self.historical_data.iloc[:, 0]


    def _run_backtest(self):
        """Executes the backtest simulation based on the generated signals."""
        self.portfolio['holdings'] = 0.0
        self.portfolio['cash'] = self.initial_capital
        self.portfolio['total'] = self.initial_capital
        self.positions['shares'] = 0.0

        # Using .values for faster iteration
        signals_array = self.signals.values
        portfolio_array = self.portfolio.values
        positions_array = self.positions.values

        for i in range(1, len(self.signals)):
            # Carry over values from the previous day
            portfolio_array[i, 1] = portfolio_array[i-1, 1]  # cash
            positions_array[i, 0] = positions_array[i-1, 0]  # shares

            signal = signals_array[i, 0]
            price = signals_array[i, 1]

            if signal == 1:  # Buy signal
                shares_to_buy = portfolio_array[i, 1] // price
                if shares_to_buy > 0:
                    positions_array[i, 0] += shares_to_buy
                    portfolio_array[i, 1] -= shares_to_buy * price
            elif signal == -1:  # Sell signal
                shares_to_sell = positions_array[i, 0]
                if shares_to_sell > 0:
                    portfolio_array[i, 1] += shares_to_sell * price
                    positions_array[i, 0] = 0

            # Update holdings and total portfolio value
            portfolio_array[i, 0] = positions_array[i, 0] * price
            portfolio_array[i, 2] = portfolio_array[i, 1] + portfolio_array[i, 0]

        # Update DataFrames from modified numpy arrays
        self.portfolio['holdings'], self.portfolio['cash'], self.portfolio['total'] = portfolio_array[:, 0], portfolio_array[:, 1], portfolio_array[:, 2]
        self.positions['shares'] = positions_array[:, 0]


    def get_performance(self):
        """Returns the portfolio performance DataFrame."""
        return self.portfolio


    def generate_results_chart(self, coin_id):
        """
        Generates a JSON representation of the backtest results chart.

        Args:
            coin_id (str): The identifier of the coin being backtested (e.g., 'bitcoin').

        Returns:
            str: A JSON string representing the Plotly chart.
        """
        # Note: The `generate_chart` function from chart_generator.py expects a list of signals, not a DataFrame
        # We need to format the signals correctly.

        # Create a list of signal dictionaries for the chart generator
        chart_signals = []
        for index, row in self.signals.iterrows():
            if row['signal'] != 0:  # If there is a buy or sell signal
                signal_type = "Buy Signal" if row['signal'] == 1 else "Sell Signal"
                chart_signals.append({
                    'timestamp': index,
                    'message': f"{coin_id.upper()} - {signal_type}",
                    'price': row['price']
                })

        # Call the chart generator with the correct data format
        return generate_chart(self.historical_data, chart_signals)


    def run(self, coin_id):
        """
        Runs the entire backtesting process and returns the results chart as JSON.

        Args:
            coin_id (str): The identifier for the coin.

        Returns:
            str: A JSON string of the results chart, or None if an error occurs.
        """
        try:
            self._generate_signals()
            self._run_backtest()
            return self.generate_results_chart(coin_id)
        except Exception as e:
            print(f"An error occurred during the backtest run: {e}")
            return None
