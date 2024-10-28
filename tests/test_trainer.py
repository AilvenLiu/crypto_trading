import unittest
from model_training.trainer import Trainer
import os
import yaml
import sqlite3

class TestTrainer(unittest.TestCase):
    def setUp(self):
        self.test_db = 'test_trainer.db'
        with open('config/config_simulation.yaml', 'r') as file:
            config = yaml.safe_load(file)
        config['data_processing']['db_path'] = self.test_db
        config['model_training']['model_path'] = 'test_model.pth'
        with open('config/test_config.yaml', 'w') as file:
            yaml.dump(config, file)
        # Initialize test data
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
        # Insert sample data
        for i in range(30):
            timestamp = f"2023-10-01 12:{i:02d}:00"
            cursor.execute('''
                INSERT INTO kline (timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, 50000+i, 50050+i, 49950+i, 50025+i, 10+i))
            cursor.execute('''
                INSERT INTO indicators (timestamp, ma, macd, rsi, other_indicators)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, 50025+i, 150+i, 70+i, "{}"))
        conn.commit()
        conn.close()
        self.trainer = Trainer(config_path='config/test_config.yaml')

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists('test_model.pth'):
            os.remove('test_model.pth')
        if os.path.exists('config/test_config.yaml'):
            os.remove('config/test_config.yaml')

    def test_train(self):
        self.trainer.train()
        self.assertTrue(os.path.exists('test_model.pth'))

if __name__ == '__main__':
    unittest.main()