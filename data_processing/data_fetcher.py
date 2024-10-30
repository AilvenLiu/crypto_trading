import asyncio
import json
import sqlite3
from threading import Thread, Lock, Event
from datetime import datetime
import time
import yaml
import logging
import websockets
from data_processing.data_storage import DataStorage

class DataFetcher:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.ws_url = config['data_processing']['ws_url']
        self.symbol = config['data_processing']['symbol']
        self.buffer = []
        self.batch_size = 100
        self.flush_interval = 60  # seconds
        self.storage = DataStorage(config_path)
        self.last_timestamp = None
        self.flushing = False
        self.lock = Lock()

        # Setup logging
        self.logger = logging.getLogger('DataFetcher')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/data_fetcher.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

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
            self.logger.info(f"Subscribed to trades channel for {self.symbol}")

            async for message in websocket:
                data = json.loads(message)
                if 'data' in data:
                    trades = data['data']
                    self.process_trade_data(trades)

    def process_trade_data(self, trades):
        with self.lock:
            for trade in trades:
                trade_id = trade['tradeId']
                timestamp = datetime.utcfromtimestamp(trade['ts'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                price = float(trade['px'])
                size = float(trade['sz'])
                side = trade['side']
                self.buffer.append((trade_id, timestamp, price, size, side))

            if len(self.buffer) >= self.batch_size:
                self.insert_trades()

    def insert_trades(self):
        if self.flushing:
            return
        self.flushing = True
        try:
            self.storage.insert_trades(self.buffer)
            self.logger.info(f"Inserted {len(self.buffer)} trades into the database.")
            self.buffer = []
        except sqlite3.Error as e:
            self.logger.error(f"SQLite insertion error: {e}")
        finally:
            self.flushing = False

    def flush_buffer_periodically(self):
        while not self.stop_event.is_set():
            time.sleep(self.flush_interval)
            with self.lock:
                if self.buffer:
                    self.insert_trades()

    def start_with_flush(self):
        flush_thread = Thread(target=self.flush_buffer_periodically)
        flush_thread.daemon = True
        flush_thread.start()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.subscribe_real_time_data())
        except Exception as e:
            self.logger.error(f"Asynchronous data fetching failed: {e}")
        finally:
            loop.close()

    def start(self):
        self.stop_event = Event()
        data_thread = Thread(target=self.start_with_flush)
        data_thread.daemon = True
        data_thread.start()
        self.logger.info("DataFetcher started.")

if __name__ == "__main__":
    fetcher = DataFetcher()
    fetcher.start()
