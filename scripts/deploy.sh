#!/bin/bash

# 设置环境变量
ENVIRONMENT=$1

if [ "$ENVIRONMENT" == "real" ]; then
    CONFIG_FILE="config/config_real.yaml"
elif [ "$ENVIRONMENT" == "simulation" ]; then
    CONFIG_FILE="config/config_simulation.yaml"
else
    echo "Usage: ./deploy.sh [real|simulation]"
    exit 1
fi

echo "Deploying system in $ENVIRONMENT environment using $CONFIG_FILE..."

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python -c "
import sqlite3, yaml
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

# 配置日志路径 (ensure logs directory exists)
mkdir -p logs

# 设置资源限制 (example for Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Limit CPU usage to 80%
    cpulimit --limit=80 --background -- python data_processing/data_fetcher.py
    # Similar resource limits can be applied to other modules
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # MacOS resource limiting can be implemented using different tools or left as is
    python data_processing/data_fetcher.py &
else
    echo "Unsupported OS. Exiting."
    exit 1
fi

echo "Starting Data Fetcher..."
python data_processing/data_fetcher.py &

echo "Starting Indicators Calculator..."
python data_processing/indicators.py &

echo "Starting Model Trainer..."
python model_training/trainer.py &

echo "Starting Signal Generator..."
python strategy_generation/signal_generator.py &

echo "Starting Multi Strategy Manager..."
python strategy_generation/multi_strategy_manager.py &

echo "Starting Trading Executor..."
python trading_execution/executor.py &

echo "Starting Monitoring Backend..."
python monitoring/backend/monitor.py &

echo "Starting Monitoring Frontend..."
cd monitoring/frontend
python -m http.server 8000 &

