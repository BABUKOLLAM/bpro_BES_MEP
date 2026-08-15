/* ME Polymers portal — scroll reveals + sticky nav. Vanilla JS; same
   rationale as bpro_hrms_portal but namespaced separately so the two
   products' assets never entangle. */
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
        if (!document.querySelector(".mep-landing, .mep-login")) {
            return;
        }

        var reducedMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;

        var revealEls = document.querySelectorAll(".mep-reveal");
        if (reducedMotion || !("IntersectionObserver" in window)) {
            revealEls.forEach(function (el) {
                el.classList.add("mep-in");
            });
        } else {
            var observer = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        if (!entry.isIntersecting) {
                            return;
                        }
                        var el = entry.target;
                        var delay = parseInt(el.dataset.delay || "0", 10);
                        setTimeout(function () {
                            el.classList.add("mep-in");
                        }, delay);
                        observer.unobserve(el);
                    });
                },
                { threshold: 0.15 }
            );
            revealEls.forEach(function (el) {
                observer.observe(el);
            });
        }

        var nav = document.getElementById("mepNav");
        if (nav) {
            var syncNav = function () {
                nav.classList.toggle("mep-nav-solid", window.scrollY > 40);
            };
            window.addEventListener("scroll", syncNav, { passive: true });
            syncNav();
        }
    });
})();
