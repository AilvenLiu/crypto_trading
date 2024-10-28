import unittest
from trading_engine.src.order_manager import OrderManager

class TestOrderManager(unittest.TestCase):
    def setUp(self):
        self.order_manager = OrderManager()
        self.order_manager.initialize()

    def test_fetch_order_book(self):
        self.order_manager.fetch_order_book()
        self.assertTrue(len(self.order_manager.order_book) > 0)

    def test_execute_orders(self):
        self.order_manager.execute_orders()
        # Add assertions based on mock behavior

if __name__ == '__main__':
    unittest.main()
