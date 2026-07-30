/**
 * FlowAI Dashboard
 * Dashboard charts + live WebSocket updates
 */

(function () {

    let trendChart = null;
    let congestionChart = null;

    const CONGESTION_THRESHOLDS = [
        [5, 'low'],
        [15, 'moderate'],
        [30, 'high']
    ];

    const CONGESTION_COLORS = {
        low: '#34d399',
        moderate: '#facc15',
        high: '#fb923c',
        severe: '#ef4444'
    };


    function congestionLevelFor(avgVehicleCount) {

        for (const [threshold, level] of CONGESTION_THRESHOLDS) {

            if (avgVehicleCount <= threshold) {
                return level;
            }

        }

        return 'severe';
    }


    /* =========================================
       CREATE CHARTS
    ========================================= */

    function createCharts() {

        if (typeof Chart === 'undefined') {
            console.error("Chart.js NOT loaded");
            return;
        }

        const trendEl =
            document.getElementById('trend-chart-data');

        const congestionEl =
            document.getElementById('congestion-chart-data');


        console.log("Trend element:", trendEl);
        console.log("Congestion element:", congestionEl);


        if (!trendEl) {
            console.error("trend-chart-data NOT FOUND");
            return;
        }

        if (!congestionEl) {
            console.error("congestion-chart-data NOT FOUND");
            return;
        }


        try {

            let trendData =
                JSON.parse(trendEl.textContent);

            let congestionData =
                JSON.parse(congestionEl.textContent);


            // Fix double encoded JSON
            if (typeof trendData === 'string') {
                trendData = JSON.parse(trendData);
            }

            if (typeof congestionData === 'string') {
                congestionData =
                    JSON.parse(congestionData);
            }


            console.log(
                "FINAL TREND DATA:",
                trendData
            );

            console.log(
                "FINAL CONGESTION DATA:",
                congestionData
            );


            /* ===============================
               VEHICLE COUNT TREND
            =============================== */

            const trendCanvas =
                document.getElementById('trendChart');


            if (trendCanvas) {

                trendChart =
                    new Chart(
                        trendCanvas.getContext('2d'),
                        {

                            type: 'line',

                            data: {

                                labels:
                                    trendData.labels || [],

                                datasets: [{

                                    label:
                                        'Vehicle Count',

                                    data:
                                        trendData.vehicle_counts || [],

                                    borderColor:
                                        '#22d3ee',

                                    backgroundColor:
                                        'rgba(34,211,238,0.15)',

                                    borderWidth: 3,

                                    pointRadius: 4,

                                    pointHoverRadius: 6,

                                    tension: 0.35,

                                    fill: true

                                }]

                            },

                            options: {

                                responsive: true,

                                maintainAspectRatio: false,

                                interaction: {
                                    intersect: false,
                                    mode: 'index'
                                },

                                plugins: {

                                    legend: {
                                        display: true
                                    }

                                },

                                scales: {

                                    y: {

                                        beginAtZero: true,

                                        ticks: {
                                            precision: 0
                                        }

                                    }

                                }

                            }

                        }
                    );


                console.log(
                    "Vehicle chart CREATED"
                );

            }

            else {

                console.error(
                    "trendChart canvas NOT FOUND"
                );

            }


            /* ===============================
               CONGESTION CHART
            =============================== */

            const congestionCanvas =
                document.getElementById(
                    'congestionChart'
                );


            if (congestionCanvas) {

                const congestionValues =
                    congestionData.vehicle_counts ||
                    congestionData.values ||
                    congestionData.counts ||
                    [];


                let colors = [];

                if (
                    congestionData.levels &&
                    congestionData.levels.length
                ) {

                    colors =
                        congestionData.levels.map(
                            level =>
                                CONGESTION_COLORS[level] ||
                                CONGESTION_COLORS.low
                        );

                }

                else {

                    colors =
                        congestionValues.map(
                            value => {

                                const level =
                                    congestionLevelFor(
                                        Number(value)
                                    );

                                return (
                                    CONGESTION_COLORS[level]
                                );

                            }
                        );

                }


                congestionChart =
                    new Chart(
                        congestionCanvas.getContext('2d'),
                        {

                            type: 'bar',

                            data: {

                                labels:
                                    congestionData.labels || [],

                                datasets: [{

                                    label:
                                        'Vehicle Count',

                                    data:
                                        congestionValues,

                                    backgroundColor:
                                        colors,

                                    borderWidth: 0,

                                    borderRadius: 6

                                }]

                            },

                            options: {

                                responsive: true,

                                maintainAspectRatio: false,

                                plugins: {

                                    legend: {
                                        display: false
                                    }

                                },

                                scales: {

                                    y: {

                                        beginAtZero: true,

                                        ticks: {
                                            precision: 0
                                        }

                                    }

                                }

                            }

                        }
                    );


                console.log(
                    "Congestion chart CREATED"
                );

            }

            else {

                console.error(
                    "congestionChart canvas NOT FOUND"
                );

            }


        }

        catch (error) {

            console.error(
                "CHART ERROR:",
                error
            );

        }

    }



    /* =========================================
       DASHBOARD HELPERS
    ========================================= */

    function setText(id, value) {

        const el =
            document.getElementById(id);

        if (el) {
            el.textContent = value;
        }

    }


    function setStatus(text, iconClass) {

        const socketStatusEl =
            document.getElementById(
                'socket-status'
            );

        if (!socketStatusEl) return;


        socketStatusEl.innerHTML =
            `<i class="fa-solid ${iconClass} me-1"></i> ${text}`;

    }



    /* =========================================
       LIVE DATA
    ========================================= */

    const trackedIntersections =
        new Map();


    function applyMonitoringUpdate(data) {

        trackedIntersections.set(
            data.intersection_id,
            {

                name:
                    data.intersection_name,

                vehicle_count:
                    Number(
                        data.vehicle_count || 0
                    ),

                avg_waiting_time_seconds:
                    Number(
                        data.avg_waiting_time_seconds || 0
                    )

            }
        );


        const values =
            Array.from(
                trackedIntersections.values()
            );


        if (!values.length) return;


        const avgWaitingTime =

            values.reduce(
                (sum, v) =>
                    sum +
                    v.avg_waiting_time_seconds,
                0
            ) / values.length;


        const avgVehicleCount =

            values.reduce(
                (sum, v) =>
                    sum +
                    v.vehicle_count,
                0
            ) / values.length;


        const overallLevel =
            congestionLevelFor(
                avgVehicleCount
            );


        setText(
            'stat-waiting-time',
            avgWaitingTime.toFixed(1)
        );


        const levelEl =
            document.getElementById(
                'stat-congestion-level'
            );


        if (levelEl) {

            levelEl.className =
                `congestion-badge congestion-${overallLevel} fs-6`;

            levelEl.textContent =
                overallLevel
                    .charAt(0)
                    .toUpperCase() +
                overallLevel.slice(1);

        }


        /* UPDATE TREND CHART */

        if (trendChart) {

            const time =
                data.captured_at
                    ? new Date(
                        data.captured_at
                    ).toLocaleTimeString(
                        [],
                        {
                            hour: '2-digit',
                            minute: '2-digit'
                        }
                    )
                    : new Date()
                        .toLocaleTimeString(
                            [],
                            {
                                hour: '2-digit',
                                minute: '2-digit'
                            }
                        );


            trendChart.data.labels.push(
                time
            );


            trendChart
                .data
                .datasets[0]
                .data
                .push(
                    Number(
                        data.vehicle_count || 0
                    )
                );


            if (
                trendChart.data.labels.length >
                20
            ) {

                trendChart
                    .data
                    .labels
                    .shift();

                trendChart
                    .data
                    .datasets[0]
                    .data
                    .shift();

            }


            trendChart.update('none');

        }


        /* UPDATE CONGESTION CHART */

        if (congestionChart) {

            const idx =
                congestionChart
                    .data
                    .labels
                    .indexOf(
                        data.intersection_name
                    );


            if (idx !== -1) {

                const count =
                    Number(
                        data.vehicle_count || 0
                    );


                const level =
                    data.congestion_level ||
                    congestionLevelFor(count);


                congestionChart
                    .data
                    .datasets[0]
                    .data[idx] =
                    count;


                congestionChart
                    .data
                    .datasets[0]
                    .backgroundColor[idx] =
                    CONGESTION_COLORS[level] ||
                    CONGESTION_COLORS.low;


                congestionChart.update(
                    'none'
                );

            }

        }

    }



    /* =========================================
       EMERGENCY ALERT
    ========================================= */

    function showEmergencyAlert(data) {

        const banner =
            document.getElementById(
                'emergency-alert-banner'
            );

        const text =
            document.getElementById(
                'emergency-alert-text'
            );


        if (!banner || !text) return;


        text.textContent =
            `Emergency vehicle (${data.vehicle_type}) detected at ${data.intersection_name}.`;


        banner.classList.remove(
            'd-none'
        );


        setTimeout(
            () =>
                banner.classList.add(
                    'd-none'
                ),
            20000
        );

    }



    /* =========================================
       WEBSOCKET
    ========================================= */

    function startWebSocket() {

        const protocol =
            window.location.protocol ===
            'https:'
                ? 'wss:'
                : 'ws:';


        const socketUrl =
            `${protocol}//${window.location.host}/ws/monitoring/overview/`;


        let reconnectDelay = 1000;

        const MAX_RECONNECT_DELAY =
            15000;


        function connect() {

            let socket;


            try {

                socket =
                    new WebSocket(
                        socketUrl
                    );

            }

            catch (error) {

                console.warn(
                    "WebSocket unavailable:",
                    error
                );

                return;

            }


            socket.onopen = () => {

                console.log(
                    "Dashboard WebSocket connected"
                );

                setStatus(
                    'Live',
                    'fa-circle text-success'
                );

                reconnectDelay = 1000;

            };


            socket.onclose = () => {

                console.warn(
                    "Dashboard WebSocket disconnected"
                );


                setStatus(
                    'Offline',
                    'fa-circle text-secondary'
                );


                setTimeout(
                    connect,
                    reconnectDelay
                );


                reconnectDelay =
                    Math.min(
                        reconnectDelay * 2,
                        MAX_RECONNECT_DELAY
                    );

            };


            socket.onerror = () => {

                console.warn(
                    "Dashboard WebSocket error"
                );

                socket.close();

            };


            socket.onmessage = event => {

                try {

                    const data =
                        JSON.parse(
                            event.data
                        );


                    if (
                        data.type ===
                        'connection.ack'
                    ) {
                        return;
                    }


                    if (
                        data.type ===
                        'monitoring.update'
                    ) {

                        applyMonitoringUpdate(
                            data
                        );

                    }

                    else if (
                        data.type ===
                        'emergency.alert'
                    ) {

                        showEmergencyAlert(
                            data
                        );

                    }

                }

                catch (error) {

                    console.error(
                        "WebSocket message error:",
                        error
                    );

                }

            };

        }


        connect();

    }



    /* =========================================
       START DASHBOARD
    ========================================= */

    document.addEventListener(
        'DOMContentLoaded',
        function () {

            console.log(
                "FlowAI dashboard starting..."
            );

            createCharts();

            // WebSocket failure should NOT
            // prevent charts from loading.
            startWebSocket();

        }
    );


})();