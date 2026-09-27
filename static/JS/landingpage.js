 
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        initMobileNav();
        initNavScrollState();
        initStaggeredReveal();
        initTrackingFormStub();
    });

    function initMobileNav() {
        var nav = document.querySelector("[data-sd-nav]");
        var toggle = document.querySelector("[data-sd-burger]");
        if (!nav || !toggle) return;

        toggle.addEventListener("click", function () {
            var isOpen = nav.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        nav.querySelectorAll("[data-sd-mobile-link]").forEach(function (link) {
            link.addEventListener("click", function () {
                nav.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    function initNavScrollState() {
        var nav = document.querySelector("[data-sd-nav]");
        if (!nav) return;
        var onScroll = function () {
            nav.classList.toggle("is-scrolled", window.scrollY > 12);
        };
        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
    }

    function initStaggeredReveal() {
        var items = document.querySelectorAll("[data-sd-reveal]");
        if (!items.length) return;

        if (!("IntersectionObserver" in window)) {
            items.forEach(function (el) { el.classList.add("sd-reveal"); });
            return;
        }

        var observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;
                    var el = entry.target;
                    var group = el.closest("[data-sd-reveal-group]");
                    var siblings = group
                        ? Array.prototype.slice.call(group.querySelectorAll("[data-sd-reveal]"))
                        : [el];
                    var index = siblings.indexOf(el);
                    el.style.animationDelay = Math.max(index, 0) * 90 + "ms";
                    el.classList.add("sd-reveal");
                    observer.unobserve(el);
                });
            },
            { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
        );

        items.forEach(function (el) { observer.observe(el); });
    }

    function initTrackingFormStub() {
        var form = document.querySelector("[data-sd-track-form]");
        if (!form) return;
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            // Backend tracking lookup is not implemented yet — UI only, per project scope.
            var input = form.querySelector("input[name='tracking_number']");
            if (input) input.focus();
        });
    }
})();