import logging
from logging.handlers import RotatingFileHandler
from trading_execution.executor import Executor
from datetime import datetime, timedelta

class RiskController:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.min_leverage = float(config['trading_execution']['risk_management']['min_leverage'])
        self.max_leverage = float(config['trading_execution']['risk_management']['max_leverage'])
        self.max_position = float(config['trading_execution']['risk_management']['max_position'])
        self.daily_loss_limit = float(config['trading_execution']['risk_management']['daily_loss_limit'])
        self.current_leverage = float(config['trading_execution']['initial_leverage'])
        self.daily_loss = 0.0
        self.last_reset = datetime.utcnow().date()

        self.executor = Executor(config_path=config_path)

        # Setup logging
        self.logger = logging.getLogger('RiskController')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/risk_controller.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("RiskController initialized.")

    def update(self, pnl):
        self.daily_loss += pnl
        self.logger.info(f"Updated daily loss: {self.daily_loss:.2%}")
        if self.daily_loss <= -self.daily_loss_limit:
            self.trigger_controls()

    def check_reset(self):
        current_day = datetime.utcnow().date()
        if current_day != self.last_reset:
            self.daily_loss = 0.0
            self.last_reset = current_day
            self.logger.info("Daily loss reset.")

    def trigger_controls(self):
        self.logger.warning("Daily loss limit exceeded. Triggering risk controls.")
        self.executor.pause_trading()
        open_orders = self.executor.get_open_orders()
        for order in open_orders:
            self.executor.cancel_order(order['ordId'])
        # Further risk controls can be implemented here

    def adjust_leverage(self, pnl):
        # Implement dynamic leverage adjustment based on performance
        if pnl < 0:
            self.current_leverage = max(self.min_leverage, self.current_leverage - 1)
        else:
            self.current_leverage = min(self.max_leverage, self.current_leverage + 1)
        self.logger.info(f"Adjusted leverage to {self.current_leverage}x")