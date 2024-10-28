import pandas as pd
import sqlite3
import yaml
from datetime import datetime
from threading import Thread
import time
import json
import numpy as np
import threading

class Indicators:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.db_path = config['data_processing']['db_path']
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.threads = []
        self.stop_event = threading.Event()

    def calculate_ma(self, df, window=20):
        df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
        return df

    def calculate_macd(self, df, span_short=12, span_long=26, span_signal=9):
        exp1 = df['close'].ewm(span=span_short, adjust=False).mean()
        exp2 = df['close'].ewm(span=span_long, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal_line'] = df['macd'].ewm(span=span_signal, adjust=False).mean()
        return df

    def calculate_rsi(self, df, periods=14):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def compute_ma(self, df, window):
        try:
            df = self.calculate_ma(df, window)
            print(f"MA{window} calculated.")
        except Exception as e:
            print(f"Error calculating MA{window}: {e}")

    def compute_macd_func(self, df):
        try:
            df = self.calculate_macd(df)
            print("MACD calculated.")
        except Exception as e:
            print(f"Error calculating MACD: {e}")

    def compute_rsi_func(self, df):
        try:
            df = self.calculate_rsi(df)
            print("RSI calculated.")
        except Exception as e:
            print(f"Error calculating RSI: {e}")

    def compute_all_indicators(self):
        try:
            self.cursor.execute('''
                SELECT timestamp, close FROM kline
                ORDER BY timestamp ASC
            ''')
            data = self.cursor.fetchall()
            df = pd.DataFrame(data, columns=['timestamp', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calculate multiple indicators in separate threads
            ma_windows = [10, 20, 50]
            for window in ma_windows:
                thread = threading.Thread(target=self.compute_ma, args=(df.copy(), window))
                thread.start()
                self.threads.append(thread)
            
            macd_thread = threading.Thread(target=self.compute_macd_func, args=(df.copy(),))
            macd_thread.start()
            self.threads.append(macd_thread)
            
            rsi_thread = threading.Thread(target=self.compute_rsi_func, args=(df.copy(),))
            rsi_thread.start()
            self.threads.append(rsi_thread)
            
            # Wait for all threads to complete
            for thread in self.threads:
                thread.join()
            
            # After all calculations, insert into database (simplified example)
            latest_data = {
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'ma_10': df['ma_10'].iloc[-1],
                'ma_20': df['ma_20'].iloc[-1],
                'ma_50': df['ma_50'].iloc[-1],
                'macd': df['macd'].iloc[-1],
                'signal_line': df['signal_line'].iloc[-1],
                'rsi': df['rsi'].iloc[-1],
                'other_indicators': json.dumps({"custom_indicator": 0})
            }
            with self.lock:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO indicators (timestamp, ma_10, ma_20, ma_50, macd, signal_line, rsi, other_indicators)
                    VALUES (:timestamp, :ma_10, :ma_20, :ma_50, :macd, :signal_line, :rsi, :other_indicators)
                ''', latest_data)
                self.conn.commit()
            print(f"Indicators calculated and stored for {latest_data['timestamp']}")
            self.threads = []
        except Exception as e:
            print(f"Error calculating indicators: {e}")

    def start(self):
        while not self.stop_event.is_set():
            self.compute_all_indicators()
            time.sleep(60)  # Compute indicators every minute

    def stop(self):
        self.stop_event.set()

    def start_in_thread(self):
        self.monitor_thread = Thread(target=self.start)
        self.monitor_thread.start()

if __name__ == "__main__":
    indicators = Indicators()
    indicators.start_in_thread()
