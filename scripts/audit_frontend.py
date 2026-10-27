"""Frontend visual-audit runner (ADR-0027 / .claude/skills/frontend-visual-audit).

Drives Chromium via Playwright over the four top-level nav routes at three
viewports; records screenshots + diagnostic JSON + an aggregate summary.
Pure dev utility; never imported by the web app.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import ConsoleMessage, Page, sync_playwright

BASE = os.environ.get("AUDIT_BASE", "http://127.0.0.1:8000")
OUT = Path(os.environ.get("AUDIT_OUT") or Path(tempfile.gettempdir()) / "fe-audit")
ROUTES = ["/", "/ledger", "/accounts", "/budget"]
VIEWPORTS = [
    {"label": "desktop", "width": 1440, "height": 900},
    {"label": "tablet", "width": 1024, "height": 768},
    {"label": "mobile", "width": 375, "height": 812},
]

DIAGNOSTIC_JS = """
() => {
  const q = sel => Array.from(document.querySelectorAll(sel));
  const overflowing = q('body *')
    .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
    .slice(0, 20)
    .map(el => ({
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      cls: typeof el.className === 'string' ? el.className : null,
      right: Math.round(el.getBoundingClientRect().right),
    }));
  const seen = new Map();
  q('[id]').forEach(e => seen.set(e.id, (seen.get(e.id) || 0) + 1));
  const duplicateIds = Array.from(seen.entries())
    .filter(([, n]) => n > 1)
    .map(([id, count]) => ({ id, count }));
  return {
    viewport: [window.innerWidth, window.innerHeight],
    docScroll: [
      document.documentElement.scrollWidth,
      document.documentElement.scrollHeight,
    ],
    horizontalScroll: document.documentElement.scrollWidth > window.innerWidth,
    verticalScroll: document.documentElement.scrollHeight > window.innerHeight,
    overflowingElements: overflowing,
    duplicateIds,
    images: {
      total: document.images.length,
      broken: Array.from(document.images).filter(
        i => !i.complete || i.naturalWidth === 0,
      ).length,
    },
  };
}
"""


def audit_route(
    page: Page,
    *,
    route: str,
    viewport: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    console_errors: list[str] = []
    request_failures: list[dict[str, Any]] = []
    page.on(
        "console",
        lambda m: console_errors.append(m.text) if m.type == "error" else None,
    )
    page.on(
        "pageerror",
        lambda e: console_errors.append(f"pageerror: {e!s}"),
    )
    page.on(
        "requestfailed",
        lambda r: request_failures.append(
            {"url": r.url, "reason": (r.failure or "")},
        ),
    )
    url = f"{BASE}{route}"
    slug = f"{viewport['label']}__{route.replace('/', '_') or 'root'}"
    try:
        page.goto(url, wait_until="networkidle", timeout=15000)
    except Exception as exc:
        return {"route": route, "viewport": viewport["label"], "error": str(exc)}
    page.wait_for_timeout(400)
    diag = page.evaluate(DIAGNOSTIC_JS)
    shot = out_dir / f"{slug}.png"
    page.screenshot(path=str(shot), full_page=True)
    (out_dir / f"{slug}.json").write_text(
        json.dumps(
            {
                "route": route,
                "url": url,
                "viewport": viewport,
                "diag": diag,
                "consoleErrors": console_errors,
                "requestFailures": request_failures,
            },
            indent=2,
        ),
    )
    return {
        "route": route,
        "viewport": viewport["label"],
        "horizontalScroll": diag["horizontalScroll"],
        "overflowingCount": len(diag["overflowingElements"]),
        "duplicateIds": len(diag["duplicateIds"]),
        "brokenImages": diag["images"]["broken"],
        "consoleErrors": len(console_errors),
        "requestFailures": len(request_failures),
        "screenshot": str(shot),
    }


def _handle_console(store: list[str]) -> Any:
    def _inner(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            store.append(msg.text)

    return _inner


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vp in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
            )
            for route in ROUTES:
                page = context.new_page()
                row = audit_route(page, route=route, viewport=vp, out_dir=OUT)
                summary.append(row)
                print(
                    f"{vp['label']:7} {route:12} "
                    f"overflow={row.get('horizontalScroll', '?')} "
                    f"err={row.get('consoleErrors', '?')}",
                )
                page.close()
            context.close()
        browser.close()
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    bad = [
        r
        for r in summary
        if any(
            [
                r.get("horizontalScroll"),
                r.get("overflowingCount", 0) > 0,
                r.get("duplicateIds", 0) > 0,
                r.get("consoleErrors", 0) > 0,
                r.get("requestFailures", 0) > 0,
                r.get("brokenImages", 0) > 0,
                "error" in r,
            ],
        )
    ]
    print(f"\n{len(summary)} audits, {len(bad)} with signals.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
