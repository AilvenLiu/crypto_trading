import unittest
from strategy_generation.signal_generator import SignalGenerator
import sqlite3
import os
import yaml

class TestSignalGenerator(unittest.TestCase):
    def setUp(self):
        self.test_db = 'test_signal.db'
        with open('config/config_simulation.yaml', 'r') as file:
            config = yaml.safe_load(file)
        config['data_processing']['db_path'] = self.test_db
        config['model_training']['model_path'] = 'test_model.pth'
        with open('config/test_config.yaml', 'w') as file:
            yaml.dump(config, file)
        # Initialize test data and model
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE indicators (
                timestamp TEXT PRIMARY KEY,
                ma REAL,
                macd REAL,
                rsi REAL,
                other_indicators TEXT
            )
        ''')
        # Insert sample indicators
        for i in range(10):
            timestamp = f"2023-10-01 12:{i:02d}:00"
            cursor.execute('''
                INSERT INTO indicators (timestamp, ma, macd, rsi, other_indicators)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, 50000+i, 150+i, 70+i, "{}"))
        conn.commit()
        conn.close()
        # Create a dummy model
        import torch
        from model_training.trainer import TradeModel
        model = TradeModel(input_dim=3, hidden_dim=50, output_dim=2)
        torch.save(model.state_dict(), 'test_model.pth')
        self.generator = SignalGenerator(config_path='config/test_config.yaml')

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists('test_model.pth'):
            os.remove('test_model.pth')
        if os.path.exists('config/test_config.yaml'):
            os.remove('config/test_config.yaml')

    def test_generate_signal(self):
        signal = self.generator.generate_signal()
        self.assertIn(signal, [0, 1])

if __name__ == '__main__':
    unittest.main()
