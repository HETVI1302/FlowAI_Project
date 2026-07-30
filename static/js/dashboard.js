document.addEventListener('DOMContentLoaded', function() {
    // Check if we are on the dashboard page by looking for a specific element
    const trafficChartCtx = document.getElementById('trafficChart');
    if (trafficChartCtx) {
        initDashboard();
    }
});

function initDashboard() {
    // Initialize Chart.js
    const ctx = document.getElementById('trafficChart').getContext('2d');
    
    // Mock Data for Traffic Volume
    const trafficData = {
        labels: ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00'],
        datasets: [{
            label: 'Vehicles per hour',
            data: [1200, 1900, 1500, 1100, 1300, 1800, 1600],
            backgroundColor: 'rgba(59, 130, 246, 0.2)',
            borderColor: 'rgba(59, 130, 246, 1)',
            borderWidth: 2,
            tension: 0.4,
            fill: true
        }]
    };

    const config = {
        type: 'line',
        data: trafficData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#f8fafc'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    };

    const trafficChart = new Chart(ctx, config);

    // Simulate Live Updates
    setInterval(() => {
        // Update total vehicles
        const totalVehiclesEl = document.getElementById('val-total-vehicles');
        if (totalVehiclesEl) {
            let current = parseInt(totalVehiclesEl.innerText.replace(/,/g, ''));
            current += Math.floor(Math.random() * 5);
            totalVehiclesEl.innerText = current.toLocaleString();
        }

        // Simulate signal change
        const signalLights = document.querySelectorAll('.light-circle');
        if (signalLights.length > 0) {
            // Very simple random toggle for demo
            if (Math.random() > 0.7) {
                signalLights.forEach(l => l.classList.remove('active'));
                const colors = ['red', 'yellow', 'green'];
                const randomColor = colors[Math.floor(Math.random() * colors.length)];
                document.querySelector(`.light-${randomColor}`).classList.add('active');
            }
        }
    }, 3000);
}
