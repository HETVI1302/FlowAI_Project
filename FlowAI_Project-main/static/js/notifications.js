/**
 * Loaded from base.html for every authenticated page (not just the
 * notification center) so the nav bell badge and live toasts work no
 * matter where the operator currently is in the app. Same reconnect
 * pattern as static/js/monitoring.js and static/js/signals.js.
 */
(function () {
    const badge = document.getElementById('notif-badge');

    function ensureToastStack() {
        let stack = document.getElementById('flowai-toast-stack');
        if (!stack) {
            stack = document.createElement('div');
            stack.id = 'flowai-toast-stack';
            document.body.appendChild(stack);
        }
        return stack;
    }

    function setBadge(count) {
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : String(count);
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    }

    function showToast(data) {
        const stack = ensureToastStack();
        const toast = document.createElement('div');
        toast.className = `glass-card p-3 notif-toast notif-priority-${data.priority}`;
        toast.innerHTML = `
            <div class="d-flex justify-content-between align-items-start gap-2">
                <div>
                    <span class="notif-priority notif-priority-${data.priority}">${data.priority}</span>
                    <div class="fw-semibold mt-1">${escapeHtml(data.title)}</div>
                    <div class="small text-muted">${escapeHtml(data.message)}</div>
                </div>
                <button type="button" class="btn-close btn-close-white btn-sm" aria-label="Dismiss"></button>
            </div>`;
        toast.querySelector('.btn-close').addEventListener('click', () => toast.remove());
        stack.prepend(toast);
        setTimeout(() => toast.remove(), 12000);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function fetchInitialUnreadCount() {
        if (!window.FLOWAI_NOTIF_UNREAD_URL) return;
        fetch(window.FLOWAI_NOTIF_UNREAD_URL, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then((res) => res.json())
            .then((data) => setBadge(data.unread_count))
            .catch(() => {});
    }

    let reconnectDelay = 1000;
    const MAX_RECONNECT_DELAY = 15000;

    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const socket = new WebSocket(`${protocol}//${window.location.host}/ws/notifications/`);

        socket.onopen = () => { reconnectDelay = 1000; };
        socket.onclose = () => {
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
        };
        socket.onerror = () => socket.close();

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'connection.ack') return;
            if (data.type === 'notification.new') {
                setBadge(data.unread_count);
                showToast(data);
            }
        };
    }

    fetchInitialUnreadCount();
    connect();
})();
