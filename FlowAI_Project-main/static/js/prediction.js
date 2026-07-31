/**
 * Connects to ws/prediction/overview/ and updates the Predictions page
 * (templates/prediction/forecast.html) live — same reconnect-with-backoff
 * shape as monitoring.js / signals.js.
 */
(function () {
    if (!document.getElementById('prediction-grid')) return; // not on this page

    const socketStatusEl = document.getElementById('prediction-socket-status');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socketUrl = `${protocol}//${window.location.host}/ws/prediction/overview/`;

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
            if (data.type === 'forecast.update') applyForecastUpdate(data);
            else if (data.type === 'incident.alert') prependIncident(data);
        };
    }

    function applyForecastUpdate(data) {
        const card = document.querySelector(`[data-intersection-id="${data.intersection_id}"]`);
        if (!card) return;

        const list = card.querySelector('[data-role="forecast-list"]');
        if (!list) return;
        list.innerHTML = data.forecasts.map((f) => {
            const when = new Date(f.predicted_for).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const pct = Math.round(f.confidence * 100);
            return `
                <div class="forecast-row">
                    <span class="text-muted small">${when}</span>
                    <span class="congestion-badge congestion-${f.predicted_level}">${f.predicted_level}</span>
                    <div class="d-flex align-items-center gap-2">
                        <div class="confidence-bar"><div class="confidence-bar-fill" style="width:${pct}%"></div></div>
                        <span class="text-muted" style="font-size:0.7rem;">${pct}%</span>
                    </div>
                </div>`;
        }).join('');

        const updated = card.querySelector('[data-role="last-generated"]');
        if (updated) updated.textContent = 'just now';
    }

    function prependIncident(data) {
        const container = document.getElementById('open-incidents-list');
        if (!container) return;

        const empty = container.querySelector('[data-role="empty-state"]');
        if (empty) empty.remove();

        const row = document.createElement('div');
        row.className = 'incident-row new-incident d-flex justify-content-between align-items-center p-3';
        row.style.borderBottom = '1px solid rgba(148,163,184,0.1)';
        row.innerHTML = `
            <div>
                <span class="incident-severity incident-severity-${data.severity}">${data.severity}</span>
                <span class="fw-semibold ms-2">${escapeHtml(data.intersection_name)}</span>
                <div class="text-muted small">Confidence ${Math.round(data.confidence * 100)}% &middot; just now</div>
            </div>`;
        container.prepend(row);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    connect();
})();
