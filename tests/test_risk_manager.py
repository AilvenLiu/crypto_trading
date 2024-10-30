import unittest
from trading_execution.risk_manager import RiskManager
from unittest.mock import Mock

class TestRiskManager(unittest.TestCase):
    def setUp(self):
        # Create a mock Executor
        self.mock_executor = Mock()
        self.risk_manager = RiskManager(config_path='config/test_config.yaml', executor=self.mock_executor)
    
    def test_manage_risk_within_limits(self):
        initial_loss = self.risk_manager.daily_loss
        self.risk_manager.manage_risk(signal=1, size=1000)
        # Since simulate_trade_pnl uses random, we can only check if daily_loss has been updated
        self.assertNotEqual(self.risk_manager.daily_loss, initial_loss)
    
    def test_manage_risk_exceeds_limit(self):
        # Simulate a loss that exceeds the limit
        self.risk_manager.daily_loss_limit = 0.05  # 5%
        self.risk_manager.daily_loss = -0.06
        self.risk_manager.trigger_risk_controls()
        self.mock_executor.pause_trading.assert_called_once()
        self.mock_executor.get_open_orders.assert_called_once()
        self.mock_executor.cancel_order.assert_called()  # Ensure cancel_order was called
    
    def test_update_leverage_valid(self):
        self.risk_manager.update_leverage(10)
        self.assertEqual(self.risk_manager.current_leverage, 10)
    
    def test_update_leverage_invalid(self):
        previous_leverage = self.risk_manager.current_leverage
        self.risk_manager.update_leverage(100)  # Exceeds max_leverage
        # Check that leverage was not updated
        self.assertEqual(self.risk_manager.current_leverage, previous_leverage)

if __name__ == '__main__':
    unittest.main()
