from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import yaml
from monitoring.backend.alert_manager import AlertManager
from monitoring.backend.performance_monitor import PerformanceMonitor

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # 请更改为实际的密钥
socketio = SocketIO(app, cors_allowed_origins="*")

# Load config
with open('config/config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Initialize components
alert_manager = AlertManager(config_path='config/config.yaml')
performance_monitor = PerformanceMonitor(config_path='config/config.yaml', socketio=socketio)

# Import executor after app initialization to avoid circular imports
from trading_execution.executor import get_executor
executor = get_executor(config_path='config/config.yaml')

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
            executor.update_leverage(new_leverage)
            socketio.emit('control_response', {'status': f'leverage updated to {new_leverage}x'})
            return jsonify({'status': f'leverage updated to {new_leverage}x'})
        else:
            return jsonify({'error': 'No leverage value provided'}), 400
    else:
        return jsonify({'error': 'Unknown command'}), 400

@socketio.on('connect')
def handle_connect():
    app.logger.info(f"Client connected: {request.sid}")
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    # Start Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000)
