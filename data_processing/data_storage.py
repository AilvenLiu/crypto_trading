import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import json
import yaml

class DataStorage:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

        # Setup logging
        self.logger = logging.getLogger('DataStorage')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/data_storage.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                timestamp TEXT,
                price REAL,
                size REAL,
                side TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS kline (
                timestamp TEXT PRIMARY KEY,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                timestamp TEXT PRIMARY KEY,
                ma_10 REAL,
                ma_20 REAL,
                ma_50 REAL,
                macd REAL,
                signal_line REAL,
                rsi REAL,
                other_indicators TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                timestamp TEXT PRIMARY KEY,
                signal INTEGER
            )
        ''')
        self.conn.commit()

    def insert_trades(self, trades):
        self.cursor.executemany('''
            INSERT OR IGNORE INTO trades (trade_id, timestamp, price, size, side)
            VALUES (?, ?, ?, ?, ?)
        ''', trades)
        self.conn.commit()

    def insert_order_book(self, timestamp, bids, asks):
        self.cursor.execute('''
            INSERT OR IGNORE INTO order_book (timestamp, bids, asks)
            VALUES (?, ?, ?)
        ''', (timestamp, json.dumps(bids), json.dumps(asks)))
        self.conn.commit()

    def insert_indicator(self, timestamp, ma, macd, rsi, other_indicators):
        self.cursor.execute('''
            INSERT OR IGNORE INTO indicators (timestamp, ma_10, ma_20, ma_50, macd, signal_line, rsi, other_indicators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, ma.get('ma_10'), ma.get('ma_20'), ma.get('ma_50'), macd.get('macd'),
              macd.get('signal_line'), rsi.get('rsi'), json.dumps(other_indicators)))
        self.conn.commit()

    def close(self):
        self.conn.close()
        self.logger.info("Database connection closed.")