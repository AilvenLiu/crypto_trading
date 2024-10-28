import numpy as np

class PerformanceMetrics:
    def __init__(self):
        self.metrics = {}

    def calculate_metrics(self, df):
        self.metrics['Total Return'] = df['strategy_returns'].sum()
        self.metrics['Mean Return'] = df['strategy_returns'].mean()
        self.metrics['Volatility'] = df['strategy_returns'].std()
        self.metrics['Sharpe Ratio'] = self.metrics['Mean Return'] / self.metrics['Volatility'] * np.sqrt(252)
        self.metrics['Max Drawdown'] = self.max_drawdown(df['capital'])

    def max_drawdown(self, capital):
        roll_max = capital.cummax()
        drawdown = (capital - roll_max) / roll_max
        return drawdown.min()

    def print_metrics(self):
        for key, value in self.metrics.items():
            print(f"{key}: {value}")