const ctx = document.getElementById('performanceChart').getContext('2d');
let chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'CPU 使用率',
            data: [],
            borderColor: 'rgba(255, 99, 132, 1)',
            fill: false
        }, {
            label: '内存使用率',
            data: [],
            borderColor: 'rgba(54, 162, 235, 1)',
            fill: false
        }, {
            label: '磁盘使用率',
            data: [],
            borderColor: 'rgba(75, 192, 192, 1)',
            fill: false
        }, {
            label: '策略回报率',
            data: [],
            borderColor: 'rgba(153, 102, 255, 1)',
            fill: false
        }]
    },
    options: {
        responsive: true,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'minute'
                },
                title: {
                    display: true,
                    text: '时间'
                }
            },
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: '百分比 (%)'
                }
            }
        }
    }
});

function fetchMetrics() {
    fetch('http://localhost:5000/metrics')
        .then(response => response.json())
        .then(data => {
            const now = new Date();
            chart.data.labels.push(now);
            chart.data.datasets[0].data.push(data.cpu_usage);
            chart.data.datasets[1].data.push(data.memory_usage);
            chart.data.datasets[2].data.push(data.disk_usage);
            chart.data.datasets[3].data.push(data.strategy_returns ? (data.strategy_returns * 100).toFixed(2) : 0);
            
            // 保持数据量在一定范围内，例如100个点
            if (chart.data.labels.length > 100) {
                chart.data.labels.shift();
                chart.data.datasets.forEach(dataset => dataset.data.shift());
            }

            chart.update();

            // 更新HTML中的指标展示
            document.getElementById('cpu').innerText = `${data.cpu_usage}%`;
            document.getElementById('memory').innerText = `${data.memory_usage}%`;
            document.getElementById('disk').innerText = `${data.disk_usage}%`;
            document.getElementById('strategy').innerText = data.strategy_returns ? `${(data.strategy_returns * 100).toFixed(2)}%` : '0%';
        })
        .catch(error => console.error('Error fetching metrics:', error));
}

// 定时每分钟刷新一次
setInterval(fetchMetrics, 60000);

// 初始化获取
fetchMetrics();

// WebSocket for real-time alerts
const alertSocket = new WebSocket('ws://localhost:5000/socket.io/?EIO=4&transport=websocket');

alertSocket.onopen = function(event) {
    console.log('WebSocket connection established.');
};

alertSocket.onmessage = function(event) {
    // 解析SocketIO消息
    const message = event.data;
    if (message.startsWith('42')) {
        const data = JSON.parse(message.substring(2));
        const eventName = data[0];
        const payload = data[1];
        if (eventName === 'alert') {
            showAlert(payload.subject, payload.body);
        } else if (eventName === 'control_response') {
            console.log(`Control Response: ${payload.status}`);
        }
    }
};

alertSocket.onerror = function(event) {
    console.error('WebSocket error:', event);
};

alertSocket.onclose = function(event) {
    console.log('WebSocket connection closed.');
};

function showAlert(subject, body) {
    // 创建一个简单的警报弹窗
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert-popup';
    alertDiv.innerHTML = `<strong>${subject}</strong><br>${body}`;
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.remove();
    }, 10000); // 10秒后移除
}

// 用户交互处理
document.getElementById('pauseStrategy').addEventListener('click', () => {
    sendControlCommand('pause');
});

document.getElementById('resumeStrategy').addEventListener('click', () => {
    sendControlCommand('resume');
});

document.getElementById('updateRisk').addEventListener('click', () => {
    const newLeverage = document.getElementById('riskParam').value;
    sendControlCommand('update_risk', { 'new_leverage': newLeverage });
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
