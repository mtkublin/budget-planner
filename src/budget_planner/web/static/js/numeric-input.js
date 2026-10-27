// Shared primitive — ADR-0030 §2.
// Restrict `<input data-numeric>` to digits + optional decimal separator
// (comma or dot) with up to two fractional digits. Server-side validation
// remains the source of truth; this is UX sugar for the common case.
(function () {
  "use strict";
  var RE = /^\d*([.,]\d{0,2})?$/;

  function projected(el, inserted) {
    var start = el.selectionStart == null ? el.value.length : el.selectionStart;
    var end = el.selectionEnd == null ? el.value.length : el.selectionEnd;
    return el.value.slice(0, start) + inserted + el.value.slice(end);
  }

  function matches(el) {
    return el && el.matches && el.matches("input[data-numeric]");
  }

  document.body.addEventListener("beforeinput", function (e) {
    if (!matches(e.target)) return;
    var t = e.inputType || "";
    if (t.indexOf("delete") === 0) return;
    var next = projected(e.target, e.data == null ? "" : e.data);
    if (!RE.test(next)) e.preventDefault();
  });

  document.body.addEventListener("paste", function (e) {
    if (!matches(e.target)) return;
    var cd = e.clipboardData || window.clipboardData;
    if (!cd) return;
    var pasted = cd.getData("text") || "";
    var next = projected(e.target, pasted);
    if (!RE.test(next)) e.preventDefault();
  });
})();
