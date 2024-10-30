import yaml
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import random

class RiskManager:
    def __init__(self, config_path='config/config.yaml', executor=None):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        trading_config = config['trading_execution']
        self.min_leverage = float(trading_config['risk_management']['min_leverage'])
        self.max_leverage = float(trading_config['risk_management']['max_leverage'])
        self.current_leverage = float(trading_config['initial_leverage'])
        self.max_position = float(trading_config['risk_management']['max_position'])
        self.daily_loss_limit = float(trading_config['risk_management']['daily_loss_limit'])  # 5%
    
        self.daily_loss = 0.0
        self.last_calculation_day = None
    
        # Reference to Executor is injected
        self.executor = executor
    
        # Setup logging
        self.logger = logging.getLogger('RiskManager')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/risk_manager.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
        self.logger.info("RiskManager initialized.")
    
    def calculate_position_size(self):
        position_size = min(self.max_position, self.current_leverage * 10)  # Example logic
        self.logger.info(f"Calculated position size: {position_size}")
        return position_size
    
    def manage_risk(self, signal, size):
        self.check_and_reset_daily_loss()
    
        # Update daily loss based on the size of the trade
        simulated_trade_pnl = self.simulate_trade_pnl(signal, size)
        self.daily_loss += simulated_trade_pnl
        self.logger.info(f"Updated daily loss: {self.daily_loss:.2%}")
    
        if self.daily_loss <= -self.daily_loss_limit:
            self.logger.warning(f"Daily loss limit reached: {self.daily_loss:.2%}. Initiating risk controls.")
            self.trigger_risk_controls()
    
    def simulate_trade_pnl(self, signal, size):
        # Simulate trade P&L for demonstration purposes
        pnl = random.uniform(-0.02, 0.02) * size * signal  # Simulate P&L between -2% to +2%
        return pnl
    
    def check_and_reset_daily_loss(self):
        current_day = datetime.utcnow().date()
        if self.last_calculation_day != current_day:
            self.logger.info(f"New day detected. Resetting daily loss from {self.daily_loss:.2%} to 0%.")
            self.daily_loss = 0.0
            self.last_calculation_day = current_day
    
    def trigger_risk_controls(self):
        try:
            if self.executor:
                self.executor.pause_trading()
                # Cancel all open orders
                open_orders = self.executor.get_open_orders()
                for order in open_orders:
                    self.executor.cancel_order(order['ordId'])
                self.logger.info("Trading paused and all open orders cancelled due to risk limits.")
            else:
                self.logger.error("Executor instance not provided to RiskManager.")
        except Exception as e:
            self.logger.error(f"Failed to trigger risk controls: {e}")
    
    def update_leverage(self, new_leverage):
        if self.min_leverage <= new_leverage <= self.max_leverage:
            self.current_leverage = new_leverage
            self.logger.info(f"Leverage updated to {new_leverage}x")
        else:
            self.logger.error(f"Leverage {new_leverage}x is out of bounds ({self.min_leverage}-{self.max_leverage}x)")
    
    def reset_daily_loss(self):
        self.daily_loss = 0.0
        self.last_calculation_day = datetime.utcnow().date()
        self.logger.info("Daily loss has been manually reset.")