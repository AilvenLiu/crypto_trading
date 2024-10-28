import smtplib
from email.mime.text import MIMEText
import yaml
import requests
import logging
from logging.handlers import RotatingFileHandler

class AlertManager:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.email_config = config['monitoring']['email']
        self.telegram_config = config['monitoring']['telegram']

        # 设置日志记录
        self.logger = logging.getLogger('AlertManager')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('logs/alerts.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def send_email_alert(self, subject, body):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_config['username']
        msg['To'] = ", ".join(self.email_config['recipients'])

        try:
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.sendmail(self.email_config['username'], self.email_config['recipients'], msg.as_string())
            self.logger.info(f"Email alert sent: {subject}")
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    def send_telegram_alert(self, body):
        url = f"https://api.telegram.org/bot{self.telegram_config['token']}/sendMessage"
        payload = {
            'chat_id': self.telegram_config['chat_id'],
            'text': body
        }
        try:
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                self.logger.info("Telegram alert sent.")
            else:
                self.logger.error(f"Failed to send Telegram alert: {response.text}")
        except Exception as e:
            self.logger.error(f"Exception in sending Telegram alert: {e}")

    def alert(self, subject, body, method='email'):
        if method == 'email':
            self.send_email_alert(subject, body)
        elif method == 'telegram':
            self.send_telegram_alert(body)
        # Log the alert
        self.logger.info(f"Alert triggered: {subject} - {body}")
