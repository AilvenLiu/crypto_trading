import yaml
import requests
import time
import threading
from trading_execution.risk_manager import RiskManager
import json
import logging
from logging.handlers import RotatingFileHandler
import hashlib
import hmac
import base64
from datetime import datetime
import queue

_executor_instance = None

def get_executor(config_path='config/config.yaml'):
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = Executor(config_path)
    return _executor_instance   

class Executor:
    def __init__(self, config_path='config/config.yaml', signal_queue=None):
        self.config_path = config_path
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.api_key = config['trading_execution']['api_key']
        self.api_secret = config['trading_execution']['api_secret']
        self.passphrase = config['trading_execution']['passphrase']
        self.base_url = config['trading_execution']['base_url']
        self.symbol = config['trading_execution']['symbol']
        self.leverage = float(config['trading_execution']['initial_leverage'])
        self.risk_manager = RiskManager(config_path)
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

        self.logger.info("Executor initialized.")

        # Signal queue for receiving trading signals
        self.signal_queue = signal_queue or queue.Queue()

    def sign_request(self, method, request_path, body=''):
        timestamp = str(time.time())
        message = timestamp + method + request_path + body
        h = hmac.new(base64.b64decode(self.api_secret), message.encode('utf-8'), hashlib.sha256)
        signature = base64.b64encode(h.digest()).decode()
        return signature, timestamp

    def place_order(self, side, size, price=None, order_type='market'):
        request_path = '/api/v5/trade/order'
        method = 'POST'
        body = {
            "instId": self.symbol,
            "tdMode": "cross",  # Trading mode: 'cross' or 'isolated'
            "side": side,
            "ordType": order_type,
            "sz": str(size)
        }
        if price and order_type in ['limit', 'post_only']:
            body["px"] = str(price)
        body_json = json.dumps(body)
        signature, timestamp = self.sign_request(method, request_path, body_json)
        headers = self.headers.copy()
        headers["OK-ACCESS-SIGN"] = signature
        headers["OK-ACCESS-TIMESTAMP"] = timestamp

        try:
            response = self.session.post(self.base_url + request_path, headers=headers, data=body_json)
            response.raise_for_status()
            data = response.json()
            if data['retCode'] == '0':
                order_id = data['data'][0]['ordId']
                with self.order_lock:
                    self.open_orders[order_id] = {
                        "side": side,
                        "size": size,
                        "status": "open",
                        "timestamp": datetime.utcnow()
                    }
                self.logger.info(f"Placed order: ID {order_id}, Side {side}, Size {size}")
                # Start monitoring the order
                monitor_thread = threading.Thread(target=self.monitor_order, args=(order_id,))
                monitor_thread.daemon = True
                monitor_thread.start()
                return order_id
            else:
                self.logger.error(f"Order placement failed: {data['msg']}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Order placement exception: {e}")
            return None

    def cancel_order(self, order_id):
        request_path = '/api/v5/trade/cancel-order'
        method = 'POST'
        body = {
            "ordId": order_id
        }
        body_json = json.dumps(body)
        signature, timestamp = self.sign_request(method, request_path, body_json)
        headers = self.headers.copy()
        headers["OK-ACCESS-SIGN"] = signature
        headers["OK-ACCESS-TIMESTAMP"] = timestamp

        try:
            response = self.session.post(self.base_url + request_path, headers=headers, data=body_json)
            response.raise_for_status()
            data = response.json()
            if data['retCode'] == '0':
                with self.order_lock:
                    if order_id in self.open_orders:
                        self.open_orders[order_id]['status'] = 'cancelled'
                self.logger.info(f"Cancelled order: ID {order_id}")
                return True
            else:
                self.logger.error(f"Order cancellation failed: {data['msg']}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Order cancellation exception: {e}")
            return False

    def get_open_orders(self):
        request_path = '/api/v5/trade/orders-pending'
        method = 'GET'
        signature, timestamp = self.sign_request(method, request_path)
        headers = self.headers.copy()
        headers["OK-ACCESS-SIGN"] = signature
        headers["OK-ACCESS-TIMESTAMP"] = timestamp

        params = {
            "instId": self.symbol
        }

        try:
            response = self.session.get(self.base_url + request_path, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if data['retCode'] == '0':
                orders = data['data']
                self.logger.info(f"Retrieved {len(orders)} open orders.")
                return orders
            else:
                self.logger.error(f"Failed to retrieve open orders: {data['msg']}")
                return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Get open orders exception: {e}")
            return []

    def cancel_all_orders(self):
        """
        Cancel all open orders.
        """
        try:
            orders = self.get_open_orders()
            for order in orders:
                order_id = order['ordId']
                success = self.cancel_order(order_id)
                if success:
                    self.logger.info(f"Cancelled order ID: {order_id}")
                else:
                    self.logger.error(f"Failed to cancel order ID: {order_id}")
            self.logger.info("All open orders have been processed for cancellation.")
        except Exception as e:
            self.logger.error(f"Error cancelling orders: {e}")

    def execute_trade(self, signal, size):
        """
        Execute a trade based on the signal.
        
        :param signal: 1 for buy, -1 for sell, 0 for hold
        :param size: Size of the order
        """
        if signal == 1:
            side = 'buy'
        elif signal == -1:
            side = 'sell'
        else:
            self.logger.warning(f"Unknown signal: {signal}")
            return

        order_id = self.place_order(side, size)
        if order_id:
            self.logger.info(f"Trade executed: Signal {signal}, Size {size}, Order ID {order_id}")
        else:
            self.logger.error("Failed to execute trade due to order placement failure.")

    def monitor_order(self, order_id):
        """
        Monitor the status of a placed order until it is filled or cancelled.
        
        :param order_id: The ID of the order to monitor
        """
        while True:
            with self.order_lock:
                if order_id not in self.open_orders:
                    self.logger.info(f"Order ID {order_id} is no longer being tracked.")
                    break
                order_status = self.open_orders[order_id]['status']
                if order_status in ['filled', 'cancelled']:
                    self.logger.info(f"Order ID {order_id} has been {order_status}.")
                    del self.open_orders[order_id]
                    break
            time.sleep(5)  # Poll every 5 seconds
            self.update_order_status(order_id)

    def update_order_status(self, order_id):
        """
        Update the status of a specific order.
        
        :param order_id: The ID of the order to update
        """
        request_path = f'/api/v5/trade/order'
        method = 'GET'
        signature, timestamp = self.sign_request(method, request_path)
        headers = self.headers.copy()
        headers["OK-ACCESS-SIGN"] = signature
        headers["OK-ACCESS-TIMESTAMP"] = timestamp

        params = {
            "instId": self.symbol,
            "ordId": order_id
        }

        try:
            response = self.session.get(self.base_url + request_path, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if data['retCode'] == '0' and data['data']:
                order = data['data'][0]
                status = order['state']
                with self.order_lock:
                    if order_id in self.open_orders:
                        self.open_orders[order_id]['status'] = status
                self.logger.info(f"Order ID {order_id} updated to status: {status}")
            else:
                self.logger.error(f"Failed to update order status: {data['msg']}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Order status update exception: {e}")

    def get_signal(self):
        """
        Fetch the latest trading signal from the signal queue.
        
        :return: Tuple of (signal, size) where signal is 1 (buy), -1 (sell), or 0 (hold)
                 and size is the order size.
        """
        try:
            signal, size = self.signal_queue.get(timeout=1)  # Wait up to 1 second for a signal
            self.logger.info(f"Fetched signal: {signal}, Size: {size}")
            return signal, size
        except queue.Empty:
            return None, None

    def run(self):
        """
        Main trading loop.
        """
        self.logger.info("Executor trading loop started.")
        while True:
            if not self.trading_active:
                time.sleep(1)
                continue

            signal, size = self.get_signal()
            if signal and size:
                self.execute_trade(signal, size)

            time.sleep(0.1)  # Adjust sleep time for desired frequency

    def pause_trading(self):
        """
        Pause the trading execution.
        """
        self.trading_active = False
        self.logger.info("Trading execution paused.")

    def resume_trading(self):
        """
        Resume the trading execution.
        """
        self.trading_active = True
        self.logger.info("Trading execution resumed.")

    def update_leverage(self, new_leverage):
        """
        Update the leverage and set it on the exchange.
        
        :param new_leverage: The new leverage to be set
        """
        try:
            new_leverage = float(new_leverage)
            if self.risk_manager.min_leverage <= new_leverage <= self.risk_manager.max_leverage:
                self.leverage = new_leverage
                self.risk_manager.current_leverage = self.leverage
                self.logger.info(f"Leverage updated to {self.leverage}x")
                self.set_leverage_on_exchange()
            else:
                self.logger.warning(f"Leverage {new_leverage}x is outside the allowed range.")
        except ValueError:
            self.logger.error(f"Invalid leverage value: {new_leverage}")

    def set_leverage_on_exchange(self):
        """
        Set leverage on the exchange.
        """
        request_path = '/api/v5/account/set-leverage'
        method = 'POST'
        body = {
            "instId": self.symbol,
            "lever": str(int(self.leverage))
        }
        body_json = json.dumps(body)
        signature, timestamp = self.sign_request(method, request_path, body_json)
        headers = self.headers.copy()
        headers["OK-ACCESS-SIGN"] = signature
        headers["OK-ACCESS-TIMESTAMP"] = timestamp

        try:
            response = self.session.post(self.base_url + request_path, headers=headers, data=body_json)
            response.raise_for_status()
            data = response.json()
            if data['retCode'] == '0':
                self.logger.info(f"Leverage set to {self.leverage}x on exchange.")
            else:
                self.logger.error(f"Failed to set leverage: {data['msg']}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Set leverage exception: {e}")

    def receive_signal(self, signal, size):
        """
        Receive a trading signal and put it into the signal queue.
        
        :param signal: 1 for buy, -1 for sell, 0 for hold
        :param size: Size of the order
        """
        if signal not in [1, -1, 0]:
            self.logger.warning(f"Invalid signal received: {signal}")
            return
        if not self.trading_active:
            self.logger.warning("Trading is currently paused. Signal ignored.")
            return
        if signal == 0:
            self.logger.info("Hold signal received. No action taken.")
            return
        self.signal_queue.put((signal, size))
        self.logger.info(f"Received signal: {signal}, Size: {size}")

if __name__ == "__main__":
    # Create a shared signal queue
    signal_q = queue.Queue()

    # Initialize Executor with the signal queue
    executor = Executor(config_path='config/config.yaml', signal_queue=signal_q)
    executor.start()

    # Example: Initialize and start the strategy generation module
    from strategy_generation.multi_strategy_manager import MultiStrategyManager

    strategy_manager = MultiStrategyManager(signal_queue=signal_q, config_path='config/config.yaml')
    strategy_manager.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        executor.logger.info("Executor stopped by user.")
