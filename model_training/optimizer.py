from skopt import BayesSearchCV
from skopt.space import Real, Categorical, Integer
import torch
import torch.nn as nn
import torch.optim as optim
from model_training.trainer import TradeModel, Trainer
import yaml
import sqlite3
import pandas as pd

class HyperparameterOptimizer:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.model_path = config['model_training']['model_path']
        self.learning_rate = config['model_training']['learning_rate']
        self.epochs = config['model_training']['epochs']
        self.batch_size = config['model_training']['batch_size']
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

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
        return df

    def objective(self, hidden_dim, learning_rate):
        # Define a simple validation mechanism
        df = self.load_data()
        X = torch.tensor(df[['ma_10', 'macd', 'rsi']].values, dtype=torch.float32)
        y = torch.tensor(df['signal'].values, dtype=torch.long)
        
        model = TradeModel(input_dim=3, hidden_dim=int(hidden_dim), output_dim=2).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        
        dataset = torch.utils.data.TensorDataset(X, y)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)
        
        # Simple training loop
        model.train()
        for epoch in range(5):  # Limited epochs for optimization
            for batch_X, batch_y in dataloader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
        
        # Evaluate on the training set
        model.eval()
        with torch.no_grad():
            outputs = model(X.to(self.device))
            _, predicted = torch.max(outputs, 1)
            accuracy = (predicted.cpu() == y).float().mean().item()
        
        # Objective is to maximize accuracy
        return -accuracy

    def optimize(self):
        search_spaces = {
            'hidden_dim': Integer(20, 100),
            'learning_rate': Real(1e-4, 1e-2, prior='log-uniform')
        }

        optimizer = BayesSearchCV(
            estimator=None,  # Placeholder, as we're manually handling the training
            search_spaces=search_spaces,
            n_iter=20,
            scoring='neg_accuracy',
            cv=3,
            verbose=0
        )

        # Since we're handling the training manually, iterate through the search
        from skopt import gp_minimize

        res = gp_minimize(
            func=self.objective,
            dimensions=[Integer(20, 100, name='hidden_dim'), Real(1e-4, 1e-2, "log-uniform", name='learning_rate')],
            acq_func='EI',
            n_calls=20,
            random_state=0
        )

        best_hidden_dim, best_learning_rate = res.x
        print(f"Best hyperparameters: hidden_dim={best_hidden_dim}, learning_rate={best_learning_rate}")
        return best_hidden_dim, best_learning_rate