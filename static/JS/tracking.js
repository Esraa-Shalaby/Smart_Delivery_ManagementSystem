/* ============================================================
   tracking.js
   Auto-refresh shipment tracking
   ============================================================ */
(function () {
    'use strict';

    const tracker = document.querySelector('[data-tracker]');
    if (!tracker) return;

    const endpoint = tracker.dataset.trackerEndpoint || null;
    if (!endpoint) return;

    const REFRESH_INTERVAL = 30000; // 30 ثانية
    let timer = null;

    async function refresh() {
        if (document.hidden) return;

        try {
            const response = await fetch(endpoint, {
                headers: { 'Accept': 'application/json' },
            });
            if (!response.ok) return;

            const data = await response.json();
            updateUI(data);
        } catch (err) {
            // فشل صامت — لا نزعج المستخدم
        }
    }

    function updateUI(data) {
        if (!data || !data.status) return;

        const currentStatus = data.status.toLowerCase();

        // تحديث tracker
        tracker.dataset.current = currentStatus;
        tracker.querySelectorAll('.tracking-progress-step').forEach((step, idx) => {
            step.classList.remove('is-current', 'is-done');
        });

        const steps = tracker.querySelectorAll('.tracking-progress-step');
        const order = ['created', 'assigned', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered'];
        const currentIdx = order.indexOf(currentStatus);

        steps.forEach((step, idx) => {
            if (idx < currentIdx) step.classList.add('is-done');
            else if (idx === currentIdx) step.classList.add('is-current', 'is-done');
        });

        // تحديث status badge
        const badge = document.querySelector('[data-status-badge]');
        if (badge && data.status_display) {
            badge.textContent = data.status_display;
            badge.className = 'status-badge status-' + currentStatus;
        }
    }

    function start() {
        timer = setInterval(refresh, REFRESH_INTERVAL);
    }

    function stop() {
        if (timer) {
            clearInterval(timer);
            timer = null;
        }
    }

    document.addEventListener('visibilitychange', function () {
        if (document.hidden) stop();
        else { refresh(); start(); }
    });

    
    setTimeout(start, 5000);
})();