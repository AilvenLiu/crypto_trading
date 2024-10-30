import pytest
from unittest.mock import Mock, patch
from flask import Flask
import sys
import os
import yaml

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.backend.monitor import app
from monitoring.backend.performance_monitor import PerformanceMonitor
from monitoring.backend.alert_manager import AlertManager

@pytest.fixture
def mock_config():
    config = {
        'monitoring': {
            'performance': {
                'cpu_threshold': 80,
                'memory_threshold': 80,
                'db_write_threshold': 100,
                'volatility_threshold': 0.1
            }
        },
        'trading_execution': {  # Ensure trading_execution config is present
            'risk_management': {
                'min_leverage': 1,
                'max_leverage': 50,
                'max_position': 1000000,
                'daily_loss_limit': 0.05
            },
            'initial_leverage': 5
        },
        'data_processing': {
            'db_path': 'test.db'
        }
    }
    os.makedirs('config', exist_ok=True)
    with open('config/test_config.yaml', 'w') as f:
        yaml.dump(config, f)
    yield config
    if os.path.exists('config/test_config.yaml'):
        os.remove('config/test_config.yaml')

@pytest.fixture
def mock_executor():
    with patch('monitoring.backend.monitor.Executor') as mock:
        yield mock

@pytest.fixture
def mock_performance_monitor():
    with patch('monitoring.backend.monitor.PerformanceMonitor') as mock:
        yield mock

@pytest.fixture
def client(mock_config, mock_executor, mock_performance_monitor):
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Setup mock PerformanceMonitor instance
        mock_performance_monitor_instance = mock_performance_monitor.return_value
        mock_performance_monitor_instance.get_current_metrics.return_value = {
            'cpu_usage': 33.2,
            'memory_usage': 79.7,
            'disk_usage': 60.0,
            'db_write_per_minute': 60,
            'volatility': 0.04
        }
        yield client

def test_get_metrics(client, mock_performance_monitor):
    response = client.get('/metrics')
    assert response.status_code == 200
    data = response.get_json()
    assert 'cpu_usage' in data
    assert 'memory_usage' in data
    assert 'disk_usage' in data
    assert 'db_write_per_minute' in data
    assert 'volatility' in data

def test_control_pause(client, mock_executor):
    response = client.post('/control', json={'command': 'pause'})
    assert response.status_code == 200
    assert 'paused' in response.get_json()['status']

def test_control_resume(client, mock_executor):
    response = client.post('/control', json={'command': 'resume'})
    assert response.status_code == 200
    assert 'resumed' in response.get_json()['status']

def test_control_update_risk(client, mock_executor):
    response = client.post('/control',
                           json={'command': 'update_risk',
                                 'data': {'new_leverage': 5}})
    assert response.status_code == 200
    assert 'Leverage updated to 5x' in response.get_json()['status']

def test_control_invalid_command(client, mock_executor):
    response = client.post('/control', json={'command': 'invalid_command'})
    assert response.status_code == 400
    assert 'error' in response.get_json()
    assert response.get_json()['error'] == 'Unknown command'

def test_control_missing_leverage(client, mock_executor):
    response = client.post('/control',
                           json={'command': 'update_risk',
                                 'data': {}})
    assert response.status_code == 400
    assert 'error' in response.get_json()
    assert response.get_json()['error'] == 'No leverage value provided'

