// Rising Dough — frontend helpers.
// (1) `?` opens the cheatsheet dialog.
// (2) `g <key>` navigation shortcuts.
// (3) `[` / `]` cycle segmented tabs.
(function () {
  "use strict";
  var pending = null;
  var pendingTs = 0;
  var editableSelector = "input,textarea,select,[contenteditable=true],[contenteditable='']";

  function openCheatsheet() {
    var d = document.getElementById("rd-cheatsheet");
    if (d && typeof d.showModal === "function") d.showModal();
  }

  function focusedEditable() {
    var el = document.activeElement;
    return el && el.matches && el.matches(editableSelector);
  }

  document.addEventListener("keydown", function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (focusedEditable()) return;
    var k = e.key;

    if (k === "?") { e.preventDefault(); openCheatsheet(); return; }
    if (k === "Escape") {
      var d = document.getElementById("rd-cheatsheet");
      if (d && d.open) { d.close(); }
      return;
    }
    if (k === "n") {
      var add = document.querySelector("[data-rd-add]");
      if (add) { e.preventDefault(); add.click(); }
      return;
    }
    if (k === "/") {
      var search = document.querySelector("[data-rd-search]");
      if (search) { e.preventDefault(); search.focus(); }
      return;
    }
    if (k === "[" || k === "]") {
      var tabs = Array.from(document.querySelectorAll(".rd-segmented__item"));
      if (!tabs.length) return;
      var idx = tabs.findIndex(function (t) { return t.getAttribute("aria-selected") === "true" || t.classList.contains("rd-segmented__item--active"); });
      if (idx === -1) return;
      var next = tabs[(idx + (k === "]" ? 1 : -1) + tabs.length) % tabs.length];
      if (next) { e.preventDefault(); next.click(); }
      return;
    }
    if (k === "g") {
      pending = "g";
      pendingTs = Date.now();
      return;
    }
    if (pending === "g" && Date.now() - pendingTs < 1200) {
      var target = { o: "/today", l: "/ledger", p: "/plan", a: "/accounts", s: "/settings" }[k];
      pending = null;
      if (target) { e.preventDefault(); window.location.href = target; }
      return;
    }
    pending = null;
  });
})();
