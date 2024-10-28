import unittest
from trading_execution.executor import Executor
import yaml
import os
from unittest.mock import patch

class TestExecutor(unittest.TestCase):
    def setUp(self):
        with open('config/config_simulation.yaml', 'r') as file:
            config = yaml.safe_load(file)
        config['trading_execution']['api_key'] = 'test_key'
        config['trading_execution']['api_secret'] = 'test_secret'
        config['trading_execution']['passphrase'] = 'test_passphrase'
        config['trading_execution']['base_url'] = 'https://www.okx.com'
        config['trading_execution']['symbol'] = 'BTC-USDT-SWAP'
        config['trading_execution']['initial_leverage'] = 5
        with open('config/test_config.yaml', 'w') as file:
            yaml.dump(config, file)
        self.executor = Executor(config_path='config/test_config.yaml')

    def tearDown(self):
        if os.path.exists('config/test_config.yaml'):
            os.remove('config/test_config.yaml')

    @patch('trading_execution.executor.requests.Session.post')
    def test_place_order(self, mock_post):
        mock_post.return_value.json.return_value = {"result": True, "msg": "Order placed"}
        response = self.executor.place_order('buy', 10, price=50000, type='limit')
        self.assertEqual(response['result'], True)

    @patch('trading_execution.executor.requests.Session.post')
    def test_cancel_order(self, mock_post):
        mock_post.return_value.json.return_value = {"result": True, "msg": "Order canceled"}
        response = self.executor.cancel_order('12345')
        self.assertEqual(response['result'], True)

if __name__ == '__main__':
    unittest.main()