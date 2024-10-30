import requests
import json
import time
import logging
import threading
from logging.handlers import RotatingFileHandler
from trading_execution.risk_manager import RiskManager
from trading_execution.trader import Trader

def get_executor(config_path='config/config.yaml'):
    return Executor(config_path=config_path)

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
        self.risk_manager = RiskManager(config_path)
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

    def sign_request(self, method, request_path, body=''):
        # Implement OKX API signing
        timestamp = str(time.time())
        message = timestamp + method + request_path + body
        signature = self.generate_signature(message)
        return signature, timestamp

    def generate_signature(self, message):
        import hmac, hashlib
        return hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    def place_order(self, side, size, price=None, order_type='limit'):
        request_path = '/api/v5/trade/order'
        method = 'POST'
        body = {
            "instId": self.symbol,
            "tdMode": "isolated",
            "side": side.lower(),
            "ordType": order_type.upper(),
            "sz": str(size),
            "slOrdPx": str(price) if price else None
        }
        body = {k: v for k, v in body.items() if v is not None}
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
                    self.open_orders[order_id] = {'side': side, 'size': size, 'price': price, 'status': 'open'}
                self.logger.info(f"Placed order: ID {order_id}, Side: {side}, Size: {size}, Price: {price}")
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
        order_id = self.place_order(action, size, price)
        if order_id:
            self.logger.info(f"Order placed: {order_id}")
            # Integrate with RiskManager
            self.risk_manager.manage_risk(signal=1 if action.lower() == 'buy' else -1, size=size)

    def start(self):
        signal_thread = threading.Thread(target=self.monitor_signals, args=(self.trader.signal_queue,))
        signal_thread.daemon = True
        signal_thread.start()
        self.logger.info("Executor started and listening to signal queue.")

if __name__ == "__main__":
    import queue
    signal_q = queue.Queue()
    executor = Executor(signal_queue=signal_q)
    executor.start()