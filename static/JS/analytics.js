/* ============================================================
   analytics.js
   Number counter + tab switching for analytics page
   ============================================================ */
(function () {
    'use strict';

    /* ============================= NUMBER COUNTER ============================= */
    function setupCounters() {
        const counters = document.querySelectorAll('[data-counter]');

        counters.forEach((el) => {
            const target = parseFloat(el.dataset.counter) || 0;
            const rawText = el.textContent.trim();

            // إذا كانت القيمة نصية (مثل "2.4 days")، لا نحرّكها
            if (isNaN(target) || target === 0) return;

            const prefersReducedMotion = window.matchMedia(
                '(prefers-reduced-motion: reduce)'
            ).matches;
            if (prefersReducedMotion) return;

            // استخدام IntersectionObserver لبدء العدّ عند الظهور
            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            animateCounter(el, target);
                            observer.unobserve(el);
                        }
                    });
                },
                { threshold: 0.3 }
            );

            observer.observe(el);
        });
    }

    function animateCounter(el, target) {
        const duration = 900;
        const startTime = performance.now();
        const isFloat = String(target).includes('.');

        function tick(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = target * eased;

            el.textContent = isFloat
                ? value.toFixed(1)
                : Math.floor(value).toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                el.textContent = isFloat
                    ? target.toFixed(1)
                    : target.toLocaleString();
            }
        }

        requestAnimationFrame(tick);
    }

    /* ============================= TIME-BASED TABS ============================= */
    function setupTimeTabs() {
        const groups = document.querySelectorAll('[data-tabs]');

        groups.forEach((group) => {
            const tabs = group.querySelectorAll('[data-tab]');
            const card = group.closest('.mgr-card') || document;
            const panels = card.querySelectorAll('[data-tab-panel]');

            tabs.forEach((tab) => {
                tab.addEventListener('click', function () {
                    const target = tab.dataset.tab;

                    tabs.forEach((t) => {
                        t.classList.remove('is-active');
                        t.setAttribute('aria-selected', 'false');
                    });
                    tab.classList.add('is-active');
                    tab.setAttribute('aria-selected', 'true');

                    panels.forEach((panel) => {
                        if (panel.dataset.tabPanel === target) {
                            panel.hidden = false;
                        } else {
                            panel.hidden = true;
                        }
                    });

                    // إعادة تحريك الأشرطة بعد ظهورها
                    reanimateBars(panels);
                });
            });
        });
    }

    /* ============================= REANIMATE BARS ============================= */
    function reanimateBars(panels) {
        panels.forEach((panel) => {
            if (panel.hidden) return;

            const bars = panel.querySelectorAll('.mini-bar');
            bars.forEach((bar, i) => {
                // إعادة تعيين animation
                bar.style.animation = 'none';
                bar.offsetHeight; // force reflow
                bar.style.animation = '';

                // تطبيق ارتفاع مؤقت لبدء animation
                bar.style.setProperty('--delay', (i * 30) + 'ms');
            });
        });
    }

    /* ============================= BAR CHART REVEAL ============================= */
    function setupBarReveal() {
        const bars = document.querySelectorAll('.bar-fill[style*="--bar-width"]');
        if (!bars.length) return;

        const prefersReducedMotion = window.matchMedia(
            '(prefers-reduced-motion: reduce)'
        ).matches;
        if (prefersReducedMotion) return;

        // إخفاء أولي
        bars.forEach((bar) => {
            bar.dataset.originalWidth = bar.style.getPropertyValue('--bar-width').trim();
            bar.style.setProperty('--bar-width', '0%');
        });

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        const bar = entry.target;
                        setTimeout(() => {
                            bar.style.setProperty('--bar-width', bar.dataset.originalWidth);
                        }, 100);
                        observer.unobserve(bar);
                    }
                });
            },
            { threshold: 0.2 }
        );

        bars.forEach((bar) => observer.observe(bar));
    }

    /* ============================= INIT ============================= */
    document.addEventListener('DOMContentLoaded', function () {
        setupCounters();
        setupTimeTabs();
        setupBarReveal();
    });
})();