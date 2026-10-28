# Rising Dough v3 — Remote Deployment Work Plan

> v3 scope: take the single-user local app (v1 functional surface + v2 Rising Dough redesign) and put it on the public internet, hosted on **Scaleway Stardust Warsaw** + **Scaleway Object Storage Warsaw** (ADR-0032), with continuous Litestream replication (ADR-0034), WebAuthn auth (ADR-0033), auto-TLS via Caddy (ADR-0036), Terraform-managed infrastructure (ADR-0035), and a GitHub Actions deploy pipeline (ADR-0037).
>
> **Non-goals**: multi-user, scalability, autoscaling, CSV import, mobile apps.
>
> **Numbering note**: this plan was authored as "v2" on 2026-10-27. The slot was renamed to v3 on 2026-10-28 when the Rising Dough redesign was promoted into v2. Scope, ADRs, and task IDs are unchanged; only the version label moved.

---

## Contents

- [`implementation_plan.md`](implementation_plan.md) — phased delivery with acceptance gates.
- [`tasks.md`](tasks.md) — flat task index (T-D01…T-D46), referenced from the phase docs.
- [`phase-1-prerequisites/`](phase-1-prerequisites/) — individual task files for app-side prerequisites.
- [`phase-2-infrastructure/`](phase-2-infrastructure/) — Terraform + cloud-init bootstrap tasks.
- [`phase-3-deployment/`](phase-3-deployment/) — GitHub Actions pipeline tasks.
- [`phase-4-validation/`](phase-4-validation/) — smoke, backup drill, security scan, runbooks.
- [`runbooks/`](runbooks/) — operational procedures created in Phase 4.

---

## At a glance

| Phase | What | Gate |
|---|---|---|
| 1 — Prerequisites | App-side changes (auth, config, SQLite PRAGMAs, Docker, security headers) | Local docker-compose smoke green; new tests at ≥ 90% coverage |
| 2 — Infrastructure | Terraform modules + cloud-init bootstrap; apply to `drill` env | `terraform apply` succeeds; `/health` reachable via public DNS on drill |
| 3 — Deployment | Build + deploy workflows; cosign; rollback script | Push to `main` lands a signed image on `drill`; manual rollback restores previous SHA |
| 4 — Validation | Backup drill; security scan; smoke; monitoring; runbooks | Monthly drill automated; Mozilla Observatory A+; UptimeRobot wired; production acceptance |

---

## Dependencies

Phase 2 depends on Phase 1 (needs a `Dockerfile` and a `/health` endpoint before any VM is useful).
Phase 3 depends on Phase 2 (needs the VM and the deploy user before a deploy workflow can run).
Phase 4 depends on Phase 3 (needs real deploys to validate).

Within Phase 1 most tasks are parallel-safe; the data-layer PRAGMA change (T-D05) must land before Litestream config (T-D23 in Phase 2).

v3 also assumes the v2 redesign has shipped — the deployed artefact is the redesigned app, not the pre-redesign one.

---

## Change policy

Per repo `CLAUDE.md`:

- Any code change in Phase 1 must reference the task id in the commit (`feat(T-Dxx): ...`).
- Any new architectural decision outside the six ADRs 0032-0037 requires a new ADR before code lands.
- Any Terraform resource added outside what ADR-0035 describes requires an amendment to ADR-0035 before `terraform apply`.
- Append a dated line to `docs/CHANGELOG.md` after each merged task.
