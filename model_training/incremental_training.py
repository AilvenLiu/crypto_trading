import torch
import sqlite3
import pandas as pd
from torch.utils.data import Dataset, DataLoader
import logging

class TradeDataset(Dataset):
    def __init__(self, data):
        self.X = data[['ma_10', 'macd', 'rsi']].values
        self.y = data['signal'].values

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return torch.tensor(self.X[idx], dtype=torch.float32), torch.tensor(self.y[idx], dtype=torch.long)

class IncrementalTrainer:
    def __init__(self, model, optimizer, criterion, device, db_path, model_path):
        self.model = model
        self.optimizer = optimizer
        self.criterion = criterion
        self.device = device
        self.db_path = db_path
        self.model_path = model_path

        # Setup logging
        self.logger = logging.getLogger('IncrementalTrainer')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/incremental_trainer.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_last_timestamp(self):
        # Implement retrieval of the last timestamp from the model_path or checkpoint
        # For simplicity, assume it's stored in a metadata table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(timestamp) FROM strategies')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else '1970-01-01 00:00:00'

    def load_new_data(self, last_timestamp):
        conn = sqlite3.connect(self.db_path)
        query = f'''
            SELECT indicators.ma_10, indicators.macd, indicators.rsi, strategies.signal
            FROM indicators
            JOIN strategies ON indicators.timestamp = strategies.timestamp
            WHERE indicators.timestamp > '{last_timestamp}'
        '''
        df = pd.read_sql_query(query, conn)
        df.dropna(inplace=True)
        conn.close()
        self.logger.info(f"Loaded {len(df)} new records for incremental training.")
        return df

    def train_incrementally(self, batch_size=32, epochs=5):
        last_timestamp = self.get_last_timestamp()
        df = self.load_new_data(last_timestamp)
        if df.empty:
            self.logger.info("No new data to train on.")
            return
        dataset = TradeDataset(df)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        self.model.train()
        for epoch in range(epochs):
            for X, y in dataloader:
                X = X.to(self.device)
                y = y.to(self.device)
                outputs = self.model(X)
                loss = self.criterion(outputs, y)
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
            self.logger.info(f"Incremental Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")
        torch.save(self.model.state_dict(), self.model_path)
        self.logger.info("Incremental training completed and model updated.")
