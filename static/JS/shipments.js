/* ============================================================
   shipments.js
   Search debouncing + auto-submit filters + form loading states
   Used by: customer/shipments, customer/create_shipment,
            driver/deliveries, driver/delivery_details
   ============================================================ */
(function () {
    'use strict';

    /* ============================= HELPERS ============================= */
    function isReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    /* ============================= DEBOUNCED SEARCH ============================= */
    function setupDebouncedSearch() {
        const filterForms = document.querySelectorAll(
            '[data-shipments-filter], [data-driver-deliveries-filter], [data-complaints-filter]'
        );

        filterForms.forEach((form) => {
            const searchInput = form.querySelector('input[type="search"][name="q"]');
            if (!searchInput) return;

            let debounceTimer = null;
            const DELAY = 500;

            searchInput.addEventListener('input', function () {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    // احفظ مكان المؤشر
                    const cursorPos = searchInput.selectionStart;
                    form.submit();

                    // احفظ القيمة في sessionStorage لاستعادة المؤشر بعد reload
                    sessionStorage.setItem('shipments_search_cursor', cursorPos);
                }, DELAY);
            });

            // استعادة المؤشر بعد reload
            if (sessionStorage.getItem('shipments_search_cursor')) {
                const pos = parseInt(sessionStorage.getItem('shipments_search_cursor'), 10);
                sessionStorage.removeItem('shipments_search_cursor');
                if (!isNaN(pos)) {
                    searchInput.focus({ preventScroll: true });
                    searchInput.setSelectionRange(pos, pos);
                }
            }
        });
    }

    /* ============================= AUTO-SUBMIT SELECTS ============================= */
    function setupAutoSubmitSelects() {
        const filterForms = document.querySelectorAll(
            '[data-shipments-filter], [data-driver-deliveries-filter], [data-complaints-filter]'
        );

        filterForms.forEach((form) => {
            // فقط الـselects اللي ليها data-auto-submit أو select بدون data-no-auto
            const selects = form.querySelectorAll(
                'select[name="status"], select[name="method"], ' +
                'select[name="type"], select[name="priority"], ' +
                'select[name="state"]'
            );

            selects.forEach((select) => {
                select.addEventListener('change', function () {
                    form.submit();
                });
            });
        });
    }

    /* ============================= SUBMIT LOADING STATE ============================= */
    function setupSubmitLoading() {
        const submitButtons = document.querySelectorAll(
            '[data-shipment-submit], [data-complaint-submit], ' +
            '[data-availability-submit], [data-location-submit], ' +
            '[data-accept-submit], [data-status-submit]'
        );

        submitButtons.forEach((btn) => {
            const form = btn.closest('form');
            if (!form) return;

            form.addEventListener('submit', function () {
                if (btn.dataset.isSubmitting === 'true') {
                    event.preventDefault();
                    return;
                }

                btn.dataset.isSubmitting = 'true';
                btn.disabled = true;
                btn.classList.add('is-loading');

                const label = btn.querySelector('.btn-label, [data-submit-label]');
                const loadingLabel = btn.dataset.loadingLabel;

                if (label && loadingLabel) {
                    label.dataset.originalLabel = label.textContent.trim();
                    label.textContent = loadingLabel;
                }
            });
        });
    }

    /* ============================= ACCEPT DELIVERY (inline) ============================= */
    function setupAcceptDelivery() {
        const acceptForms = document.querySelectorAll(
            'form[action*="accept_delivery"], form[action*="accept-assignment"]'
        );

        acceptForms.forEach((form) => {
            form.addEventListener('submit', function (e) {
                const btn = form.querySelector('button[type="submit"]');
                if (!btn) return;

                if (!confirm('Accept this delivery assignment?')) {
                    e.preventDefault();
                    return;
                }

                btn.disabled = true;
                btn.classList.add('is-loading');
            });
        });
    }

    /* ============================= STATUS TRANSITION (inline) ============================= */
    function setupStatusTransition() {
        const statusForms = document.querySelectorAll(
            'form[action*="update_delivery_status"], form[action*="update_status"]'
        );

        statusForms.forEach((form) => {
            form.addEventListener('submit', function (e) {
                const statusInput = form.querySelector('input[name="status"]');
                if (!statusInput) return;

                const newStatus = statusInput.value;
                const displayStatus = formatStatus(newStatus);

                if (!confirm('Mark this delivery as "' + displayStatus + '"?')) {
                    e.preventDefault();
                    return;
                }

                const btn = form.querySelector('button[type="submit"]');
                if (btn) {
                    btn.disabled = true;
                    btn.classList.add('is-loading');

                    const label = btn.querySelector('.btn-label');
                    if (label) {
                        label.textContent = 'Updating…';
                    }
                }
            });
        });
    }

    function formatStatus(status) {
        return status
            .toLowerCase()
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (c) => c.toUpperCase());
    }

    /* ============================= FORM VALIDATION HINT ============================= */
    function setupClientValidationHint() {
        const forms = document.querySelectorAll('[data-shipment-form], [data-complaint-form]');
        if (!forms.length) return;

        forms.forEach((form) => {
            const requiredFields = form.querySelectorAll('[required]');

            requiredFields.forEach((field) => {
                field.addEventListener('blur', function () {
                    if (field.value.trim() === '') {
                        field.setAttribute('aria-invalid', 'true');
                    } else {
                        field.removeAttribute('aria-invalid');
                    }
                });
            });
        });
    }

    /* ============================= RESET FILTER ON EMPTY SEARCH ============================= */
    function setupClearSearchOnEscape() {
        const searchInputs = document.querySelectorAll('input[type="search"][name="q"]');

        searchInputs.forEach((input) => {
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Escape' && input.value !== '') {
                    input.value = '';
                    input.form.submit();
                }
            });
        });
    }

    /* ============================= INIT ============================= */
    document.addEventListener('DOMContentLoaded', function () {
        setupDebouncedSearch();
        setupAutoSubmitSelects();
        setupSubmitLoading();
        setupAcceptDelivery();
        setupStatusTransition();
        setupClientValidationHint();
        setupClearSearchOnEscape();
    });
})();