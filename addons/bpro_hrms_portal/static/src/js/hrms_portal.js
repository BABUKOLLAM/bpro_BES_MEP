/* bpro HRMS portal — scroll reveals, stat counters, sticky nav.
   Vanilla JS on purpose: the landing/login pages are public frontend
   pages and should not pull the OWL runtime graph in for ~100 lines. */
(function () {
    "use strict";

    function onReady(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    onReady(function () {
        var landing = document.querySelector(".bpro-landing, .bpro-login");
        if (!landing) {
            return;
        }

        var reducedMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;

        // ---- scroll reveal ----
        var revealEls = document.querySelectorAll(".bpro-reveal");
        if (reducedMotion || !("IntersectionObserver" in window)) {
            revealEls.forEach(function (el) {
                el.classList.add("bpro-in");
            });
        } else {
            var revealObserver = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        if (!entry.isIntersecting) {
                            return;
                        }
                        var el = entry.target;
                        var delay = parseInt(el.dataset.delay || "0", 10);
                        setTimeout(function () {
                            el.classList.add("bpro-in");
                        }, delay);
                        revealObserver.unobserve(el);
                    });
                },
                { threshold: 0.15 }
            );
            revealEls.forEach(function (el) {
                revealObserver.observe(el);
            });
        }

        // ---- stat counters ----
        var counters = document.querySelectorAll(".bpro-count");
        function runCounter(el) {
            var target = parseInt(el.dataset.target || "0", 10);
            if (reducedMotion) {
                el.textContent = String(target);
                return;
            }
            var duration = 1400;
            var start = null;
            function step(ts) {
                if (start === null) {
                    start = ts;
                }
                var progress = Math.min((ts - start) / duration, 1);
                // easeOutCubic
                var eased = 1 - Math.pow(1 - progress, 3);
                el.textContent = String(Math.round(target * eased));
                if (progress < 1) {
                    requestAnimationFrame(step);
                }
            }
            requestAnimationFrame(step);
        }
        if (counters.length) {
            if (!("IntersectionObserver" in window)) {
                counters.forEach(runCounter);
            } else {
                var counterObserver = new IntersectionObserver(
                    function (entries) {
                        entries.forEach(function (entry) {
                            if (entry.isIntersecting) {
                                runCounter(entry.target);
                                counterObserver.unobserve(entry.target);
                            }
                        });
                    },
                    { threshold: 0.6 }
                );
                counters.forEach(function (el) {
                    counterObserver.observe(el);
                });
            }
        }

        // ---- sticky nav state ----
        var nav = document.getElementById("bproNav");
        if (nav) {
            var syncNav = function () {
                nav.classList.toggle("bpro-nav-solid", window.scrollY > 40);
            };
            window.addEventListener("scroll", syncNav, { passive: true });
            syncNav();
        }
    });
})();
