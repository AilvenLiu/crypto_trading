import optuna
import torch
import torch.nn as nn
import torch.optim as optim
import yaml
import sqlite3
import pandas as pd
import logging
from model_training.trainer import TradeModel

class HyperparameterOptimizer:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.logger = logging.getLogger('HyperparameterOptimizer')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/hyperparameter_optimizer.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def load_data(self):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT indicators.ma_10, indicators.macd, indicators.rsi, strategies.signal
            FROM indicators
            JOIN strategies ON indicators.timestamp = strategies.timestamp
        '''
        df = pd.read_sql_query(query, conn)
        df.dropna(inplace=True)
        conn.close()
        self.logger.info(f"Loaded {len(df)} records for optimization.")
        return df

    def objective(self, trial):
        hidden_dim = trial.suggest_int('hidden_dim', 20, 100)
        learning_rate = trial.suggest_loguniform('learning_rate', 1e-5, 1e-2)
        
        model = TradeModel(input_dim=3, hidden_dim=hidden_dim, output_dim=2).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        
        df = self.load_data()
        X = torch.tensor(df[['ma_10', 'macd', 'rsi']].values, dtype=torch.float32)
        y = torch.tensor(df['signal'].values, dtype=torch.long)
        
        dataset = torch.utils.data.TensorDataset(X, y)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)
        
        model.train()
        for epoch in range(5):
            for batch_X, batch_y in dataloader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        
        model.eval()
        with torch.no_grad():
            outputs = model(X.to(self.device))
            _, predicted = torch.max(outputs, 1)
            accuracy = (predicted.cpu() == y).float().mean().item()
        
        self.logger.info(f"Trial - Hidden_dim: {hidden_dim}, Learning_rate: {learning_rate}, Accuracy: {accuracy}")
        return -accuracy  # Optuna minimizes the objective

    def optimize(self, n_trials=50):
        import optuna
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        study = optuna.create_study(direction='minimize')
        study.optimize(self.objective, n_trials=n_trials)
        self.logger.info(f"Best Trial: {study.best_trial.params}, Accuracy: {-study.best_trial.value}")
        return study.best_trial.params

if __name__ == "__main__":
    optimizer = HyperparameterOptimizer()
    best_params = optimizer.optimize()
    print(f"Best Parameters: {best_params}")