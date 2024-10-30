import torch
import yaml
import sqlite3
import pandas as pd
from model_training.trainer import TradeModel
import logging

class SignalGenerator:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.model_path = config['model_training']['model_path']
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = TradeModel(input_dim=3, hidden_dim=50, output_dim=2).to(self.device)
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model.eval()

        # Setup logging
        self.logger = logging.getLogger('SignalGenerator')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/signal_generator.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def generate_signal(self):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT ma_10, macd, rsi FROM indicators
            ORDER BY timestamp DESC LIMIT 1
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        if df.empty:
            self.logger.warning("No indicator data available to generate signal.")
            return None
        data = torch.tensor(df[['ma_10', 'macd', 'rsi']].values, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            output = self.model(data)
            _, predicted = torch.max(output, 1)
            signal = predicted.item()
        self.logger.info(f"Generated signal: {signal}")
        return signal  # 1 for Buy, 0 for Sell

if __name__ == "__main__":
    generator = SignalGenerator()
    signal = generator.generate_signal()
    print(f"Generated Signal: {'Buy' if signal == 1 else 'Sell'}")