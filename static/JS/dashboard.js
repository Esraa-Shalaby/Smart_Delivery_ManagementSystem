/* ============================================================
   dashboard.js
   Shared interactions for all dashboard pages
   ============================================================ */
(function () {
    'use strict';

    /* ============================= LOADING STATE ============================= */
    function setupLoadingState() {
        // أي form فيه زر [data-*-submit] أو زر [data-loading-label]
        const forms = document.querySelectorAll('form');

        forms.forEach((form) => {
            form.addEventListener('submit', function (e) {
                const submitBtn = form.querySelector(
                    '[data-shipment-submit], [data-complaint-submit], ' +
                    '[data-profile-submit], [data-availability-submit], ' +
                    '[data-location-submit], [data-auth-submit], ' +
                    '[data-loading-label]'
                );

                if (!submitBtn) return;

                if (submitBtn.dataset.isSubmitting === 'true') {
                    e.preventDefault();
                    return;
                }

                submitBtn.dataset.isSubmitting = 'true';
                submitBtn.classList.add('is-loading');
                submitBtn.disabled = true;

                const loadingLabel = submitBtn.dataset.loadingLabel;
                const labelEl = submitBtn.querySelector('.btn-label, .auth-submit-label, [data-submit-label]');

                if (loadingLabel && labelEl) {
                    labelEl.dataset.originalLabel = labelEl.textContent.trim();
                    labelEl.textContent = loadingLabel;
                }
            });
        });
    }

    /* ============================= GEOLOCATION DETECT ============================= */
    function setupGeolocationDetect() {
        const buttons = document.querySelectorAll('[data-location-detect]');

        buttons.forEach((btn) => {
            btn.addEventListener('click', function () {
                if (!navigator.geolocation) {
                    alert('Geolocation is not supported by your browser.');
                    return;
                }

                btn.classList.add('is-loading');
                btn.disabled = true;

                const originalLabel = btn.querySelector('.btn-label');
                if (originalLabel) {
                    originalLabel.dataset.originalLabel = originalLabel.textContent;
                    originalLabel.textContent = 'Detecting…';
                }

                navigator.geolocation.getCurrentPosition(
                    function (position) {
                        const latFieldId = btn.dataset.latField;
                        const lngFieldId = btn.dataset.lngField;

                        if (latFieldId) {
                            const latField = document.getElementById(latFieldId);
                            if (latField) latField.value = position.coords.latitude.toFixed(6);
                        }
                        if (lngFieldId) {
                            const lngField = document.getElementById(lngFieldId);
                            if (lngField) lngField.value = position.coords.longitude.toFixed(6);
                        }

                        btn.classList.remove('is-loading');
                        btn.disabled = false;
                        if (originalLabel) {
                            originalLabel.textContent = originalLabel.dataset.originalLabel || 'Detect my location';
                        }
                    },
                    function (error) {
                        let message = 'Unable to detect your location.';
                        if (error.code === error.PERMISSION_DENIED) {
                            message = 'Location permission was denied. Please enable it in your browser settings.';
                        } else if (error.code === error.POSITION_UNAVAILABLE) {
                            message = 'Location information is unavailable.';
                        } else if (error.code === error.TIMEOUT) {
                            message = 'Location request timed out. Please try again.';
                        }
                        alert(message);

                        btn.classList.remove('is-loading');
                        btn.disabled = false;
                        if (originalLabel) {
                            originalLabel.textContent = originalLabel.dataset.originalLabel || 'Detect my location';
                        }
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0,
                    }
                );
            });
        });
    }

    /* ============================= AUTO-RESIZE TEXTAREA ============================= */
    function setupAutoResizeTextarea() {
        const textareas = document.querySelectorAll('textarea[data-auto-resize], .app-chatbot-textarea');

        textareas.forEach((ta) => {
            const resize = () => {
                ta.style.height = 'auto';
                ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
            };

            ta.addEventListener('input', resize);
            resize();
        });
    }

    /* ============================= MODAL HANDLING ============================= */
    function setupModals() {
        // فتح modal عبر [data-open-modal="<id>"]
        document.querySelectorAll('[data-open-modal]').forEach((trigger) => {
            trigger.addEventListener('click', function () {
                const modalId = trigger.dataset.openModal;
                const modal = document.getElementById(modalId);
                if (!modal) return;

                modal.hidden = false;
                modal.setAttribute('aria-hidden', 'false');
                document.body.style.overflow = 'hidden';

                // focus على أول عنصر قابل للتركيز
                const focusable = modal.querySelector('button, [href], input, select, textarea');
                if (focusable) focusable.focus();
            });
        });

        // إغلاق modal
        document.querySelectorAll('[data-action="close-modal"]').forEach((btn) => {
            btn.addEventListener('click', function () {
                const modal = btn.closest('.modal-backdrop');
                if (!modal) return;

                modal.hidden = true;
                modal.setAttribute('aria-hidden', 'true');
                document.body.style.overflow = '';
            });
        });

        // إغلاق عند الضغط على backdrop
        document.querySelectorAll('.modal-backdrop').forEach((modal) => {
            modal.addEventListener('click', function (e) {
                if (e.target === modal) {
                    modal.hidden = true;
                    modal.setAttribute('aria-hidden', 'true');
                    document.body.style.overflow = '';
                }
            });
        });

        // Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal-backdrop:not([hidden])').forEach((modal) => {
                    modal.hidden = true;
                    modal.setAttribute('aria-hidden', 'true');
                    document.body.style.overflow = '';
                });
            }
        });
    }

    /* ============================= STATUS BADGE COLORING ============================= */
    // (لا حاجة — يتم ذلك عبر CSS classes)

    /* ============================= NUMBER COUNTER ============================= */
    function setupNumberCounter() {
        const counters = document.querySelectorAll('[data-counter]');

        counters.forEach((el) => {
            const target = parseFloat(el.dataset.counter) || 0;
            if (target === 0) return;

            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            if (prefersReducedMotion) return;

            const duration = 800;
            const start = performance.now();

            const tick = (now) => {
                const elapsed = now - start;
                const progress = Math.min(elapsed / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const value = Math.floor(target * eased);
                el.textContent = value;

                if (progress < 1) {
                    requestAnimationFrame(tick);
                } else {
                    el.textContent = target;
                }
            };

            requestAnimationFrame(tick);
        });
    }

    /* ============================= TRACKER REVEAL ============================= */
    function setupTrackerReveal() {
        const trackers = document.querySelectorAll('[data-tracker]');

        trackers.forEach((tracker) => {
            tracker.classList.add('tracker-reveal');
        });
    }

    /* ============================= TABS ============================= */
    function setupTabs() {
        document.querySelectorAll('[data-tabs]').forEach((group) => {
            const tabs = group.querySelectorAll('[data-tab]');
            const container = group.closest('.mgr-card') || document;
            const panels = container.querySelectorAll('[data-tab-panel]');

            tabs.forEach((tab) => {
                tab.addEventListener('click', function () {
                    const target = tab.dataset.tab;

                    tabs.forEach((t) => t.classList.remove('is-active'));
                    tab.classList.add('is-active');

                    panels.forEach((panel) => {
                        if (panel.dataset.tabPanel === target) {
                            panel.hidden = false;
                        } else {
                            panel.hidden = true;
                        }
                    });
                });
            });
        });
    }

    /* ============================= INIT ============================= */
    document.addEventListener('DOMContentLoaded', function () {
        setupLoadingState();
        setupGeolocationDetect();
        setupAutoResizeTextarea();
        setupModals();
        setupNumberCounter();
        setupTrackerReveal();
        setupTabs();
    });
})();