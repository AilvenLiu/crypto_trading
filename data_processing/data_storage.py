import sqlite3
import yaml
from datetime import datetime

class DataStorage:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def insert_kline(self, timestamp, open_price, high, low, close, volume):
        self.cursor.execute('''
            INSERT OR IGNORE INTO kline (timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, open_price, high, low, close, volume))
        self.conn.commit()

    def insert_order_book(self, timestamp, bids, asks):
        self.cursor.execute('''
            INSERT OR IGNORE INTO order_book (timestamp, bids, asks)
            VALUES (?, ?, ?)
        ''', (timestamp, bids, asks))
        self.conn.commit()

    def insert_trade(self, trade_id, timestamp, price, size, side):
        self.cursor.execute('''
            INSERT OR IGNORE INTO trades (trade_id, timestamp, price, size, side)
            VALUES (?, ?, ?, ?, ?)
        ''', (trade_id, timestamp, price, size, side))
        self.conn.commit()

    def insert_indicator(self, timestamp, ma, macd, rsi, other_indicators):
        self.cursor.execute('''
            INSERT OR IGNORE INTO indicators (timestamp, ma, macd, rsi, other_indicators)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, ma, macd, rsi, other_indicators))
        self.conn.commit()

    def fetch_latest_kline(self):
        self.cursor.execute('''
            SELECT * FROM kline ORDER BY timestamp DESC LIMIT 1
        ''')
        return self.cursor.fetchone()

    def fetch_order_book(self):
        self.cursor.execute('''
            SELECT * FROM order_book ORDER BY timestamp DESC LIMIT 1
        ''')
        return self.cursor.fetchone()

    def fetch_trades(self):
        self.cursor.execute('''
            SELECT * FROM trades ORDER BY timestamp DESC LIMIT 100
        ''')
        return self.cursor.fetchall()

    def fetch_indicators(self):
        self.cursor.execute('''
            SELECT * FROM indicators ORDER BY timestamp DESC LIMIT 1
        ''')
        return self.cursor.fetchone()