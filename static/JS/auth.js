/* ============================================================
   auth.js
   Login / Register / Forgot Password interactions
   ============================================================ */
(function () {
    'use strict';

    /* ============================= PASSWORD VISIBILITY TOGGLE ============================= */
    function setupPasswordToggle() {
        const toggles = document.querySelectorAll('[data-password-toggle]');

        toggles.forEach((toggle) => {
            toggle.addEventListener('click', function () {
                // البحث عن الحقل داخل نفس الـwrap
                const wrap = toggle.closest('.auth-input-wrap');
                if (!wrap) return;

                const input = wrap.querySelector('[data-password-input]');
                if (!input) return;

                const isVisible = input.type === 'text';
                input.type = isVisible ? 'password' : 'text';

                toggle.classList.toggle('is-visible', !isVisible);
                toggle.setAttribute('aria-pressed', String(!isVisible));
                toggle.setAttribute(
                    'aria-label',
                    !isVisible ? 'Hide password' : 'Show password'
                );
            });

            // Keyboard support (Space / Enter)
            toggle.addEventListener('keydown', function (e) {
                if (e.key === ' ' || e.key === 'Enter') {
                    e.preventDefault();
                    toggle.click();
                }
            });
        });
    }

    /* ============================= PASSWORD STRENGTH ============================= */
    function calculateStrength(password) {
        let score = 0;
        if (!password) return { score: 0, level: 'empty', label: '' };

        if (password.length >= 8) score++;
        if (password.length >= 12) score++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
        if (/\d/.test(password)) score++;
        if (/[^A-Za-z0-9]/.test(password)) score++;

        let level = 'weak';
        let label = 'Weak';

        if (score <= 1) {
            level = 'weak';
            label = 'Weak password';
        } else if (score === 2) {
            level = 'fair';
            label = 'Fair password';
        } else if (score === 3 || score === 4) {
            level = 'good';
            label = 'Good password';
        } else if (score >= 5) {
            level = 'strong';
            label = 'Strong password';
        }

        return { score, level, label };
    }

    function setupPasswordStrength() {
        const sources = document.querySelectorAll('[data-password-strength-source]');

        sources.forEach((input) => {
            const form = input.closest('form');
            if (!form) return;

            const strengthWrap = form.querySelector('[data-password-strength]');
            const fill = form.querySelector('[data-password-strength-fill]');
            const label = form.querySelector('[data-password-strength-label]');

            if (!strengthWrap || !fill || !label) return;

            input.addEventListener('input', function () {
                const password = input.value;

                if (!password) {
                    strengthWrap.hidden = true;
                    strengthWrap.setAttribute('aria-hidden', 'true');
                    return;
                }

                strengthWrap.hidden = false;
                strengthWrap.setAttribute('aria-hidden', 'false');

                const result = calculateStrength(password);

                fill.className = 'auth-strength-fill is-' + result.level;
                label.textContent = result.label;
            });
        });
    }

    /* ============================= FOCUS MANAGEMENT ============================= */
    function setupFocusManagement() {
        // focus على أول حقل عند تحميل الصفحة
        const firstInput = document.querySelector(
            '.auth-form input:not([type="hidden"]):not([disabled])'
        );

        if (firstInput && !firstInput.value) {
            // تأجيل بسيط لتفادي مشاكل الـautofill
            setTimeout(() => {
                firstInput.focus({ preventScroll: true });
            }, 100);
        }
    }

    /* ============================= INIT ============================= */
    document.addEventListener('DOMContentLoaded', function () {
        setupPasswordToggle();
        setupPasswordStrength();
        setupFocusManagement();
    });
})();