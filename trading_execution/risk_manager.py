import yaml
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from trading_execution.executor import get_executor

class RiskManager:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        trading_config = config['trading_execution']
        self.min_leverage = float(trading_config['risk_management']['min_leverage'])
        self.max_leverage = float(trading_config['risk_management']['max_leverage'])
        self.current_leverage = float(trading_config['initial_leverage'])
        self.max_position = float(trading_config['risk_management']['max_position'])
        self.daily_loss_limit = float(trading_config['risk_management']['daily_loss_limit'])  # 5%
        self.db_path = config['data_processing']['db_path']

        # Initialize loss tracking
        self.daily_loss = 0.0
        self.last_calculation_day = datetime.utcnow().date()

        # Reference to Executor
        self.executor = get_executor(config_path)

        # Setup logging
        self.logger = logging.getLogger('RiskManager')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/risk_manager.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("RiskManager initialized.")

    def calculate_position_size(self):
        """
        Calculate the position size based on current leverage and maximum position limit.
        """
        position_size = min(self.max_position, self.current_leverage * 10)  # Example logic
        self.logger.info(f"Calculated position size: {position_size}")
        return position_size

    def manage_risk(self, signal, size):
        """
        Manage risk by adjusting leverage based on trading signals and monitoring daily losses.

        :param signal: 1 for buy, -1 for sell, 0 for hold
        :param size: Size of the order
        """
        self.check_and_reset_daily_loss()

        # Example: Update daily loss based on the size of the trade
        # This should be replaced with actual P&L tracking logic
        simulated_trade_pnl = self.simulate_trade_pnl(signal, size)
        self.daily_loss += simulated_trade_pnl
        self.logger.info(f"Updated daily loss: {self.daily_loss:.2%}")

        if self.daily_loss <= -self.daily_loss_limit:
            self.logger.warning(f"Daily loss limit reached: {self.daily_loss:.2%}. Initiating risk controls.")
            self.trigger_risk_controls()

    def simulate_trade_pnl(self, signal, size):
        """
        Simulate trade P&L for demonstration purposes.

        :param signal: 1 for buy, -1 for sell
        :param size: Size of the order
        :return: Simulated P&L as a decimal percentage
        """
        # In a real implementation, fetch actual P&L from trading records
        # Here we simulate a random loss or profit
        import random
        pnl = random.uniform(-0.02, 0.02) * size * signal  # Simulate P&L between -2% to +2%
        return pnl

    def check_and_reset_daily_loss(self):
        """
        Check if a new day has started and reset daily loss if needed.
        """
        current_day = datetime.utcnow().date()
        if current_day != self.last_calculation_day:
            self.logger.info(f"New day detected. Resetting daily loss from {self.daily_loss:.2%} to 0%.")
            self.daily_loss = 0.0
            self.last_calculation_day = current_day

    def trigger_risk_controls(self):
        """
        Trigger risk control measures such as pausing trading and cancelling open orders.
        """
        try:
            self.executor.pause_trading()
            self.executor.cancel_all_orders()
            self.logger.info("Trading paused and all open orders cancelled due to risk limits.")
            # Optionally, integrate with AlertManager to notify stakeholders
        except Exception as e:
            self.logger.error(f"Failed to trigger risk controls: {e}")

    def reset_daily_loss(self):
        """
        Reset the daily loss manually if needed.
        """
        self.daily_loss = 0.0
        self.last_calculation_day = datetime.utcnow().date()
        self.logger.info("Daily loss has been manually reset.")

    def get_current_leverage(self):
        """
        Get the current leverage.

        :return: Current leverage
        """
        return self.current_leverage

    def set_leverage(self, new_leverage):
        """
        Set a new leverage level within the allowed range.

        :param new_leverage: The new leverage to be set
        """
        try:
            new_leverage = float(new_leverage)
            if self.min_leverage <= new_leverage <= self.max_leverage:
                self.current_leverage = new_leverage
                self.logger.info(f"Leverage manually set to {self.current_leverage}x.")
                self.executor.update_leverage(new_leverage)
            else:
                self.logger.warning(f"Attempted to set leverage to {new_leverage}x which is outside the allowed range.")
        except ValueError:
            self.logger.error(f"Invalid leverage value provided: {new_leverage}")

    def __str__(self):
        return (f"RiskManager(leverage={self.current_leverage}x, "
                f"daily_loss={self.daily_loss:.2%}, "
                f"daily_loss_limit={self.daily_loss_limit:.2%})")


if __name__ == "__main__":
    # Example usage
    risk_manager = RiskManager(config_path='config/config.yaml')
    position_size = risk_manager.calculate_position_size()
    risk_manager.manage_risk(signal=1, size=position_size)
