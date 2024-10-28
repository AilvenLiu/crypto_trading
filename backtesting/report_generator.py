import pandas as pd
import matplotlib.pyplot as plt

class ReportGenerator:
    def __init__(self, report_path='backtesting/report.csv'):
        self.report_path = report_path
        self.df = pd.read_csv(self.report_path, index_col=0)

    def plot_performance(self):
        self.df.plot(kind='bar', figsize=(10, 6))
        plt.title('Strategy Performance Comparison')
        plt.ylabel('Total Return')
        plt.savefig('backtesting/performance_comparison.png')
        print("Performance comparison chart saved at backtesting/performance_comparison.png")

    def generate(self):
        self.plot_performance()