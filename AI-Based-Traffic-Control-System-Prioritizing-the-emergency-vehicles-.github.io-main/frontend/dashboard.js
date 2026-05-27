/* dashboard.js - Analytics Dashboard Logic */

let vehicleTypeChart, densityChart, emergencyPieChart;
let ws = null;
let updateInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    connectWebSocket();
    startPeriodicRefresh();
});

// Initialize Charts
function initCharts() {
    // Vehicle Type Bar Chart
    const ctx1 = document.getElementById('vehicleTypeChart').getContext('2d');
    vehicleTypeChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: ['Cars', 'Trucks', 'Buses', 'Motorcycles', 'Emergency'],
            datasets: [{
                label: 'Vehicle Count',
                data: [0, 0, 0, 0, 0],
                backgroundColor: 'rgba(0, 255, 136, 0.3)',
                borderColor: '#00ff88',
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { labels: { color: '#c8d8e8' } }
            },
            scales: {
                y: { grid: { color: 'rgba(0, 255, 136, 0.1)' }, ticks: { color: '#c8d8e8' } },
                x: { ticks: { color: '#c8d8e8' } }
            }
        }
    });

    // Density Line Chart
    const ctx2 = document.getElementById('densityChart').getContext('2d');
    densityChart = new Chart(ctx2, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Traffic Density (%)',
                data: [],
                borderColor: '#00aaff',
                backgroundColor: 'rgba(0, 170, 255, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#00aaff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { labels: { color: '#c8d8e8' } }
            },
            scales: {
                y: { min: 0, max: 100, grid: { color: 'rgba(0, 255, 136, 0.1)' }, ticks: { color: '#c8d8e8' } },
                x: { ticks: { color: '#c8d8e8', rotation: 45, maxRotation: 45 } }
            }
        }
    });

    // Emergency Pie Chart
    const ctx3 = document.getElementById('emergencyPieChart').getContext('2d');
    emergencyPieChart = new Chart(ctx3, {
        type: 'pie',
        data: {
            labels: ['North', 'East', 'South', 'West'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: ['#00ff88', '#00aaff', '#ffcc00', '#ff3355'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#c8d8e8' } }
            }
        }
    });
}

// WebSocket Connection
function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8000/api/dashboard/ws/dashboard');
    
    ws.onopen = () => {
        console.log('Dashboard WebSocket connected');
        updateSidebarStatus(true);
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'analytics_update') {
                updateDashboard(data.data);
            }
        } catch (e) {
            console.error('WebSocket parse error:', e);
        }
    };
    
    ws.onclose = () => {
        console.log('Dashboard WebSocket disconnected, reconnecting...');
        updateSidebarStatus(false);
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// Update Sidebar Status
function updateSidebarStatus(online) {
    const statusEl = document.getElementById('sidebarStatus');
    const dotEl = document.querySelector('.status-dot');
    if (statusEl) {
        statusEl.textContent = online ? 'Online' : 'Offline';
        statusEl.style.color = online ? '#00ff88' : '#ff3355';
    }
    if (dotEl) {
        dotEl.style.background = online ? '#00ff88' : '#ff3355';
    }
}

// Periodic Refresh Fallback
function startPeriodicRefresh() {
    // Fetch data every 2 seconds as fallback
    setInterval(() => {
        fetchAnalyticsData();
    }, 2000);
}

// Fetch analytics via HTTP
async function fetchAnalyticsData() {
    try {
        const response = await fetch('http://localhost:8000/api/dashboard/analytics');
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Failed to fetch analytics:', error);
    }
}

// Update Dashboard UI
function updateDashboard(data) {
    // Update stats cards
    document.getElementById('totalVehicles').textContent = data.total_vehicles || 0;
    document.getElementById('emergencyCount').textContent = data.emergency_count || 0;
    document.getElementById('avgWaitTime').innerHTML = `${data.avg_waiting_time || 0}<span class="stat-unit">s</span>`;
    document.getElementById('signalEfficiency').innerHTML = `${data.signal_efficiency || 0}<span class="stat-unit">%</span>`;
    
    // Update last update time
    document.getElementById('lastUpdate').textContent = `Updated: ${data.last_updated || '--'}`;
    
    // Update vehicle type chart
    if (vehicleTypeChart && data.vehicle_types) {
        const types = ['car', 'truck', 'bus', 'motorcycle', 'ambulance'];
        const counts = types.map(t => data.vehicle_types[t] || 0);
        vehicleTypeChart.data.datasets[0].data = counts;
        vehicleTypeChart.update();
    }
    
    // Update density chart
    if (densityChart && data.time_labels && data.density_history) {
        densityChart.data.labels = data.time_labels;
        densityChart.data.datasets[0].data = data.density_history;
        densityChart.update();
    }
    
    // Update emergency pie chart
    if (emergencyPieChart && data.emergency_by_camera) {
        const cameras = ['North', 'East', 'South', 'West'];
        const values = cameras.map(c => data.emergency_by_camera[c] || 0);
        emergencyPieChart.data.datasets[0].data = values;
        emergencyPieChart.update();
    }
    
    // Update heatmap
    if (data.heatmap_data) {
        updateHeatmap(data.heatmap_data);
    }
    
    // Update camera table
    if (data.cameras) {
        updateCameraTable(data.cameras);
    }
    
    // Update emergency logs
    if (data.emergency_logs) {
        updateEmergencyLogs(data.emergency_logs);
        document.getElementById('emergencyLogCount').textContent = data.emergency_logs.length;
    }
    
    // Update recommendations
    if (data.recommendations) {
        updateRecommendations(data.recommendations);
    }
    
    // Update peak hours
    if (data.peak_hours) {
        updatePeakHours(data.peak_hours);
    }
    
    // Update signal stats
    if (data.avg_green_duration !== undefined) {
        document.getElementById('avgGreenDuration').textContent = `${data.avg_green_duration || 0} s`;
        document.getElementById('emergencyOverrides').textContent = data.emergency_overrides || 0;
    }
    
    if (data.busiest_camera) {
        document.getElementById('busiestCamera').textContent = data.busiest_camera.name;
    }
}

// Update Heatmap
function updateHeatmap(heatmapData) {
    const container = document.getElementById('heatmapContainer');
    if (!container) return;
    
    const cameras = ['North', 'East', 'South', 'West'];
    const densities = [heatmapData.North || 0, heatmapData.East || 0, heatmapData.South || 0, heatmapData.West || 0];
    
    container.innerHTML = cameras.map((cam, idx) => `
        <div class="heatmap-item">
            <div class="heatmap-label">${cam}</div>
            <div class="heatmap-bar-container">
                <div class="heatmap-bar" style="height: ${densities[idx]}%; background: ${getDensityColor(densities[idx])};"></div>
            </div>
            <span class="heatmap-value">${Math.round(densities[idx])}%</span>
        </div>
    `).join('');
}

function getDensityColor(density) {
    if (density < 30) return 'linear-gradient(180deg, #00ff88, #00cc66)';
    if (density < 70) return 'linear-gradient(180deg, #ffcc00, #ffaa00)';
    return 'linear-gradient(180deg, #ff3355, #cc0044)';
}

// Update Camera Table
function updateCameraTable(cameras) {
    const tbody = document.getElementById('cameraTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = cameras.map(cam => `
        <tr>
            <td><strong>${cam.name}</strong></td>
            <td>${cam.count}</td>
            <td>${cam.density}%</td>
            <td class="congestion-${cam.congestion.toLowerCase()}">${cam.congestion}</td>
            <td>${cam.waiting_time}s</td>
            <td>${cam.density > 70 ? '⚠️ Congested' : cam.density > 30 ? '📊 Moderate' : '✅ Smooth'}</td>
        </tr>
    `).join('');
}

// Update Emergency Logs
function updateEmergencyLogs(logs) {
    const container = document.getElementById('emergencyLogList');
    if (!container) return;
    
    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="log-placeholder">No emergencies detected</div>';
        return;
    }
    
    container.innerHTML = logs.map(log => `
        <div class="log-entry">
            <div class="log-time">${log.timestamp}</div>
            <div class="log-details">
                <span class="log-camera">📹 ${log.camera}</span> | 
                🚑 ${log.vehicle_type} | 
                ⏱️ ETA: ${log.eta}s | 
                🚦 ${log.signal_priority}
            </div>
        </div>
    `).join('');
}

// Update Recommendations
function updateRecommendations(recommendations) {
    const container = document.getElementById('recommendationsList');
    if (!container) return;
    
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = '<div class="rec-placeholder">Analyzing traffic patterns...</div>';
        return;
    }
    
    container.innerHTML = recommendations.map(rec => `
        <div class="rec-entry">💡 ${rec}</div>
    `).join('');
}

// Update Peak Hours
function updatePeakHours(peakHours) {
    const container = document.getElementById('peakHoursList');
    if (!container) return;
    
    if (!peakHours || peakHours.length === 0) {
        container.innerHTML = '<div class="peak-placeholder">Collecting data...</div>';
        return;
    }
    
    container.innerHTML = peakHours.map(peak => `
        <div class="peak-hour-item">
            <span class="peak-hour">${peak.hour}</span>
            <span class="peak-density">${peak.density} vehicles/min</span>
        </div>
    `).join('');
}

// Export Functions
async function exportCSV() {
    try {
        window.location.href = 'http://localhost:8000/api/dashboard/export/csv';
    } catch (error) {
        console.error('CSV export failed:', error);
        alert('Failed to export CSV. Please try again.');
    }
}

async function exportPDF() {
    try {
        window.location.href = 'http://localhost:8000/api/dashboard/export/pdf';
    } catch (error) {
        console.error('PDF export failed:', error);
        alert('Failed to export PDF. Please try again.');
    }
}

async function refreshData() {
    await fetchAnalyticsData();
}

// Update trends (simple animation)
function updateTrends() {
    const trends = document.querySelectorAll('.stat-trend');
    trends.forEach(trend => {
        trend.style.opacity = '0';
        setTimeout(() => {
            trend.style.opacity = '1';
        }, 100);
    });
}

// Auto-refresh trends every 5 seconds
setInterval(updateTrends, 5000);