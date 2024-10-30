import sqlite3
import logging
import yaml
import pandas as pd
import numpy as np
import concurrent.futures
from datetime import datetime
from backtesting.performance_metrics import PerformanceMetrics
from backtesting.report_generator import ReportGenerator

class Backtester:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.start_date = config['backtesting']['start_date']
        self.end_date = config['backtesting']['end_date']
        self.strategies = config['backtesting']['strategies']
        self.cursor = sqlite3.connect(self.db_path).cursor()
        self.metrics = PerformanceMetrics()
        self.logger = logging.getLogger('Backtester')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/backtester.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.info("Backtester initialized.")

    def load_data(self):
        query = f'''
            SELECT timestamp, open, high, low, close, volume FROM kline
            WHERE timestamp BETWEEN '{self.start_date}' AND '{self.end_date}'
            ORDER BY timestamp ASC
        '''
        df = pd.read_sql_query(query, sqlite3.connect(self.db_path))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        self.logger.info(f"Loaded {len(df)} kline records for backtesting.")
        return df

    def run_strategy(self, df, strategy_name, strategy_config):
        self.logger.info(f"Running strategy: {strategy_name}")
        if strategy_name == "ma_strategy":
            df['ma'] = df['close'].rolling(window=20).mean()
            df['signal'] = 0
            df.loc[20:, 'signal'] = np.where(df['close'][20:] > df['ma'][20:], 1, -1)
        elif strategy_name == "macd_strategy":
            df['macd'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
            df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['signal'] = 0
            df.loc[df['macd'] > df['signal_line'], 'signal'] = 1
            df.loc[df['macd'] < df['signal_line'], 'signal'] = -1
        elif strategy_name == "rsi_strategy":
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            df['signal'] = 0
            df.loc[df['rsi'] > 70, 'signal'] = -1
            df.loc[df['rsi'] < 30, 'signal'] = 1
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        # Apply slippage and fees
        df['position'] = df['signal'].shift(1)
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['position'] * df['returns']
        df['strategy_returns'] = df['strategy_returns'] - (strategy_config['slippage'] + strategy_config['fee']) * df['position'].abs()
        
        self.logger.info(f"Strategy {strategy_name} executed.")
        return df

    def simulate_trades(self, df):
        initial_capital = 100000
        df['capital'] = initial_capital + (df['strategy_returns'].cumsum() * initial_capital)
        self.logger.info("Trade simulation completed.")
        return df

    def evaluate_performance(self, df):
        self.metrics.calculate_metrics(df)
        self.logger.info("Performance evaluation completed.")

    def run_backtest(self):
        df = self.load_data()
        results = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_strategy = {
                executor.submit(self.run_single_strategy, df.copy(), strategy_name, config): strategy_name
                for strategy_name, config in self.strategies.items()
            }
            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy_name = future_to_strategy[future]
                try:
                    result_df = future.result()
                    self.simulate_trades(result_df)
                    self.evaluate_performance(result_df)
                    results[strategy_name] = self.metrics.metrics[strategy_name]
                except Exception as e:
                    self.logger.error(f"Strategy {strategy_name} failed: {e}")
        self.generate_report(results)
        return results

    def run_single_strategy(self, df, strategy_name, strategy_config):
        return self.run_strategy(df, strategy_name, strategy_config)

    def generate_report(self, results):
        report = pd.DataFrame(results).T
        report.to_csv('backtesting/report.csv')
        self.logger.info("Backtest report generated at backtesting/report.csv")
        reporter = ReportGenerator(report_path='backtesting/report.csv')
        reporter.generate()

if __name__ == "__main__":
    backtester = Backtester()
    results = backtester.run_backtest()
    print("Backtesting Completed")
    print(backtester.metrics.metrics)
