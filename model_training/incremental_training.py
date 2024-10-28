import torch
import torch.nn as nn
import torch.optim as optim
import sqlite3
import pandas as pd
from torch.utils.data import Dataset, DataLoader

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
        return df

    def train_incrementally(self, batch_size=32, epochs=5):
        # Retrieve the last timestamp from the model_path or a checkpoint file
        # For simplicity, assume last_timestamp is stored externally
        last_timestamp = self.get_last_timestamp()
        df = self.load_new_data(last_timestamp)
        if df.empty:
            print("No new data to train on.")
            return
        dataset = TradeDataset(df)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        for epoch in range(epochs):
            for X, y in dataloader:
                X = X.to(self.device)
                y = y.to(self.device)
                outputs = self.model(X)
                loss = self.criterion(outputs, y)
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
        torch.save(self.model.state_dict(), self.model_path)
        print("Incremental training completed and model updated.")

    def get_last_timestamp(self):
        # Implement logic to retrieve last timestamp from the trained model or checkpoints
        # Placeholder implementation
        return '2023-09-30 23:59:59'
