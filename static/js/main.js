/* LuzKids site-wide polish: scroll-reveal animations */
(function () {
  "use strict";
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var els = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window)) {
    els.forEach(function (el) { el.classList.add("visible"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("visible"); io.unobserve(e.target); }
    });
  }, { threshold: 0.12 });
  els.forEach(function (el) { io.observe(el); });

  /* subtle scroll parallax on the hero's star layers — each drifts at
     a different rate as you scroll past, layered on top of their
     existing twinkle animation (which only animates opacity, so it
     doesn't fight this transform). .firefly is deliberately excluded:
     its own "drift" keyframes already animate transform directly. */
  var hero = document.querySelector(".hero");
  if (hero) {
    var layers = [
      { el: hero.querySelector(".stars"),  rate: .08 },
      { el: hero.querySelector(".stars2"), rate: .05 },
      { el: hero.querySelector(".stars3"), rate: .03 },
    ].filter(function (l) { return l.el; });
    var ticking = false;
    function applyParallax() {
      ticking = false;
      var rect = hero.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) return;
      layers.forEach(function (l) {
        l.el.style.transform = "translateY(" + (rect.top * -l.rate) + "px)";
      });
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(applyParallax); }
    }, { passive: true });
    applyParallax();
  }
})();
