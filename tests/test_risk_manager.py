import unittest
from unittest.mock import Mock, patch
from trading_execution.risk_manager import RiskManager
import yaml
import os
from datetime import datetime, timedelta

class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.config = {
            'trading_execution': {
                'risk_management': {
                    'min_leverage': 1.0,
                    'max_leverage': 10.0,
                    'max_position': 1000000,
                    'daily_loss_limit': 0.05
                },
                'initial_leverage': 5.0
            },
            'data_processing': {
                'db_path': 'test.db'
            }
        }
        with open('config/test_config.yaml', 'w') as f:
            yaml.dump(self.config, f)
        self.risk_manager = RiskManager(config_path='config/test_config.yaml')

    def tearDown(self):
        if os.path.exists('config/test_config.yaml'):
            os.remove('config/test_config.yaml')

    def test_calculate_position_size(self):
        size = self.risk_manager.calculate_position_size()
        self.assertLessEqual(size, self.config['trading_execution']['risk_management']['max_position'])
        self.assertGreater(size, 0)

    def test_manage_risk_within_limits(self):
        self.risk_manager.daily_loss = -0.02  # 2% loss
        self.risk_manager.manage_risk(signal=1, size=100000)
        self.assertTrue(self.risk_manager.is_trading_allowed)

    def test_manage_risk_exceeds_limits(self):
        self.risk_manager.daily_loss = -0.06  # 6% loss
        self.risk_manager.manage_risk(signal=1, size=100000)
        self.assertFalse(self.risk_manager.is_trading_allowed)

    def test_update_leverage(self):
        new_leverage = 3.0
        self.risk_manager.update_leverage(new_leverage)
        self.assertEqual(self.risk_manager.current_leverage, new_leverage)

    def test_update_leverage_exceeds_max(self):
        with self.assertRaises(ValueError):
            self.risk_manager.update_leverage(15.0)

    def test_daily_loss_reset(self):
        self.risk_manager.daily_loss = -0.03
        self.risk_manager.last_calculation_day = datetime.utcnow().date() - timedelta(days=1)
        self.risk_manager.check_and_reset_daily_loss()
        self.assertEqual(self.risk_manager.daily_loss, 0.0)

if __name__ == '__main__':
    unittest.main()
