/* ============================================================
   sidebar.js
   Sidebar collapse / expand + mobile drawer
   ============================================================ */
(function () {
    'use strict';

    const STORAGE_KEY = 'app-sidebar-collapsed';

    function setupDesktopCollapse() {
        const sidebar = document.querySelector('[data-sidebar]');
        const toggle = document.querySelector('[data-sidebar-collapse]');
        const main = document.querySelector('.app-main');

        if (!sidebar || !toggle) return;

        // استعادة الحالة المحفوظة
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved === 'true') {
            sidebar.classList.add('is-collapsed');
            if (main) main.classList.add('is-collapsed');
            toggle.setAttribute('aria-expanded', 'false');
        }

        toggle.addEventListener('click', function () {
            const isCollapsed = sidebar.classList.toggle('is-collapsed');
            if (main) main.classList.toggle('is-collapsed', isCollapsed);
            toggle.setAttribute('aria-expanded', String(!isCollapsed));
            localStorage.setItem(STORAGE_KEY, String(isCollapsed));
        });
    }

    function setupMobileDrawer() {
        const sidebar = document.querySelector('[data-sidebar]');
        const openBtn = document.querySelector('[data-sidebar-open]') ||
            document.querySelector('[data-mobile-menu-trigger]');
        const closeBtn = document.querySelector('[data-sidebar-close]');
        const overlay = document.querySelector('[data-sidebar-overlay]');

        if (!sidebar) return;

        function open() {
            sidebar.classList.add('is-open');
            if (overlay) overlay.hidden = false;
            document.body.style.overflow = 'hidden';
            sidebar.setAttribute('aria-hidden', 'false');

            // focus على أول رابط
            const firstLink = sidebar.querySelector('a, button');
            if (firstLink) firstLink.focus({ preventScroll: true });
        }

        function close() {
            sidebar.classList.remove('is-open');
            if (overlay) overlay.hidden = true;
            document.body.style.overflow = '';
            sidebar.setAttribute('aria-hidden', 'true');
        }

        if (openBtn) openBtn.addEventListener('click', open);
        if (closeBtn) closeBtn.addEventListener('click', close);
        if (overlay) overlay.addEventListener('click', close);

        // Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
                close();
            }
        });

        // إغلاق عند تكبير الشاشة
        window.addEventListener('resize', function () {
            if (window.innerWidth > 1024 && sidebar.classList.contains('is-open')) {
                close();
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        setupDesktopCollapse();
        setupMobileDrawer();
    });
})();