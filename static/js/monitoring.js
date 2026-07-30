/**
 * Connects to the monitoring Channels consumers and updates the DOM live.
 * Works on two pages:
 *   - monitoring/live.html  -> ws/monitoring/overview/   (updates every card)
 *   - monitoring/detail.html -> ws/monitoring/<id>/       (updates the stat tiles)
 * Auto-detects which page it's on and reconnects with backoff on drop.
 */
(function () {
    const socketStatusEl = document.getElementById('socket-status');
    const isDetailPage = document.body.contains(document.getElementById('stat-vehicle-count'));

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let socketUrl = `${protocol}//${window.location.host}/ws/monitoring/overview/`;

    if (isDetailPage) {
        const wrapper = document.querySelector('.container[data-intersection-id]');
        const intersectionId = wrapper ? wrapper.dataset.intersectionId : null;
        if (intersectionId) {
            socketUrl = `${protocol}//${window.location.host}/ws/monitoring/${intersectionId}/`;
        }
    }

    let reconnectDelay = 1000;
    const MAX_RECONNECT_DELAY = 15000;

    function setStatus(text, iconClass) {
        if (!socketStatusEl) return;
        socketStatusEl.innerHTML = `<i class="fa-solid ${iconClass} me-1"></i> ${text}`;
    }

    function connect() {
        const socket = new WebSocket(socketUrl);

        socket.onopen = () => {
            setStatus('Live', 'fa-circle text-success');
            reconnectDelay = 1000;
        };

        socket.onclose = () => {
            setStatus('Reconnecting…', 'fa-triangle-exclamation');
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
        };

        socket.onerror = () => socket.close();

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'connection.ack') return;

            if (data.type === 'monitoring.update') {
                isDetailPage ? applyDetailUpdate(data) : applyGridUpdate(data);
            } else if (data.type === 'emergency.alert') {
                showEmergencyAlert(data);
            }
        };
    }

    function applyGridUpdate(data) {
        const card = document.querySelector(`[data-intersection-id="${data.intersection_id}"]`);
        if (!card) return;

        card.querySelector('[data-role="vehicle-count"]').textContent = data.vehicle_count;
        card.querySelector('[data-role="queue-length"]').textContent = data.queue_length_meters;
        card.querySelector('[data-role="waiting-time"]').textContent = data.avg_waiting_time_seconds;

        const badge = card.querySelector('[data-role="congestion-badge"]');
        if (badge) {
            badge.className = `congestion-badge congestion-${data.congestion_level}`;
            badge.textContent = data.congestion_level.charAt(0).toUpperCase() + data.congestion_level.slice(1);
        }

        const updated = card.querySelector('[data-role="last-updated"]');
        if (updated) updated.textContent = 'just now';
    }

    function applyDetailUpdate(data) {
        setText('stat-vehicle-count', data.vehicle_count);
        setText('stat-queue-length', data.queue_length_meters);
        setText('stat-waiting-time', data.avg_waiting_time_seconds);

        const levelEl = document.getElementById('stat-congestion-level');
        if (levelEl) {
            levelEl.className = `congestion-badge congestion-${data.congestion_level} fs-6`;
            levelEl.textContent = data.congestion_level.charAt(0).toUpperCase() + data.congestion_level.slice(1);
        }
    }

    function showEmergencyAlert(data) {
        const banner = document.getElementById('emergency-alert-banner');
        const text = document.getElementById('emergency-alert-text');
        if (!banner || !text) return;
        text.textContent = `Emergency vehicle (${data.vehicle_type}) detected at ${data.intersection_name}.`;
        banner.classList.remove('d-none');
        setTimeout(() => banner.classList.add('d-none'), 20000);
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    connect();
})();
