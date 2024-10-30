import torch
import torch.nn as nn
import torch.optim as optim
import yaml
import os
import sqlite3
import pandas as pd
import logging
from torch.utils.data import Dataset, DataLoader
from model_training.incremental_training import IncrementalTrainer

class TradeDataset(Dataset):
    def __init__(self, data):
        self.X = data[['ma_10', 'macd', 'rsi']].values
        self.y = data['signal'].values

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return torch.tensor(self.X[idx], dtype=torch.float32), torch.tensor(self.y[idx], dtype=torch.long)

class TradeModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(TradeModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        return out

class Trainer:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.model_path = config['model_training']['model_path']
        self.input_dim = config['model_training']['input_dim']
        self.hidden_dim = config['model_training']['hidden_dim']
        self.output_dim = config['model_training']['output_dim']
        self.learning_rate = config['model_training']['learning_rate']
        self.epochs = config['model_training']['epochs']
        self.batch_size = config['model_training']['batch_size']
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = TradeModel(input_dim=self.input_dim, hidden_dim=self.hidden_dim, output_dim=self.output_dim).to(self.device)
        if os.path.exists(self.model_path):
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            print("Loaded existing model.")
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

        # Setup logging
        self.logger = logging.getLogger('Trainer')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/trainer.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def load_data(self, incremental=False, last_timestamp=None):
        conn = sqlite3.connect(self.db_path)
        if incremental and last_timestamp:
            query = f'''
                SELECT indicators.ma_10, indicators.macd, indicators.rsi, strategies.signal
                FROM indicators
                JOIN strategies ON indicators.timestamp = strategies.timestamp
                WHERE indicators.timestamp > '{last_timestamp}'
            '''
        else:
            query = f'''
                SELECT indicators.ma_10, indicators.macd, indicators.rsi, strategies.signal
                FROM indicators
                JOIN strategies ON indicators.timestamp = strategies.timestamp
                WHERE indicators.timestamp BETWEEN '{self.start_date}' AND '{self.end_date}'
            '''
        df = pd.read_sql_query(query, conn)
        df.dropna(inplace=True)
        conn.close()
        self.logger.info(f"Loaded {len(df)} records for training.")
        return df

    def train(self):
        df = self.load_data()
        dataset = TradeDataset(df)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        for epoch in range(self.epochs):
            for X, y in dataloader:
                X = X.to(self.device)
                y = y.to(self.device)
                outputs = self.model(X)
                loss = self.criterion(outputs, y)
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
            self.logger.info(f"Epoch [{epoch+1}/{self.epochs}], Loss: {loss.item():.4f}")
        torch.save(self.model.state_dict(), self.model_path)
        self.logger.info("Model training completed and saved.")

    def incremental_train(self):
        incremental_trainer = IncrementalTrainer(
            model=self.model,
            optimizer=self.optimizer,
            criterion=self.criterion,
            device=self.device,
            db_path=self.db_path,
            model_path=self.model_path
        )
        incremental_trainer.train_incrementally()

if __name__ == "__main__":
    trainer = Trainer()
    trainer.train()
