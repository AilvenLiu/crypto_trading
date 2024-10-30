import queue
import threading

class Trader:
    def __init__(self, executor):
        self.executor = executor
        self.signal_queue = queue.Queue()

    def send_signal(self, signal):
        self.signal_queue.put(signal)

    def start(self):
        signal_thread = threading.Thread(target=self.monitor_signals)
        signal_thread.daemon = True
        signal_thread.start()

    def monitor_signals(self):
        while True:
            signal = self.signal_queue.get()
            if signal:
                self.executor.execute_signal(signal)