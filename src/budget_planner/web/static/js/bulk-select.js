// T-R69 — Bulk-select behaviour for Ledger · Actual and · Planned.
// Delegated listeners on document.body survive HTMX swaps. Toolbar is a
// `[data-bulk-toolbar]` element rendered by `templates/ledger/index.html`.
// Deletes iterate the per-row endpoints (atomic bulk-delete + undo-token
// backend work is a separate task — see docs/plans/v2/tasks.md T-R69).

(function () {
  "use strict";

  function toolbar() { return document.querySelector("[data-bulk-toolbar]"); }
  function allRowCheckboxes() { return document.querySelectorAll("[data-bulk-row]"); }
  function selectedCheckboxes() {
    return Array.from(allRowCheckboxes()).filter(function (c) { return c.checked; });
  }
  function selectedIds() { return selectedCheckboxes().map(function (c) { return c.value; }); }

  function refresh() {
    var bar = toolbar();
    if (!bar) return;
    var ids = selectedIds();
    var count = ids.length;
    var countEl = bar.querySelector("[data-bulk-count]");
    if (countEl) countEl.textContent = String(count);
    if (count > 0) bar.removeAttribute("hidden");
    else bar.setAttribute("hidden", "");
    var all = document.querySelector("[data-bulk-all]");
    if (all) {
      var total = allRowCheckboxes().length;
      all.indeterminate = count > 0 && count < total;
      all.checked = count > 0 && count === total;
    }
  }

  document.body.addEventListener("change", function (e) {
    var t = e.target;
    if (!(t instanceof HTMLInputElement)) return;
    if (t.matches("[data-bulk-row]")) {
      refresh();
    } else if (t.matches("[data-bulk-all]")) {
      allRowCheckboxes().forEach(function (c) { c.checked = t.checked; });
      refresh();
    }
  });

  document.body.addEventListener("click", function (e) {
    var t = e.target;
    if (!(t instanceof Element)) return;
    var clear = t.closest("[data-bulk-clear]");
    if (clear) {
      allRowCheckboxes().forEach(function (c) { c.checked = false; });
      refresh();
      return;
    }
    var del = t.closest("[data-bulk-delete]");
    if (del) {
      var ids = selectedIds();
      if (ids.length === 0) return;
      if (!confirm("Delete " + ids.length + " selected row" + (ids.length === 1 ? "" : "s") + "?")) return;
      var bar = toolbar();
      var view = bar && bar.getAttribute("data-view");
      var base = view === "planned" ? "/planned/" : "/transactions/";
      Promise.all(ids.map(function (id) {
        return fetch(base + id + "/delete", { method: "POST", headers: { "HX-Request": "true" } });
      })).then(function () {
        // Fire the shared stale events so the table re-fetches.
        document.body.dispatchEvent(new Event("ledger-stale"));
        document.body.dispatchEvent(new Event("balance-stale"));
        document.body.dispatchEvent(new Event("forecast-stale"));
        refresh();
      });
      return;
    }
    var exp = t.closest("[data-bulk-export]");
    if (exp) {
      // Export respects the current filter (hitting the existing GET endpoint
      // through the <a> href). Per-row selection constraint is a follow-up
      // (needs backend row_ids[] filter — see T-R69 handoff).
      return;
    }
  });

  // Refresh after any HTMX swap re-renders the table.
  document.body.addEventListener("htmx:afterSwap", refresh);
  // Initial state on page load.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", refresh);
  } else {
    refresh();
  }
})();
