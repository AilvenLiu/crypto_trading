import sqlite3
import yaml
import pandas as pd
from performance_metrics import PerformanceMetrics
import numpy as np
import concurrent.futures
from report_generator import ReportGenerator
import logging
import random

class Backtester:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.start_date = config['backtesting']['start_date']
        self.end_date = config['backtesting']['end_date']
        self.strategy = config['backtesting']['strategy']
        self.cursor = sqlite3.connect(self.db_path).cursor()
        self.metrics = PerformanceMetrics()
        self.slippage = config['backtesting'].get('slippage', 0.001)  # 0.1%
        self.fee = config['backtesting'].get('fee', 0.00075)  # 0.075%
        self.backtest_config = config.get('backtesting', {})
        self.logger = logging.getLogger('Backtester')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('logs/backtester.log')
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
        self.cursor.execute(query)
        data = self.cursor.fetchall()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def run_strategy(self, df):
        if self.strategy == "ma_strategy":
            # 移动平均策略
            df['ma'] = df['close'].rolling(window=20).mean()
            df['signal'] = 0
            df.loc[20:, 'signal'] = np.where(df['close'][20:] > df['ma'][20:], 1, -1)
        elif self.strategy == "macd_strategy":
            # MACD策略
            df['macd'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
            df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['signal'] = 0
            df.loc[df['macd'] > df['signal_line'], 'signal'] = 1
            df.loc[df['macd'] < df['signal_line'], 'signal'] = -1
        elif self.strategy == "rsi_strategy":
            # RSI策略
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            df['signal'] = 0
            df.loc[df['rsi'] > 70, 'signal'] = -1
            df.loc[df['rsi'] < 30, 'signal'] = 1
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
        
        df['position'] = df['signal'].shift(1)
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['position'] * df['returns']
        # Apply slippage and fees
        df['strategy_returns'] = df['strategy_returns'] - (self.slippage + self.fee) * df['position'].abs()
        return df

    def simulate_trades(self, df):
        initial_capital = 100000
        df['capital'] = initial_capital + (df['strategy_returns'].cumsum() * initial_capital)
        return df

    def evaluate_performance(self, df):
        self.metrics.calculate_metrics(df)

    def run_backtest(self):
        df = self.load_data()
        df = self.run_strategy(df)
        df = self.simulate_trades(df)
        self.evaluate_performance(df)
        print("Backtesting Completed")
        self.metrics.print_metrics()
        return self.metrics.metrics

    def backtest_multiple_strategies(self, strategies):
        results = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_strategy = {
                executor.submit(self.run_backtest_for_strategy, strategy, strategies[strategy]): strategy
                for strategy in strategies
            }
            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    result = future.result()
                    results[strategy] = result
                except Exception as e:
                    print(f"Strategy {strategy} generated an exception: {e}")
        self.generate_report(results)
        return results

    def run_backtest_for_strategy(self, strategy_name, strategies):
        self.strategy = strategies[strategy_name]['strategy']
        self.slippage = strategies[strategy_name].get('slippage', 0.001)
        self.fee = strategies[strategy_name].get('fee', 0.00075)
        return self.run_backtest()

    def generate_report(self, results):
        report_df = pd.DataFrame(results).T
        report_df.to_csv('backtesting/report.csv')
        print("Backtest report generated at backtesting/report.csv")
        # Generate performance charts
        reporter = ReportGenerator(report_path='backtesting/report.csv')
        reporter.generate()

    def backtest_strategy(self, strategy_name):
        """
        Backtest a single strategy.
        
        :param strategy_name: Name of the strategy to backtest
        :return: Dictionary with backtest results
        """
        # Placeholder for actual backtesting logic
        # Replace with real backtesting implementation
        # Simulate backtest results
        performance = {
            "return": random.uniform(-0.1, 0.2),  # Example return between -10% and +20%
            "max_drawdown": random.uniform(0.0, 0.1),
            "sharpe_ratio": random.uniform(0.5, 2.0)
        }
        self.logger.info(f"Backtested {strategy_name}: {performance}")
        return performance

    def backtest_multiple_strategies(self, strategies):
        """
        Backtest multiple strategies.
        
        :param strategies: Dictionary of strategy names and their weights
        :return: Dictionary with backtest results for each strategy
        """
        results = {}
        for strategy in strategies.keys():
            results[strategy] = self.backtest_strategy(strategy)
        return results

if __name__ == "__main__":
    backtester = Backtester()
    backtester.backtest()
