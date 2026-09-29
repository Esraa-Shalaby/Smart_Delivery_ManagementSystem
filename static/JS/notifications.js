/* ============================================================
   notifications.js
   Mark as read + badge update
   ============================================================ */
(function () {
    'use strict';

    /* ============================= MARK AS READ ============================= */
    const items = document.querySelectorAll('[data-notification-id]');

    items.forEach((item) => {
        const form = item.querySelector('form[action*="mark_read"]');
        if (!form) return;

        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
            const submitBtn = form.querySelector('button[type="submit"]');

            if (submitBtn) submitBtn.disabled = true;

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                    },
                });

                if (response.ok) {
                    item.classList.remove('is-unread');
                    item.dataset.notificationState = 'read';

                    // إخفاء زر Mark as read
                    const markBtn = form.querySelector('button');
                    if (markBtn) markBtn.closest('.notif-center-actions')?.querySelector('form')?.remove();

                    // تقليل badge
                    const badge = document.querySelector('.title-badge');
                    if (badge) {
                        const current = parseInt(badge.textContent.trim(), 10) || 0;
                        const next = Math.max(0, current - 1);

                        if (next === 0) {
                            badge.remove();
                        } else {
                            badge.textContent = next;
                            badge.setAttribute(
                                'aria-label',
                                next + ' unread notifications'
                            );
                        }
                    }

                    // تحديث badge في الـnavbar / sidebar
                    updateGlobalBadge(-1);

                } else {
                    if (submitBtn) submitBtn.disabled = false;
                    alert('Unable to mark as read. Please try again.');
                }
            } catch (err) {
                if (submitBtn) submitBtn.disabled = false;
                alert('Connection error. Please try again.');
            }
        });
    });

    /* ============================= MARK ALL AS READ ============================= */
    const markAllForms = document.querySelectorAll('form[action*="mark_all_read"]');

    markAllForms.forEach((form) => {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('is-loading');
            }

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                });

                if (response.ok) {
                    // تحديث كل العناصر
                    document.querySelectorAll('[data-notification-id].is-unread').forEach((item) => {
                        item.classList.remove('is-unread');
                        item.dataset.notificationState = 'read';

                        // إزالة زر Mark as read
                        item.querySelectorAll('form[action*="mark_read"]').forEach((f) => f.remove());

                        // إزالة unread pill
                        const pill = item.querySelector('.notif-center-unread-pill');
                        if (pill) pill.remove();
                    });

                    // إزالة title badge
                    const badge = document.querySelector('.title-badge');
                    if (badge) badge.remove();

                    // إزالة زر Mark all
                    form.remove();

                    // تحديث badge في الـnavbar / sidebar
                    updateGlobalBadge(0, true);

                } else {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove('is-loading');
                    }
                    alert('Unable to mark all as read. Please try again.');
                }
            } catch (err) {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('is-loading');
                }
                alert('Connection error. Please try again.');
            }
        });
    });

    /* ============================= GLOBAL BADGE UPDATE ============================= */
    function updateGlobalBadge(delta, reset) {
        // navbar badge
        const navBadge = document.querySelector('.app-notify-badge');
        // sidebar badge
        const sidebarBadge = document.querySelector('.app-sidebar-badge');

        [navBadge, sidebarBadge].forEach((badge) => {
            if (!badge) return;

            if (reset) {
                badge.remove();
                return;
            }

            const current = parseInt(badge.textContent.trim(), 10) || 0;
            const next = Math.max(0, current + delta);

            if (next === 0) {
                badge.remove();
            } else {
                badge.textContent = next;
            }
        });
    }

    /* ============================= AUTO MARK ON OPEN ============================= */
    // عند الضغط على "Open" لإشعار unread، نرسل mark_read أولاً
    document.querySelectorAll('[data-notification-id].is-unread a[href]').forEach((link) => {
        link.addEventListener('click', function (e) {
            const item = link.closest('[data-notification-id]');
            if (!item) return;

            const form = item.querySelector('form[action*="mark_read"]');
            if (!form) return;

            // نرسل mark_read في الخلفية بدون انتظار
            const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
            fetch(form.action, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                keepalive: true,
            }).catch(() => { });
        });
    });
})();