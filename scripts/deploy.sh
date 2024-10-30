#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

CONFIG_FILE='config/config.yaml'

# Initialize database
echo "Initializing database..."
python -c "
import sqlite3, yaml, json
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
conn = sqlite3.connect(config['data_processing']['db_path'])
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        trade_id TEXT PRIMARY KEY,
        timestamp TEXT,
        price REAL,
        size REAL,
        side TEXT
    )
''')
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
cursor.execute('''
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
cursor.execute('''
    CREATE TABLE IF NOT EXISTS strategies (
        timestamp TEXT PRIMARY KEY,
        signal INTEGER
    )
''')
conn.commit()
conn.close()
"
echo "Database initialized."

# Ensure logs directory exists
mkdir -p logs

# Start all services with resource limits if applicable
echo "Starting Data Fetcher..."
(eventlet.spawn python data_processing/data_fetcher.py &) # Using eventlet for concurrency

echo "Starting Indicators Calculator..."
(eventlet.spawn python data_processing/indicators.py &) 

echo "Starting Model Trainer..."
(eventlet.spawn python model_training/trainer.py &) 

echo "Starting Signal Generator..."
(eventlet.spawn python strategy_generation/signal_generator.py &) 

echo "Starting Multi Strategy Manager..."
(eventlet.spawn python strategy_generation/multi_strategy_manager.py &) 

echo "Starting Trading Executor..."
(eventlet.spawn python trading_execution/executor.py &) 

echo "Starting Monitoring Backend..."
(eventlet.spawn python monitoring/backend/monitor.py &) 

echo "Starting Monitoring Frontend..."
cd monitoring/frontend
python -m http.server 8000 &
cd ../../

echo "Deployment completed successfully."