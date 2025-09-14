import pandas as pd
import logging
from backend.chart_generator import generate_chart

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
        self.data = historical_data
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
            price = self.data.loc[self.data['timestamp'] == timestamp, 'close'].iloc[0]
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
            str: A JSON string representing the Plotly chart, or None if an error occurs.
        """
        try:
            logging.info(f"Running backtest for {coin_id}...")
            self._generate_positions()
            self._simulate_portfolio()
            charting_signals = self._extract_signals_for_charting()

            # The chart generator expects the timestamp to be a column, not the index
            chart_df = self.data.reset_index()

            chart_json = generate_chart(chart_df, charting_signals)
            logging.info("Successfully generated backtest chart.")
            return chart_json
        except Exception as e:
            logging.error(f"An error occurred during the backtest run: {e}", exc_info=True)
            return None
