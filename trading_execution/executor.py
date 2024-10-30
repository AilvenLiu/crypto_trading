import requests
import json
import time
import yaml
import logging
import threading
from logging.handlers import RotatingFileHandler
from trading_execution.risk_manager import RiskManager
from trading_execution.trader import Trader

class Executor:
    def __init__(self, config_path='config/config.yaml', signal_queue=None):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.api_key = config['trading_execution']['api_key']
        self.api_secret = config['trading_execution']['api_secret']
        self.passphrase = config['trading_execution']['passphrase']
        self.base_url = config['trading_execution']['base_url']
        self.symbol = config['trading_execution']['symbol']
        self.leverage = float(config['trading_execution']['initial_leverage'])
        self.risk_manager = RiskManager(config_path=config_path, executor=self)
        self.trader = Trader(self)
        self.session = requests.Session()
        self.headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": "",
            "OK-ACCESS-TIMESTAMP": "",
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }
        self.trading_active = True
        self.order_lock = threading.Lock()
        self.open_orders = {}  # Mapping of order_id to order details

        # Setup logging
        self.logger = logging.getLogger('Executor')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/executor.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def place_order(self, action, size, price, type='limit'):
        """
        Places an order using OKX API.
        """
        order_data = {
            "instId": self.symbol,
            "tdMode": "cross",  # or "isolated"
            "side": action,
            "ordType": type,
            "sz": str(size),
            "px": str(price)
        }
        try:
            self.logger.info(f"Placing order: {order_data}")
            # Example: Signing and sending the request (Implement actual signing as per OKX API)
            response = self.session.post(f"{self.base_url}/api/v5/trade/order", headers=self.headers, data=json.dumps(order_data))
            data = response.json()
            if data.get("result"):
                order_id = data['data'][0]['ordId']
                with self.order_lock:
                    self.open_orders[order_id] = order_data
                return data['data'][0]
            else:
                self.logger.error(f"Failed to place order: {data.get('msg')}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Exception during placing order: {e}")
            return None

    def cancel_order(self, order_id):
        """
        Cancels an existing order using OKX API.
        """
        cancel_data = {
            "instId": self.symbol,
            "ordId": order_id
        }
        try:
            self.logger.info(f"Cancelling order: {order_id}")
            response = self.session.post(f"{self.base_url}/api/v5/trade/cancel-order", headers=self.headers, data=json.dumps(cancel_data))
            data = response.json()
            if data.get("result"):
                with self.order_lock:
                    self.open_orders.pop(order_id, None)
                self.logger.info(f"Order {order_id} cancelled successfully.")
                return True
            else:
                self.logger.error(f"Failed to cancel order {order_id}: {data.get('msg')}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Exception during cancelling order {order_id}: {e}")
            return False

    def get_open_orders(self):
        """
        Retrieves all open orders from OKX API.
        """
        try:
            self.logger.info("Fetching open orders.")
            response = self.session.get(f"{self.base_url}/api/v5/trade/orders-pending?instId={self.symbol}", headers=self.headers)
            data = response.json()
            if data.get("result"):
                return data['data']
            else:
                self.logger.error(f"Failed to retrieve open orders: {data.get('msg')}")
                return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Get open orders exception: {e}")
            return []

    def pause_trading(self):
        self.trading_active = False
        self.logger.info("Trading has been paused.")

    def resume_trading(self):
        self.trading_active = True
        self.logger.info("Trading has been resumed.")

    def monitor_signals(self, signal_queue):
        while True:
            signal = signal_queue.get()
            if signal is None:
                break
            self.logger.info(f"Received signal: {signal}")
            self.execute_signal(signal)

    def execute_signal(self, signal):
        if not self.trading_active:
            self.logger.info("Trading is paused. Ignoring signal.")
            return
        action, size, price = signal
        order = self.place_order(action, size, price)
        if order:
            order_id = order['ordId']
            self.logger.info(f"Order placed: {order_id}")
            # Integrate with RiskManager
            signal_value = 1 if action.lower() == 'buy' else -1
            self.risk_manager.manage_risk(signal=signal_value, size=size)

    def start(self):
        signal_thread = threading.Thread(target=self.monitor_signals, args=(self.trader.signal_queue,))
        signal_thread.daemon = True
        signal_thread.start()
        self.logger.info("Executor started and listening to signal queue.")