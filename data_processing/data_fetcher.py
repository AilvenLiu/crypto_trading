import asyncio
import websockets
import json
import sqlite3
from datetime import datetime
import yaml
import pandas as pd
import numpy as np
from threading import Thread
import time

class DataFetcher:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.symbol = config['data_processing']['symbol']
        self.ws_url = config['data_processing']['ws_url']
        self.buffer = []
        self.batch_size = 100  # 批量插入大小
        self.flush_interval = 60  # 每60秒刷新缓存
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.last_timestamp = None
        self.flushing = False

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
        self.conn.commit()

    async def subscribe_real_time_data(self):
        async with websockets.connect(self.ws_url) as websocket:
            subscribe_message = {
                "op": "subscribe",
                "args": [{
                    "channel": "trades",
                    "instId": self.symbol
                }]
            }
            await websocket.send(json.dumps(subscribe_message))
            print(f"Subscribed to trades channel for {self.symbol}")

            async for message in websocket:
                data = json.loads(message)
                if 'data' in data:
                    trades = data['data']
                    self.process_trade_data(trades)

    def process_trade_data(self, trades):
        for trade in trades:
            trade_id = trade['tradeId']
            timestamp = datetime.utcfromtimestamp(trade['ts'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            price = float(trade['px'])
            size = float(trade['sz'])
            side = trade['side']
            self.buffer.append((trade_id, timestamp, price, size, side))
        
        # Flush buffer if batch size reached
        if len(self.buffer) >= self.batch_size:
            self.insert_trades()

    def insert_trades(self):
        if self.flushing:
            return
        self.flushing = True
        try:
            self.cursor.executemany('''
                INSERT OR IGNORE INTO trades (trade_id, timestamp, price, size, side)
                VALUES (?, ?, ?, ?, ?)
            ''', self.buffer)
            self.conn.commit()
            print(f"Inserted {len(self.buffer)} trades into the database.")
            self.buffer = []
        except sqlite3.Error as e:
            print(f"SQLite insertion error: {e}")
            # 可以在此加入更多的错误处理逻辑
        finally:
            self.flushing = False

    def flush_buffer_periodically(self):
        while True:
            time.sleep(self.flush_interval)
            if self.buffer:
                self.insert_trades()

    def start_with_flush(self):
        flush_thread = Thread(target=self.flush_buffer_periodically)
        flush_thread.daemon = True
        flush_thread.start()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.subscribe_real_time_data())

    def fetch_historical_data(self, start_time, end_time):
        # 实现历史数据获取的逻辑
        # 这部分需要根据OKX的API文档进行具体实现
        pass

if __name__ == "__main__":
    fetcher = DataFetcher()
    # 启动历史数据获取（需要实现）
    # fetcher.fetch_historical_data(start_time, end_time)
    # 启动实时数据接收与定期刷新
    fetcher.start_with_flush()
