const socket = io('http://localhost:5000');

// Real-time metrics update
function fetchMetrics() {
    fetch('http://localhost:5000/metrics')
        .then(response => response.json())
        .then(data => {
            document.getElementById('cpu').innerText = `${data.cpu_usage}%`;
            document.getElementById('memory').innerText = `${data.memory_usage}%`;
            document.getElementById('disk').innerText = `${data.disk_usage}%`;
            document.getElementById('strategy').innerText = `${(data.strategy_return * 100).toFixed(2)}%`;
        })
        .catch(error => console.error('Error fetching metrics:', error));
}

// Setup chart
const ctx = document.getElementById('performanceChart').getContext('2d');
const performanceChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],  // Time labels
        datasets: [{
            label: 'Strategy Returns',
            data: [],
            borderColor: 'rgba(75, 192, 192, 1)',
            fill: false
        }]
    },
    options: {
        scales: {
            x: { display: true, title: { display: true, text: 'Time' } },
            y: { display: true, title: { display: true, text: 'Return (%)' } }
    }
});

// Update chart with new data
function updateChart(returnValue) {
    const now = new Date().toLocaleTimeString();
    performanceChart.data.labels.push(now);
    performanceChart.data.datasets[0].data.push((returnValue * 100).toFixed(2));
    if (performanceChart.data.labels.length > 20) {
        performanceChart.data.labels.shift();
        performanceChart.data.datasets[0].data.shift();
    }
    performanceChart.update();
}

// Handle alerts from backend
socket.on('alert', function(data) {
    showAlert(data.subject, data.body);
});

// Alert popup
function showAlert(subject, body) {
    const alertContainer = document.getElementById('alertContainer');
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert-popup';
    alertDiv.innerHTML = `<strong>${subject}</strong><br>${body}`;
    alertContainer.appendChild(alertDiv);

    alertDiv.onclick = () => {
        alertContainer.removeChild(alertDiv);
    };

    // Auto-remove after 10 seconds
    setTimeout(() => {
        if (alertContainer.contains(alertDiv)) {
            alertContainer.removeChild(alertDiv);
        }
    }, 10000);
}

// User interaction handling
document.getElementById('pauseStrategy').addEventListener('click', () => {
    sendControlCommand('pause');
});

document.getElementById('resumeStrategy').addEventListener('click', () => {
    sendControlCommand('resume');
});

document.getElementById('updateRisk').addEventListener('click', () => {
    const newLeverage = document.getElementById('riskParam').value;
    sendControlCommand('update_risk', { 'new_leverage': parseFloat(newLeverage) });
});

function sendControlCommand(command, data = {}) {
    fetch('http://localhost:5000/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 'command': command, 'data': data })
    })
    .then(response => response.json())
    .then(data => {
        console.log(`Command ${command} executed:`, data);
    })
    .catch(error => console.error('Error sending control command:', error));
}

// Periodically fetch and update metrics
setInterval(fetchMetrics, 5000); // every 5 seconds

// Example: Update chart with dummy data (replace with actual strategy returns)
socket.on('metrics_update', function(data) {
    updateChart(data.strategy_return);
});
