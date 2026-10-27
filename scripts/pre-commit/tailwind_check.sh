#!/usr/bin/env bash
# tailwind_check — pre-commit hook (ADR-0027 §1).
# Rebuilds static/tailwind.css into a temp file and diffs against the
# committed copy. Fails the commit if content/js/config changes have not
# been re-applied to tailwind.css. Non-destructive.
set -euo pipefail

if ! command -v npx >/dev/null 2>&1; then
  echo "tailwind-check: npx not found. Run 'just install' or install Node 20+." >&2
  exit 1
fi

out="src/budget_planner/web/static/tailwind.css"
tmp="$(mktemp -t tailwind-check.XXXXXX.css)"
trap 'rm -f "$tmp"' EXIT

npx --no-install tailwindcss \
  -i src/budget_planner/web/static/tailwind.src.css \
  -o "$tmp" \
  --minify >/dev/null 2>&1

if ! cmp -s "$tmp" "$out"; then
  echo "tailwind-check: $out is stale. Run 'just css' and stage the result." >&2
  exit 1
fi
