# Phase 7 — Cleanup

> Lands **one release after** v2 is cut as green on main. Retires v1 302 shims, deletes the FAB, removes `#drawer-root`, prunes dead CSS.
>
> This phase is explicitly deferred until the v2 release has lived in production for one release with no bookmarked-URL complaints.

Entry: v2 shipped on main; one additional release passed with no 302-hit complaints.

Exit: v1 route handlers deleted; FAB code deleted; `#drawer-root` removed; `tasks.md` carries a `✅ v2 shipped` line.

Tasks: T-R57..T-R60.

- T-R57 Retire v1 → v2 302 redirects
- T-R58 Delete FAB template + CSS + JS
- T-R59 Retire `#drawer-root` from base shell
- T-R60 Dead-CSS prune + close v2

ADR references: 0051 §2 (302 shim removal), 0026 (FAB amended by 0056 §8).
