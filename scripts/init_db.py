import sqlite3
import yaml

def initialize_database(config_path='config/config.yaml'):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    db_path = config['data_processing']['db_path']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建 trades 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            timestamp TEXT,
            price REAL,
            size REAL,
            side TEXT
        )
    ''')

    # 创建 kline 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kline (
            timestamp TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL
        )
    ''')

    # 创建 indicators 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicators (
            timestamp TEXT,
            ma10 REAL,
            ma20 REAL,
            ma50 REAL,
            macd REAL,
            signal_line REAL,
            rsi REAL,
            PRIMARY KEY (timestamp)
        )
    ''')

    # 创建 backtest_results 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backtest_results (
            strategy TEXT,
            timestamp TEXT,
            strategy_returns REAL,
            PRIMARY KEY (strategy, timestamp)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    initialize_database()