import unittest
import sqlite3
import os
import yaml
from backtesting.backtester import Backtester

class TestBacktester(unittest.TestCase):
    def setUp(self, config):
        self.test_db = 'test_backtest.db'
        with open('config/config_simulation.yaml', 'r') as file:
            config_data = yaml.safe_load(file)
        config_data['data_processing']['db_path'] = self.test_db
        config_data['backtesting']['start_date'] = "2023-01-01 00:00:00"
        config_data['backtesting']['end_date'] = "2023-01-02 00:00:00"
        config_data['backtesting']['strategies'] = {
            "ma_strategy": {"strategy": "ma_strategy", "slippage": 0.001, "fee": 0.00075},
            "macd_strategy": {"strategy": "macd_strategy", "slippage": 0.001, "fee": 0.00075},
            "rsi_strategy": {"strategy": "rsi_strategy", "slippage": 0.001, "fee": 0.00075}
        }
        with open('config/test_config.yaml', 'w') as file:
            yaml.dump(config_data, file)
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
            CREATE TABLE strategies (
                timestamp TEXT PRIMARY KEY,
                signal INTEGER
            )
''')
        cursor.execute('''
            CREATE TABLE indicators (
                timestamp TEXT PRIMARY KEY,
                ma_10 REAL,
                macd REAL,
                rsi REAL,
                other_indicators TEXT
            )
''')
        # Insert sample data
        for i in range(20):
            timestamp = f"2023-01-01 12:{i:02d}:00"
            cursor.execute('''
                INSERT INTO kline VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, 50000+i, 50050+i, 49950+i, 50025+i, 10+i))
            cursor.execute('''
                INSERT INTO strategies VALUES (?, ?)
            ''', (timestamp, 1))
            cursor.execute('''
                INSERT INTO indicators VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, 50025+i, 150+i, 70+i, "{}"))
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists('config/test_config.yaml'):
            os.remove('config/test_config.yaml')

    def test_load_data(self):
        df = self.backtester.load_data()
        self.assertEqual(len(df), 20)
        self.assertTrue(all(col in df.columns for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']))

    def test_run_strategy_ma(self):
        df = self.backtester.load_data()
        strategy_config = self.backtester.strategies['ma_strategy']
        df = self.backtester.run_strategy(df, 'ma_strategy', strategy_config)
        self.assertIn('ma', df.columns)
        self.assertIn('signal', df.columns)
        self.assertIn('position', df.columns)
        self.assertIn('strategy_returns', df.columns)

    def test_run_strategy_macd(self):
        df = self.backtester.load_data()
        strategy_config = self.backtester.strategies['macd_strategy']
        df = self.backtester.run_strategy(df, 'macd_strategy', strategy_config)
        self.assertIn('macd', df.columns)
        self.assertIn('signal_line', df.columns)
        self.assertIn('signal', df.columns)
        self.assertIn('position', df.columns)
        self.assertIn('strategy_returns', df.columns)

    def test_run_strategy_rsi(self):
        df = self.backtester.load_data()
        strategy_config = self.backtester.strategies['rsi_strategy']
        df = self.backtester.run_strategy(df, 'rsi_strategy', strategy_config)
        self.assertIn('rsi', df.columns)
        self.assertIn('signal', df.columns)
        self.assertIn('position', df.columns)
        self.assertIn('strategy_returns', df.columns)

    def test_run_backtest(self):
        results = self.backtester.run_backtest()
        self.assertIn('ma_strategy', results)
        self.assertIn('macd_strategy', results)
        self.assertIn('rsi_strategy', results)
        self.assertIsNotNone(results['ma_strategy']['total_return'])
        self.assertIsNotNone(results['macd_strategy']['sharpe_ratio'])

if __name__ == '__main__':
    unittest.main()
