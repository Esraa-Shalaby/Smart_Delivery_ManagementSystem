/* ============================================================
   landingpage.js
   SmartDelivery — Landing Page interactions

   Features:
   - Mobile navigation toggle
   - Nav scroll state
   - Staggered reveal on scroll
   - Smooth anchor scrolling
   - Tracking form stub (UI only)
   ============================================================ */
(function () {
    'use strict';

    /* ============================= INIT ============================= */
    document.addEventListener('DOMContentLoaded', function () {
        initMobileNav();
        initNavScrollState();
        initStaggeredReveal();
        initSmoothScroll();
        initTrackingFormStub();
    });

    /* ============================= MOBILE NAV ============================= */
    function initMobileNav() {
        var nav = document.querySelector('[data-sd-nav]');
        var toggle = document.querySelector('[data-sd-burger]');
        if (!nav || !toggle) return;

        toggle.addEventListener('click', function () {
            var isOpen = nav.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        nav.querySelectorAll('[data-sd-mobile-link]').forEach(function (link) {
            link.addEventListener('click', function () {
                nav.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
            });
        });

        // Escape key closes mobile menu
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && nav.classList.contains('is-open')) {
                nav.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /* ============================= NAV SCROLL STATE ============================= */
    function initNavScrollState() {
        var nav = document.querySelector('[data-sd-nav]');
        if (!nav) return;

        var onScroll = function () {
            if (window.scrollY > 12) {
                nav.classList.add('is-scrolled');
            } else {
                nav.classList.remove('is-scrolled');
            }
        };

        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll(); // run once on load
    }

    /* ============================= STAGGERED REVEAL ============================= */
    function initStaggeredReveal() {
        var items = document.querySelectorAll('[data-sd-reveal]');
        if (!items.length) return;

        // Fallback: no IntersectionObserver → just reveal everything
        if (!('IntersectionObserver' in window)) {
            items.forEach(function (el) { el.classList.add('sd-reveal'); });
            return;
        }

        var observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;

                    var el = entry.target;
                    var group = el.closest('[data-sd-reveal-group]');
                    var siblings = group
                        ? Array.prototype.slice.call(
                            group.querySelectorAll('[data-sd-reveal]')
                        )
                        : [el];

                    var index = siblings.indexOf(el);
                    el.style.animationDelay = Math.max(index, 0) * 90 + 'ms';
                    el.classList.add('sd-reveal');
                    observer.unobserve(el);
                });
            },
            { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
        );

        items.forEach(function (el) { observer.observe(el); });
    }

    /* ============================= SMOOTH ANCHOR SCROLL ============================= */
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
            anchor.addEventListener('click', function (e) {
                var target = anchor.getAttribute('href');
                if (!target || target === '#' || target.length < 2) return;

                var el = document.querySelector(target);
                if (!el) return;

                e.preventDefault();
                var top = el.getBoundingClientRect().top +
                    window.pageYOffset -
                    90; // offset for sticky nav
                window.scrollTo({ top: top, behavior: 'smooth' });
            });
        });
    }

    /* ============================= TRACKING FORM STUB ============================= */
    function initTrackingFormStub() {
        var form = document.querySelector('[data-sd-track-form]');
        if (!form) return;

        form.addEventListener('submit', function (event) {
            event.preventDefault();

            // Backend tracking lookup is not implemented yet — UI only.
            // This keeps the input focused so the user notices the form is a preview.
            var input = form.querySelector('input[name="tracking_number"]');
            if (input) input.focus();
        });
    }
})();