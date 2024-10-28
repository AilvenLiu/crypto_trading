import psutil
import time
import yaml
import pandas as pd
import numpy as np
from threading import Thread
from monitoring.backend.alert_manager import AlertManager  # Updated import
from flask_socketio import SocketIO
import sqlite3

class PerformanceMonitor:
    def __init__(self, config_path='config/config.yaml', socketio=None):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.cpu_threshold = config['monitoring']['performance']['cpu_threshold']
        self.memory_threshold = config['monitoring']['performance']['memory_threshold']
        self.db_write_threshold = config['monitoring']['performance']['db_write_threshold']
        self.volatility_threshold = config['monitoring']['performance']['volatility_threshold']
        self.alert_manager = AlertManager(config_path)
        self.db_path = config['data_processing']['db_path']
        self.socketio = socketio

    def get_metrics(self):
        metrics = {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'db_write_per_minute': self.get_db_write_count()
        }
        return metrics

    def get_db_write_count(self):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT COUNT(*) as write_count FROM trades
            WHERE timestamp >= datetime('now', '-1 minute')
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['write_count'].iloc[0] if not df.empty else 0

    def calculate_market_volatility(self):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT close FROM kline
            ORDER BY timestamp DESC LIMIT 60
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        if len(df) < 2:
            return 0
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(60)  # 简单波动率估计
        return volatility

    def monitor_performance(self):
        while True:
            metrics = self.get_metrics()
            # 检查CPU使用率
            if metrics['cpu_usage'] > self.cpu_threshold:
                subject = '高CPU使用率警报'
                body = f"当前CPU使用率为 {metrics['cpu_usage']}% ，已超过阈值 {self.cpu_threshold}% 。"
                self.alert_manager.alert(subject, body, method='email')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            # 检查内存使用率
            if metrics['memory_usage'] > self.memory_threshold:
                subject = '高内存使用率警报'
                body = f"当前内存使用率为 {metrics['memory_usage']}% ，已超过阈值 {self.memory_threshold}% 。"
                self.alert_manager.alert(subject, body, method='telegram')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            # 检查数据库写入量
            if metrics['db_write_per_minute'] < self.db_write_threshold:
                subject = '低数据库写入量警报'
                body = f"过去一分钟内数据库写入量为 {metrics['db_write_per_minute']} 条，低于阈值 {self.db_write_threshold} 条。"
                self.alert_manager.alert(subject, body, method='email')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            # 检查市场波动性
            volatility = self.calculate_market_volatility()
            if volatility > self.volatility_threshold:
                subject = '市场波动性高警报'
                body = f"当前市场波动性为 {volatility:.2%}，已超过阈值 {self.volatility_threshold:.2%} 。"
                self.alert_manager.alert(subject, body, method='telegram')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            time.sleep(60)  # 每分钟检查一次

    def get_metrics_wrapper(self):
        return self.get_metrics()

    def start(self):
        monitoring_thread = Thread(target=self.monitor_performance)
        monitoring_thread.daemon = True
        monitoring_thread.start()

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    monitor.start()
    while True:
        time.sleep(1)
