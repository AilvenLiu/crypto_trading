import logging
import numpy as np

class PerformanceMetrics:
    def __init__(self):
        self.metrics = {}
        self.logger = logging.getLogger('PerformanceMetrics')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/performance_metrics.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def calculate_metrics(self, df, strategy_name='default'):
        returns = df['strategy_returns']
        total_return = returns.sum()
        max_drawdown = self.calculate_max_drawdown(df['capital'])
        sharpe_ratio = self.calculate_sharpe_ratio(returns)

        self.metrics[strategy_name] = {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }

        self.logger.info(f"Metrics for {strategy_name}: {self.metrics[strategy_name]}")

    def calculate_max_drawdown(self, capital):
        roll_max = capital.cummax()
        drawdown = (capital - roll_max) / roll_max
        return drawdown.min()

    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.0):
        excess_returns = returns - risk_free_rate
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)  # Annualized