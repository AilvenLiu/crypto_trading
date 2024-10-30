import pytest
import yaml
import os

@pytest.fixture(scope="session")
def config(tmp_path_factory):
    config_path = tmp_path_factory.mktemp("data") / "test_config.yaml"
    config_data = {
        'monitoring': {
            'performance': {
                'cpu_threshold': 80,
                'memory_threshold': 80,
                'db_write_threshold': 100,
                'volatility_threshold': 0.1
            }
        },
        'data_processing': {
            'db_path': str(tmp_path_factory.mktemp("data") / "test.db")
        },
        'trading_execution': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'passphrase': 'test_passphrase',
            'base_url': 'https://www.okx.com',
            'symbol': 'BTC-USDT-SWAP',
            'initial_leverage': 5,
            'risk_management': {
                'min_leverage': 1.0,
                'max_leverage': 10.0,
                'max_position': 1000000,
                'daily_loss_limit': 0.05
            }
        }
    }
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)
    return config_path