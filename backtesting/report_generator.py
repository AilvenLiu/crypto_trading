import pandas as pd
import matplotlib.pyplot as plt
import logging
from logging.handlers import RotatingFileHandler
class ReportGenerator:
    def __init__(self, report_path='backtesting/report.csv'):
        self.report_path = report_path
        self.logger = logging.getLogger('ReportGenerator')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/report_generator.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def generate(self):
        df = pd.read_csv(self.report_path, index_col=0)
        df.plot(kind='bar', figsize=(10, 6))
        plt.title('Backtesting Performance Metrics')
        plt.xlabel('Strategy')
        plt.ylabel('Values')
        plt.tight_layout()
        plt.savefig('backtesting/performance_metrics.png')
        plt.close()
        self.logger.info("Performance metrics chart generated at backtesting/performance_metrics.png")