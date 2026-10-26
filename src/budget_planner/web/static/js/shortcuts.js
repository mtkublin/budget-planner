// T-068 — Global keyboard shortcuts. Reads `data-shortcut` off nav items so
// the keymap can never drift from the rail partial (ADR-0023).
(() => {
  const CHORD_MS = 1000;
  let pending = null; // { prefix, expiresAt }

  // WHY: typing in a field or already inside a <dialog> should never trigger
  // chords. Esc is the one global we always keep.
  const guarded = () => {
    const a = document.activeElement;
    if (!a) return false;
    if (a.closest("dialog[open]")) return true;
    const tag = a.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || a.isContentEditable;
  };

  const navMap = () => {
    const map = {};
    document.querySelectorAll("nav [data-shortcut]").forEach(el => {
      const key = el.getAttribute("data-shortcut");
      if (key) map[key] = el.getAttribute("href");
    });
    return map;
  };

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const top = Array.from(document.querySelectorAll("dialog[open]")).pop();
      if (top) { e.preventDefault(); top.close(); }
      return;
    }
    if (guarded()) return;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      window.openCommandPalette?.();
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    const now = Date.now();
    if (pending && now > pending.expiresAt) pending = null;

    if (pending && pending.prefix === "g") {
      const chord = `g ${e.key.toLowerCase()}`;
      pending = null;
      const href = navMap()[chord];
      if (href) { e.preventDefault(); window.location.assign(href); }
      return;
    }
    if (e.key === "g") { pending = { prefix: "g", expiresAt: now + CHORD_MS }; return; }
    if (e.key === "n") { e.preventDefault(); window.openCommandPalette?.(); return; }
    if (e.key === "/") {
      const target = document.querySelector("[data-search-input]");
      if (target) { e.preventDefault(); target.focus(); }
      return;
    }
    if (e.key === "?") {
      const dlg = document.getElementById("shortcuts-dialog");
      if (dlg) { e.preventDefault(); dlg.showModal(); }
    }
  });
})();
