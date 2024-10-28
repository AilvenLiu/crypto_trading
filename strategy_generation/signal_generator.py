import torch
import yaml
import sqlite3
import pandas as pd
from model_training.trainer import TradeModel

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

    def generate_signal(self):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT ma, macd, rsi FROM indicators
            ORDER BY timestamp DESC LIMIT 1
        '''
        df = pd.read_sql_query(query, conn)
        if df.empty:
            return None
        data = torch.tensor(df[['ma', 'macd', 'rsi']].values, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            output = self.model(data)
            _, predicted = torch.max(output, 1)
            signal = predicted.item()
        return signal  # 1 for Buy, 0 for Sell

if __name__ == "__main__":
    generator = SignalGenerator()
    signal = generator.generate_signal()
    print(f"Generated Signal: {'Buy' if signal == 1 else 'Sell'}")