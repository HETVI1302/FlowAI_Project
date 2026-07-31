/**
 * Renders the two Chart.js charts on the Analytics dashboard from the
 * server-computed JSON (analytics/views.py). No WebSocket here — unlike
 * the live monitoring/dashboard/prediction pages, analytics rollups only
 * change every few minutes (see run_analytics_rollup), so a plain
 * server-rendered page that refreshes on period-switch is enough.
 */
(function () {
    if (typeof Chart === 'undefined') return;

    const volumeDataEl = document.getElementById('volume-chart-data');
    const emissionsDataEl = document.getElementById('emissions-chart-data');
    const volumeData = volumeDataEl ? JSON.parse(volumeDataEl.textContent) : { labels: [], vehicle_counts: [] };
    const emissionsData = emissionsDataEl ? JSON.parse(emissionsDataEl.textContent) : { labels: [], carbon_kg: [] };

    const volumeCanvas = document.getElementById('volumeChart');
    if (volumeCanvas) {
        new Chart(volumeCanvas, {
            type: 'bar',
            data: {
                labels: volumeData.labels,
                datasets: [{
                    label: 'Vehicles',
                    data: volumeData.vehicle_counts,
                    backgroundColor: 'rgba(34, 211, 238, 0.55)',
                    borderRadius: 6,
                }],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#cbd5e1' }, grid: { display: false } },
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true },
                },
            },
        });
    }

    const emissionsCanvas = document.getElementById('emissionsChart');
    if (emissionsCanvas) {
        new Chart(emissionsCanvas, {
            type: 'line',
            data: {
                labels: emissionsData.labels,
                datasets: [{
                    label: 'CO2 (kg)',
                    data: emissionsData.carbon_kg,
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52, 211, 153, 0.12)',
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#cbd5e1' }, grid: { display: false } },
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true },
                },
            },
        });
    }
})();
