import smtplib
from email.mime.text import MIMEText
import logging
import yaml
import requests

class AlertManager:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.email_config = config['monitoring']['email']
        self.telegram_config = config['monitoring']['telegram']

        # Setup logging
        self.logger = logging.getLogger('AlertManager')
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler('logs/alert_manager.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def alert(self, subject, body, method='email'):
        if method == 'email':
            self.send_email(subject, body)
        elif method == 'telegram':
            self.send_telegram(subject, body)
        else:
            self.logger.error(f"Unknown alert method: {method}")

    def send_email(self, subject, body):
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.email_config['username']
            msg['To'] = ', '.join(self.email_config['recipients'])

            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.sendmail(self.email_config['username'], self.email_config['recipients'], msg.as_string())
            server.quit()
            self.logger.info(f"Email sent: {subject}")
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")

    def send_telegram(self, subject, body):
        try:
            token = self.telegram_config['token']
            chat_id = self.telegram_config['chat_id']
            message = f"{subject}\n{body}"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message
            }
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                self.logger.info(f"Telegram alert sent: {subject}")
            else:
                self.logger.error(f"Failed to send Telegram alert: {response.text}")
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
