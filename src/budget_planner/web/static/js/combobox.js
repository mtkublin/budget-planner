// Shared primitive — ADR-0030 §3.
// Filterable combobox over an inline-rendered option list. WAI-ARIA 1.2
// "combobox with list autocomplete + manual selection" pattern. No XHR
// per keystroke — the full option set is in the DOM.
//
// Markup contract:
//   <div class="combobox" data-combobox>
//     <input class="combobox__input" role="combobox" aria-expanded="false"
//            aria-controls="…list-id…" aria-autocomplete="list"
//            autocomplete="off" data-combobox-input [data-initial-label]>
//     <input type="hidden" name="…" value="" data-combobox-value>
//     <ul class="combobox__list" id="…list-id…" role="listbox" hidden>
//       <li class="combobox__option" role="option"
//           data-value="…" data-label="…">…label…</li>
//     </ul>
//   </div>
(function () {
  "use strict";

  function init(root) {
    if (root.dataset.cbReady === "1") return;
    root.dataset.cbReady = "1";

    var input = root.querySelector("[data-combobox-input]");
    var hidden = root.querySelector("[data-combobox-value]");
    var list = root.querySelector("[role='listbox']");
    if (!input || !hidden || !list) return;
    var options = Array.prototype.slice.call(list.querySelectorAll("[role='option']"));

    // Hydrate the visible input from the hidden value's matching label, so
    // edit forms render the current selection on first paint.
    var seeded = hidden.value;
    if (seeded) {
      var match = options.find(function (o) { return o.dataset.value === seeded; });
      if (match) input.value = match.dataset.label || match.textContent.trim();
    } else if (input.dataset.initialLabel) {
      input.value = input.dataset.initialLabel;
    }

    function openList() {
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }
    function closeList() {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      clearActive();
    }
    function clearActive() {
      options.forEach(function (o) { o.classList.remove("combobox__option--active"); });
      input.removeAttribute("aria-activedescendant");
    }
    function activeIndex() {
      for (var i = 0; i < options.length; i++) {
        if (options[i].classList.contains("combobox__option--active")) return i;
      }
      return -1;
    }
    function setActive(i) {
      clearActive();
      var visible = options.filter(function (o) { return !o.hidden; });
      if (!visible.length) return;
      if (i < 0) i = visible.length - 1;
      if (i >= visible.length) i = 0;
      var target = visible[i];
      target.classList.add("combobox__option--active");
      if (target.id) input.setAttribute("aria-activedescendant", target.id);
      // Keep highlight in view.
      if (typeof target.scrollIntoView === "function") {
        target.scrollIntoView({ block: "nearest" });
      }
    }
    function filter(term) {
      var needle = (term || "").toLowerCase();
      var anyVisible = false;
      options.forEach(function (o) {
        var label = (o.dataset.label || o.textContent).toLowerCase();
        var hit = !needle || label.indexOf(needle) !== -1;
        o.hidden = !hit;
        if (hit) anyVisible = true;
      });
      list.dataset.empty = anyVisible ? "0" : "1";
    }
    function commit(option) {
      hidden.value = option.dataset.value;
      input.value = option.dataset.label || option.textContent.trim();
      filter("");
      closeList();
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
    function clearSelection() {
      hidden.value = "";
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    input.addEventListener("focus", function () {
      filter(input.value);
      openList();
    });
    input.addEventListener("input", function () {
      // Any manual edit invalidates the stored id until the user re-picks.
      if (hidden.value) clearSelection();
      filter(input.value);
      openList();
    });
    input.addEventListener("keydown", function (e) {
      var visible = options.filter(function (o) { return !o.hidden; });
      if (e.key === "ArrowDown") {
        e.preventDefault();
        openList();
        setActive(activeVisibleIndex() + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        openList();
        setActive(activeVisibleIndex() - 1);
      } else if (e.key === "Enter") {
        if (!list.hidden) {
          var idx = activeVisibleIndex();
          var pick = idx === -1 ? visible[0] : visible[idx];
          if (pick) {
            e.preventDefault();
            commit(pick);
          }
        }
      } else if (e.key === "Escape") {
        if (!list.hidden) {
          e.preventDefault();
          closeList();
        }
      } else if (e.key === "Tab") {
        closeList();
      }
    });
    function activeVisibleIndex() {
      var visible = options.filter(function (o) { return !o.hidden; });
      for (var i = 0; i < visible.length; i++) {
        if (visible[i].classList.contains("combobox__option--active")) return i;
      }
      return -1;
    }
    list.addEventListener("mousedown", function (e) {
      var li = e.target.closest("[role='option']");
      if (!li) return;
      e.preventDefault();
      commit(li);
    });
    document.addEventListener("mousedown", function (e) {
      if (!root.contains(e.target)) closeList();
    });
  }

  function initAll(context) {
    var scope = context || document;
    var roots = scope.querySelectorAll("[data-combobox]");
    roots.forEach(init);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { initAll(); });
  } else {
    initAll();
  }
  // Re-run after htmx swap so forms injected into slide-overs wire up.
  document.body.addEventListener("htmx:afterSwap", function (e) {
    initAll(e.target || document);
  });
})();
