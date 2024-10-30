import psutil
import time
import logging
import yaml
from monitoring.backend.alert_manager import AlertManager

class PerformanceMonitor:
    def __init__(self, config_path='config/config.yaml', socketio=None):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.cpu_threshold = config['monitoring']['performance']['cpu_threshold']
        self.memory_threshold = config['monitoring']['performance']['memory_threshold']
        self.db_write_threshold = config['monitoring']['performance']['db_write_threshold']
        self.volatility_threshold = config['monitoring']['performance']['volatility_threshold']
        self.alert_manager = AlertManager(config_path=config_path)
        self.socketio = socketio

        # Setup logging
        self.logger = logging.getLogger('PerformanceMonitor')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/performance_monitor.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_cpu_usage(self):
        return psutil.cpu_percent(interval=1)

    def get_memory_usage(self):
        return psutil.virtual_memory().percent

    def get_db_write_rate(self):
        # Implement actual logic to calculate DB writes per minute
        # Placeholder: simulate
        return 60  # Example value

    def calculate_market_volatility(self):
        # Implement actual volatility calculation
        # Placeholder: simulate
        return 0.04  # Example volatility

    def get_metrics(self):
        cpu = self.get_cpu_usage()
        memory = self.get_memory_usage()
        db_writes = self.get_db_write_rate()
        volatility = self.calculate_market_volatility()
        return {
            'cpu_usage': cpu,
            'memory_usage': memory,
            'db_write_per_minute': db_writes,
            'volatility': volatility
        }

    def monitor_performance(self):
        while True:
            metrics = self.get_metrics()
            self.logger.info(f"Metrics: {metrics}")
            if metrics['cpu_usage'] > self.cpu_threshold:
                subject = 'High CPU Usage Alert'
                body = f"CPU usage is at {metrics['cpu_usage']}%, exceeding the threshold of {self.cpu_threshold}%."
                self.alert_manager.alert(subject, body, method='email')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            if metrics['memory_usage'] > self.memory_threshold:
                subject = 'High Memory Usage Alert'
                body = f"Memory usage is at {metrics['memory_usage']}%, exceeding the threshold of {self.memory_threshold}%."
                self.alert_manager.alert(subject, body, method='telegram')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            if metrics['db_write_per_minute'] < self.db_write_threshold:
                subject = 'Low Database Write Rate Alert'
                body = f"Database write rate is at {metrics['db_write_per_minute']} writes per minute, below the threshold of {self.db_write_threshold}."
                self.alert_manager.alert(subject, body, method='email')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            if metrics['volatility'] > self.volatility_threshold:
                subject = 'High Market Volatility Alert'
                body = f"Market volatility is at {metrics['volatility']:.2%}, exceeding the threshold of {self.volatility_threshold:.2%}."
                self.alert_manager.alert(subject, body, method='telegram')
                if self.socketio:
                    self.socketio.emit('alert', {'subject': subject, 'body': body})

            time.sleep(60)  # Monitor every minute
