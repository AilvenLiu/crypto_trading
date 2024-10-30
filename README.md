# 基于 OKX 永续合约的高频量化交易系统


## Project Structure

```
crypto_trading
│
├── config/
│   ├── config.yaml
│   ├── config_simulation.yaml
│   ├── config_real.yaml
│   └── test_config.yaml
│
├── backtesting/
│   ├── __init__.py
│   └── backtester.py
│
├── data_processing/
│   ├── __init__.py
│   ├── data_fetcher.py
│   ├── data_storage.py
│   └── indicators.py
│
├── model_training/
│   ├── __init__.py
│   ├── optimizer.py
│   ├── trainer.py
│   └── incremental_training.py
│
├── scripts/
│   └── deploy.sh
│
├── strategy_generation/
│   ├── __init__.py
│   ├── multi_strategy_manager.py
│   └── signal_generator.py
│
├── trading_execution/
│   ├── __init__.py
│   ├── executor.py
│   └── risk_manager.py
│
├── monitoring/
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── alert_manager.py
│   │   ├── monitor.py
│   │   └── performance_monitor.py
│   └── frontend/
│       ├── index.html
│       ├── styles.css
│       └── app.js
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_backtester.py
│   ├── test_data_fetcher.py
│   ├── test_executor.py
│   ├── test_monitor.py
│   ├── test_risk_controller.py
│   ├── test_risk_manager.py
│   ├── test_signal_generator.py
│   ├── test_trader.py
│   └── test_trainer.py
│
├── requirements.txt
│
└── README.md
```

## 项目概述

本项目旨在实现一个高频量化交易系统，支持 OKX 永续合约交易，具备实时数据获取、策略回测、模型增量训练、信号生成、自动交易执行和可视化监控等功能。系统采用 C++ 和 Python 构建，前端监控使用 JavaScript，实现了数据处理、风险管理和性能监控的无缝集成。

## 模块说明

### 1. 数据处理模块 (`data_processing/`)

- **功能**: 负责历史和实时市场数据的获取、清洗、存储及指标计算。
- **关键类**:
  - `DataFetcher`: 通过 OKX API 和 WebSocket 接口获取数据。
  - `DataStorage`: 管理数据的本地存储。
  - `Indicators`: 计算各类技术指标（MA、MACD、RSI 等）。

### 2. 回测模块 (`backtesting/`)

- **功能**: 支持对策略在历史数据上的效果测试，包括盈亏、胜率、最大回撤等指标。
- **关键类**:
  - `Backtester`: 执行回测逻辑。
  - `PerformanceMetrics`: 评估回测结果。

### 3. 模型训练模块 (`model_training/`)

- **功能**: 基于 PyTorch 实现机器学习模型的训练和增量训练。
- **关键类**:
  - `Trainer`: 负责模型的初始训练。
  - `IncrementalTrainer`: 实现模型的增量训练逻辑。

### 4. 策略生成模块 (`strategy_generation/`)

- **功能**: 生成交易信号，支持多策略并行运行。
- **关键类**:
  - `SignalGenerator`: 根据模型输出生成交易信号。
  - `MultiStrategyManager`: 管理多个策略的信号生成。

### 5. 交易执行模块 (`trading_execution/`)

- **功能**: 实现自动交易执行，包含下单、撤单和风险管理。
- **关键类**:
  - `Executor`: 负责与 OKX API 对接，执行交易指令。
  - `RiskManager`: 动态调整仓位和杠杆，控制风险。

### 6. 监控模块 (`monitoring/`)

- **功能**: 提供系统性能和交易表现的可视化监控，同时处理报警和日志记录。
- **关键组件**:
  - **后端**:
    - `monitor.py`: 提供实时性能数据。
    - `alert_manager.py`: 处理报警通知。
    - `performance_monitor.py`: 监控系统性能指标。
  - **前端**:
    - `index.html`, `app.js`, `styles.css`: 实现交互式监控面板。

## 部署说明

### 前提条件

- **操作系统**: MacOS 或 Linux
- **Python**: 3.7+
- **C++**: 支持 C++17
- **依赖**: Docker（可选）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置系统

1. 编辑 `config/config.yaml`，根据需要选择环境（real 或 simulation），并填写相应的 API 密钥和其他配置。

2. 为真实环境创建 `config/config_real.yaml`，为模拟环境创建 `config/config_simulation.yaml`，并根据需求调整配置参数。

### 初始化数据库

部署脚本会自动初始化数据库。如果需要手动初始化，可以参考 `deploy.sh` 中的数据库初始化部分。

### 部署系统

运行部署脚本，指定环境类型（real 或 simulation）：

```bash
bash scripts/deploy.sh simulation
```

### 运行测试

运行测试脚本，确保所有模块功能正常：

```bash
bash scripts/test.sh
```

## 调试方法

### 日志查看

日志文件位于 `logs/system.log`。使用以下命令实时查看日志：

```bash
tail -f logs/system.log
```

### 监控界面

访问 `http://localhost:8000` 查看实时监控数据和系统性能。

### API接口

后端监控API位于 `http://localhost:5000/metrics`，可用于自定义监控需求。

## 二次开发

### 添加新策略

1. 在 `strategy_generation/` 目录下创建新的策略生成类，继承 `SignalGenerator`。
2. 修改 `MultiStrategyManager` 以加载新的策略生成器。

### 扩展风险管理

1. 在 `trading_execution/risk_manager.py` 中添加新的风险控制逻辑。
2. 更新 `Executor` 类以调用最新的风险管理功能。

### 优化交易引擎

调整 `trading_execution/` 下的 C++ 代码，实现更高效的订单处理和 API 调用。

## 贡献指南

欢迎提交 Issues 和 Pull Requests，贡献代码和优化建议，共同完善本高频量化交易系统。

## 联系方式

如有任何问题，请联系 [ailven.liu@nio.com](mailto:ailven.liu@nio.com)。

## 参考文献

- [OKX API 文档](https://www.okx.com/docs-v5/en/#rest-api)
- [PyTorch 文档](https://pytorch.org/docs/stable/index.html)
- [Flask 文档](https://flask.palletsprojects.com/)