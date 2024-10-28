import threading
import time
import queue
import logging
from logging.handlers import RotatingFileHandler
import random
import yaml
import numpy as np
from backtesting.backtester import Backtester


class MultiStrategyManager:
    def __init__(self, signal_queue, config_path='config/config.yaml'):
        self.signal_queue = signal_queue
        self.config_path = config_path
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.strategy_weights = {
            "ma_strategy": 1.0,
            "macd_strategy": 1.0,
            "rsi_strategy": 1.0
        }
        self.logger = logging.getLogger('MultiStrategyManager')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/multi_strategy_manager.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.info("MultiStrategyManager initialized.")

    def ma_strategy(self, df):
        """
        Moving Average Strategy:
        Buy when price crosses above the moving average.
        Sell when price crosses below the moving average.
        """
        df['ma'] = df['close'].rolling(window=20).mean()
        df['ma_signal'] = 0
        df.loc[df['close'] > df['ma'], 'ma_signal'] = 1
        df.loc[df['close'] < df['ma'], 'ma_signal'] = -1
        signal = df['ma_signal'].iloc[-1]
        self.logger.debug(f"MA Strategy signal: {signal}")
        return signal

    def macd_strategy(self, df):
        """
        MACD Strategy:
        Buy when MACD crosses above the signal line.
        Sell when MACD crosses below the signal line.
        """
        df['macd'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
        df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_signal'] = 0
        df.loc[df['macd'] > df['signal_line'], 'macd_signal'] = 1
        df.loc[df['macd'] < df['signal_line'], 'macd_signal'] = -1
        signal = df['macd_signal'].iloc[-1]
        self.logger.debug(f"MACD Strategy signal: {signal}")
        return signal

    def rsi_strategy(self, df):
        """
        RSI Strategy:
        Buy when RSI drops below 30.
        Sell when RSI rises above 70.
        """
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_signal'] = 0
        df.loc[df['rsi'] > 70, 'rsi_signal'] = -1
        df.loc[df['rsi'] < 30, 'rsi_signal'] = 1
        signal = df['rsi_signal'].iloc[-1]
        self.logger.debug(f"RSI Strategy signal: {signal}")
        return signal

    def generate_signals(self, df):
        """
        Generate trading signals based on multiple strategies and their weights.

        :param df: DataFrame containing market data with at least 'close' price
        :return: Final aggregated signal based on strategy outputs.
        """
        signals = {}
        # Execute each strategy and store their signals
        signals['ma_strategy'] = self.ma_strategy(df)
        signals['macd_strategy'] = self.macd_strategy(df)
        signals['rsi_strategy'] = self.rsi_strategy(df)

        # Weighted aggregation
        weighted_sum = sum(signals[strategy] * weight for strategy, weight in self.strategy_weights.items())
        total_weight = sum(self.strategy_weights.values())
        average_signal = weighted_sum / total_weight if total_weight != 0 else 0

        # Determine final signal based on average
        if average_signal > 0.5:
            final_signal = 1
        elif average_signal < -0.5:
            final_signal = -1
        else:
            final_signal = 0

        self.logger.info(f"Generated signals: {signals}, Final aggregated signal: {final_signal}")
        return final_signal

    def run(self):
        """
        Continuously run the strategy manager to generate and send signals.
        """
        while True:
            try:
                # Fetch latest market data
                df = self.fetch_market_data()
                if df.empty:
                    self.logger.warning("No market data available. Skipping signal generation.")
                    time.sleep(1)
                    continue

                final_signal = self.generate_signals(df)

                if final_signal != 0:
                    size = self.calculate_order_size(final_signal)
                    self.signal_queue.put((final_signal, size))
                    self.logger.info(f"Final Signal: {'Buy' if final_signal == 1 else 'Sell'}, Size: {size}")
                else:
                    self.logger.info("Hold signal generated. No action taken.")

                self.evaluate_and_adjust()

            except Exception as e:
                self.logger.error(f"Error in strategy manager run loop: {e}")

            time.sleep(1)  # Adjust sleep time for desired frequency

    def fetch_market_data(self):
        """
        Fetch the latest market data.

        :return: DataFrame containing market data with at least 'close' prices.
        """
        # Placeholder for actual market data fetching
        # Replace with real data fetching from API or data storage
        import pandas as pd

        # Simulate fetching last 100 close prices
        dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='T')
        close_prices = np.random.random(size=100) * 10000  # Simulated close prices
        df = pd.DataFrame({'close': close_prices}, index=dates)
        return df

    def start(self):
        """
        Start the strategy manager in a separate thread.
        """
        strategy_thread = threading.Thread(target=self.run)
        strategy_thread.daemon = True
        strategy_thread.start()
        self.logger.info("Strategy generation thread started.")

    def calculate_order_size(self, signal):
        """
        Calculate the size of the order based on risk management parameters.

        :param signal: 1 for buy, -1 for sell
        :return: Calculated order size
        """
        # Placeholder for actual order size calculation based on risk management
        # Ideally, integrate with RiskManager to get position size
        order_size = random.uniform(0.01, 0.1)  # Example size
        self.logger.debug(f"Calculated order size: {order_size}")
        return order_size

    def evaluate_and_adjust(self):
        """
        Evaluate backtest results and adjust strategy weights.
        """
        try:
            backtester = Backtester(config_path=self.config_path)
            results = backtester.backtest_multiple_strategies(strategies=self.strategy_weights)
            self.adjust_strategy_weights(results)
        except Exception as e:
            self.logger.error(f"Error during backtesting: {e}")

    def adjust_strategy_weights(self, results):
        """
        Adjust the weights of strategies based on backtest results.

        :param results: Backtest results as a dictionary
        """
        for strategy, performance in results.items():
            if performance['return'] > 0:
                self.strategy_weights[strategy] += 0.1
                self.logger.info(f"Increased weight for {strategy} to {self.strategy_weights[strategy]}")
            else:
                self.strategy_weights[strategy] = max(self.strategy_weights[strategy] - 0.1, 0.1)
                self.logger.info(f"Decreased weight for {strategy} to {self.strategy_weights[strategy]}")

        self.logger.info(f"Updated strategy weights: {self.strategy_weights}")


if __name__ == "__main__":
    # Example usage
    signal_q = queue.Queue()
    manager = MultiStrategyManager(signal_queue=signal_q, config_path='config/config.yaml')
    manager.start()

    # Simulate running indefinitely
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.logger.info("MultiStrategyManager stopped by user.")
