// Kebab menu toggle. One open menu at a time; closes on outside click,
// Escape, or activation of any menu item. HTMX-safe: delegated listeners
// on document.body so re-swapped markup works without re-wiring.
(function () {
  "use strict";

  function closeAll(except) {
    document.querySelectorAll("[data-kebab].is-open").forEach(function (k) {
      if (k === except) return;
      k.classList.remove("is-open");
      var trigger = k.querySelector(".kebab__trigger");
      var menu = k.querySelector(".kebab__menu");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
      if (menu) menu.setAttribute("hidden", "");
    });
  }

  document.body.addEventListener("click", function (e) {
    var target = e.target;
    if (!(target instanceof Element)) return;
    var trigger = target.closest(".kebab__trigger");
    if (trigger) {
      e.preventDefault();
      var kebab = trigger.closest("[data-kebab]");
      if (!kebab) return;
      var isOpen = kebab.classList.contains("is-open");
      closeAll(isOpen ? null : kebab);
      if (isOpen) {
        kebab.classList.remove("is-open");
        trigger.setAttribute("aria-expanded", "false");
        var menu = kebab.querySelector(".kebab__menu");
        if (menu) menu.setAttribute("hidden", "");
      } else {
        kebab.classList.add("is-open");
        trigger.setAttribute("aria-expanded", "true");
        var m = kebab.querySelector(".kebab__menu");
        if (m) m.removeAttribute("hidden");
      }
      return;
    }
    // Click on a menu item inside an open kebab → close after activation.
    var item = target.closest(".kebab__menu button, .kebab__menu a");
    if (item) {
      closeAll(null);
      return;
    }
    // Outside click → close all.
    if (!target.closest("[data-kebab]")) closeAll(null);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeAll(null);
  });
})();
