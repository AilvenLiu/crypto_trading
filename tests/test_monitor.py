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
        'data_processing': {
            'db_path': 'test.db'
        }
    }
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
def client(mock_config, mock_executor, mock_performance_monitor):
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
@pytest.fixture
def mock_performance_monitor():
    with patch('monitoring.backend.monitor.PerformanceMonitor') as mock:
        mock.return_value.get_metrics.return_value = {
            'cpu_usage': 50.0,
            'memory_usage': 60.0,
            'disk_usage': 70.0,
            'db_write_per_minute': 100
        }
        yield mock

def test_get_metrics(client, mock_performance_monitor):
    response = client.get('/metrics')
    assert response.status_code == 200
    data = response.get_json()
    assert 'cpu_usage' in data
    assert 'memory_usage' in data
    assert 'disk_usage' in data
    assert 'db_write_per_minute' in data

def test_control_pause(client):
    response = client.post('/control', json={'command': 'pause'})
    assert response.status_code == 200
    assert response.get_json()['status'] == 'paused'

def test_control_resume(client):
    response = client.post('/control', json={'command': 'resume'})
    assert response.status_code == 200
    assert response.get_json()['status'] == 'resumed'

def test_control_update_risk(client):
    response = client.post('/control', 
                         json={'command': 'update_risk', 
                              'data': {'new_leverage': 5}})
    assert response.status_code == 200
    assert 'leverage updated to 5x' in response.get_json()['status']

def test_control_invalid_command(client):
    response = client.post('/control', json={'command': 'invalid'})
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Unknown command'

def test_control_missing_leverage(client):
    response = client.post('/control', 
                         json={'command': 'update_risk'})
    assert response.status_code == 400
    assert response.get_json()['error'] == 'No leverage value provided'

