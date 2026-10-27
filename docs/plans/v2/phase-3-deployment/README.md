# Phase 3 — Deployment pipeline

GitHub Actions deploys cosign-signed images to the Scaleway VM via SSH to a tightly-caged `deploy` user (ADR-0037).

- [T-D30](T-D30-build-workflow.md) — Build workflow (image + cosign).
- [T-D31](T-D31-deploy-workflow.md) — Deploy workflow (detailed here).
- T-D32 — Deploy user command restriction + script. See `../tasks.md`.
- T-D33 — Deliberate-break rollback test.
- T-D34 — Manual rollback workflow.
