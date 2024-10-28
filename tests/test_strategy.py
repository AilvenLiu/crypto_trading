import unittest
from strategies.trend_following import TrendFollowingStrategy

class TestTrendFollowingStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = TrendFollowingStrategy(input_size=10, hidden_size=50, output_size=3)

    def test_generate_signal(self):
        market_data = [1.0] * 10
        signal = self.strategy.generate_signal(market_data)
        self.assertIn(signal, [0, 1, 2])

if __name__ == '__main__':
    unittest.main()
