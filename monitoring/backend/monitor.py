from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import yaml
import logging
from monitoring.backend.alert_manager import AlertManager
from monitoring.backend.performance_monitor import PerformanceMonitor
from trading_execution.executor import Executor

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change to actual secret
socketio = SocketIO(app, cors_allowed_origins="*")

# Load config
with open('config/config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Initialize components
alert_manager = AlertManager(config_path='config/config.yaml')
performance_monitor = PerformanceMonitor(config_path='config/config.yaml', socketio=socketio)
executor = Executor(config_path='config/config.yaml')

@app.route('/metrics', methods=['GET'])
def get_metrics():
    metrics = performance_monitor.get_metrics()
    return jsonify(metrics)

@app.route('/control', methods=['POST'])
def control_commands():
    data = request.get_json()
    command = data.get('command')
    command_data = data.get('data', {})
    
    if command == 'pause':
        executor.pause_trading()
        socketio.emit('control_response', {'status': 'paused'})
        return jsonify({'status': 'paused'})
    elif command == 'resume':
        executor.resume_trading()
        socketio.emit('control_response', {'status': 'resumed'})
        return jsonify({'status': 'resumed'})
    elif command == 'update_risk':
        new_leverage = command_data.get('new_leverage')
        if new_leverage:
            executor.risk_manager.update_leverage(new_leverage)
            socketio.emit('control_response', {'status': f'Leverage updated to {new_leverage}x'})
            return jsonify({'status': f'Leverage updated to {new_leverage}x'})
        else:
            return jsonify({'error': 'No leverage value provided'}), 400
    else:
        return jsonify({'error': 'Unknown command'}), 400

if __name__ == "__main__":
    # Start performance monitoring in a separate thread
    monitor_thread = threading.Thread(target=performance_monitor.monitor_performance)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Start Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000)
