/* ============================================================
   main.js
   Navbar dropdown + alerts + general UI
   ============================================================ */
(function () {
    'use strict';

    /* ============================= USER DROPDOWN ============================= */
    function setupUserDropdown() {
        const trigger = document.querySelector('[data-dropdown-trigger]');
        const menu = document.querySelector('[data-dropdown-menu]');

        if (!trigger || !menu) return;

        function toggle() {
            const isOpen = !menu.hidden;
            menu.hidden = isOpen;
            trigger.setAttribute('aria-expanded', String(!isOpen));
        }

        function close() {
            menu.hidden = true;
            trigger.setAttribute('aria-expanded', 'false');
        }

        trigger.addEventListener('click', function (e) {
            e.stopPropagation();
            toggle();
        });

        document.addEventListener('click', function (e) {
            if (!menu.hidden && !menu.contains(e.target) && !trigger.contains(e.target)) {
                close();
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !menu.hidden) {
                close();
                trigger.focus();
            }
        });
    }

    /* ============================= ALERTS ============================= */
    function setupAlerts() {
        const alerts = document.querySelectorAll('[data-alert]');

        alerts.forEach((alert) => {
            // Close button
            const closeBtn = alert.querySelector('[data-alert-close]');
            if (closeBtn) {
                closeBtn.addEventListener('click', function () {
                    closeAlert(alert);
                });
            }

            // Auto dismiss (اختياري)
            const autoDismiss = alert.dataset.autoDismiss;
            if (autoDismiss) {
                const delay = parseInt(autoDismiss, 10) || 5000;
                setTimeout(() => closeAlert(alert), delay);
            }
        });

        function closeAlert(alert) {
            alert.classList.add('is-closing');
            setTimeout(() => {
                alert.remove();
                const container = document.querySelector('[data-alerts-root]');
                if (container && container.querySelectorAll('[data-alert]').length === 0) {
                    container.remove();
                }
            }, 300);
        }
    }

    /* ============================= MOBILE MENU (TOPBAR) ============================= */
    function setupMobileMenu() {
        const trigger = document.querySelector('[data-mobile-menu-trigger]');
        const menu = document.querySelector('[data-mobile-menu]');

        if (!trigger || !menu) return;

        trigger.addEventListener('click', function () {
            const isOpen = !menu.hidden;
            menu.hidden = isOpen;
            trigger.setAttribute('aria-expanded', String(!isOpen));
        });
    }

    /* ============================= SMOOTH SCROLL ============================= */
    function setupSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach((link) => {
            link.addEventListener('click', function (e) {
                const href = link.getAttribute('href');
                if (href === '#' || href.length < 2) return;

                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    /* ============================= INIT ============================= */
    document.addEventListener('DOMContentLoaded', function () {
        setupUserDropdown();
        setupAlerts();
        setupMobileMenu();
        setupSmoothScroll();
    });
})();