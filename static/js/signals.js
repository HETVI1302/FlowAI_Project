/**
 * Connects to ws/signals/overview/ and updates the Signal Management control
 * panel (templates/signals_app/control.html) live — mirrors the
 * reconnect-with-backoff pattern in static/js/monitoring.js.
 */
(function () {
    const socketStatusEl = document.getElementById('signals-socket-status');
    if (!document.querySelector('[data-signal-id]')) return; // not on the control panel page

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socketUrl = `${protocol}//${window.location.host}/ws/signals/overview/`;

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
            if (data.type === 'signal.update') applySignalUpdate(data);
        };
    }

    function applySignalUpdate(data) {
        const card = document.querySelector(`[data-signal-id="${data.signal_id}"]`);
        if (!card) return;

        card.querySelector('[data-role="green-time"]').textContent = `${data.green_time}s`;
        card.querySelector('[data-role="yellow-time"]').textContent = `${data.yellow_time}s`;
        card.querySelector('[data-role="red-time"]').textContent = `${data.red_time}s`;

        const modeEl = card.querySelector('[data-role="mode-pill"]');
        if (modeEl) {
            modeEl.className = `signal-mode-pill signal-mode-${data.mode}`;
            modeEl.textContent = data.mode.replace('_', ' ');
        }

        const total = data.green_time + data.yellow_time + data.red_time;
        const bar = card.querySelector('[data-role="timing-bar"]');
        if (bar && total > 0) {
            bar.querySelector('.green').style.width = `${(data.green_time / total) * 100}%`;
            bar.querySelector('.yellow').style.width = `${(data.yellow_time / total) * 100}%`;
            bar.querySelector('.red').style.width = `${(data.red_time / total) * 100}%`;
        }

        const reasonEl = card.querySelector('[data-role="last-reason"]');
        if (reasonEl) reasonEl.textContent = data.reason.replace(/_/g, ' ');

        card.classList.remove('just-updated');
        void card.offsetWidth; // restart the flash animation on repeat updates
        card.classList.add('just-updated');
    }

    connect();
})();
