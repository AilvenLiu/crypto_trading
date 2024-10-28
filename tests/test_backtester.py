import unittest
import sqlite3
import os
import yaml
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategy_generation.backtester import Backtester

class TestBacktester(unittest.TestCase):
    def setUp(self):
        self.test_db = 'test_backtest.db'
        with open('config/config_simulation.yaml', 'r') as file:
            config = yaml.safe_load(file)
        config['data_processing']['db_path'] = self.test_db
        with open('config/test_config.yaml', 'w') as file:
            yaml.dump(config, file)
        self.backtester = Backtester(config_path='config/test_config.yaml')
        self._setup_test_database()

    def _setup_test_database(self):
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE kline (
                timestamp TEXT PRIMARY KEY,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE indicators (
                timestamp TEXT PRIMARY KEY,
                ma REAL,
                macd REAL,
                rsi REAL,
                other_indicators TEXT
            )
        ''')
        self._insert_sample_data(cursor)
        conn.commit()
        conn.close()

    def _insert_sample_data(self, cursor):
        for i in range(30):
            timestamp = f"2024-01-01 12:{i:02d}:00"
            cursor.execute(
                'INSERT INTO kline VALUES (?, ?, ?, ?, ?, ?)',
                (timestamp, 50000+i, 50050+i, 49950+i, 50025+i, 10+i)
            )
            cursor.execute(
                'INSERT INTO indicators VALUES (?, ?, ?, ?, ?)',
                (timestamp, 50025+i, 150+i, 70+i, "{}")
            )

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists('config/test_config.yaml'):
            os.remove('config/test_config.yaml')

    def test_load_data(self):
        df = self.backtester.load_data()
        self.assertEqual(len(df), 30)
        self.assertTrue(all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']))

    def test_run_strategy_ma(self):
        df = self.backtester.load_data()
        self.backtester.strategy = "ma_strategy"
        df = self.backtester.run_strategy(df)
        self.assertIn('signal', df.columns)
        self.assertIn('position', df.columns)
        self.assertIn('strategy_returns', df.columns)

    def test_run_strategy_macd(self):
        df = self.backtester.load_data()
        self.backtester.strategy = "macd_strategy"
        df = self.backtester.run_strategy(df)
        self.assertIn('signal', df.columns)
        self.assertIn('macd', df.columns)

    def test_run_strategy_rsi(self):
        df = self.backtester.load_data()
        self.backtester.strategy = "rsi_strategy"
        df = self.backtester.run_strategy(df)
        self.assertIn('signal', df.columns)
        self.assertIn('rsi', df.columns)

    def test_backtest_results(self):
        results = self.backtester.backtest()
        self.assertIsNotNone(results)
        self.assertTrue(hasattr(results, 'sharpe_ratio'))
        self.assertTrue(hasattr(results, 'max_drawdown'))
        self.assertTrue(hasattr(results, 'total_return'))

if __name__ == '__main__':
    unittest.main()
