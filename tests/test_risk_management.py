import unittest
from risk_management.risk_controller import RiskController

class TestRiskController(unittest.TestCase):
    def setUp(self):
        self.risk_controller = RiskController(input_size=2, hidden_size=10, output_size=1)

    def test_adjust_leverage(self):
        signal = 0.6
        volatility = 0.04
        leverage = self.risk_controller.adjust_leverage(signal, volatility)
        self.assertTrue(1.0 <= leverage <= 50.0)

if __name__ == '__main__':
    unittest.main()
