# Phase 11 — Shared Form Primitives + Overview Enhancements + Budget Page v2 (page-composition version 2) + Fixes

> Status: pending (docs scaffolding landed via T-110; code starts at T-111). Scope: web layer only. No change to data model, service arithmetic, or repository shape. Six task files land together: the Budget + Account + Overview changes compose from the same shared primitives, and two surgical fixes (ledger row actions + transit lock) ride on the same phase.

## Trigger

Field-use report 2026-10-27 surfaces seven UX / correctness defects that compound through the create / edit / list surfaces of the app:

1. **Overview Budget panel** does not show "left per day", even though the Budget page hero has carried it since Phase 9. One `MonthSummary` field, two surfaces, divergent treatment.
2. **Overview Upcoming** has a `+ Planned` button (T-093) but no `+ Recurring` partner, even though `services.planned.list_planned` already unions persisted + virtual rows. The affordance is asymmetric to the data.
3. **Transaction / planned / recurring forms** are inconsistent: date fields ship empty (even though "today" is 95% of the use case), amount fields accept any text (server-side validation only), id-reference `<select>`s are plain dropdowns that get painful past ~15 options.
4. **Accounts** render the create form inline (not slide-over), the Reconcile modal has no close button, "Credit card (liability)" mis-scopes ADR-0024 (the feature is any liability, not just cards), and the credit-limit field stays visible even when the toggle is off.
5. **Budget page** carries the income anchor selector in section 2b, which is a user preference and belongs in the Settings drawer. The Rules section three-column table over-promises on what's being edited; the right shape is `category + default inline + Override…` per row. Users planning a quarter / year also need a cross-month view (Yearly table).
6. **Ledger row actions** are broken: clicking **Edit** removes the row (should swap to form); no **Delete** button exists at all.
7. **Category creation in Settings** still exposes `transit` as a user-pickable direction, even though the single seeded `Transit` system category is the only transit-direction row the app should ever carry.

## Decisions

- [ADR-0030 — Shared Form Interaction Primitives](../../../adr/0030-shared-form-interaction-primitives.md): one combobox macro, one digit-only script, one `today_local()` helper, one `data-reset-on-submit` listener, one close-affordance convention, one conditional-field pattern. Reused by every create / edit surface.
- [ADR-0031 — Budget Page Composition v2](../../../adr/0031-budget-page-composition-v2.md): income anchor relocates to `/settings?tab=prefs#income-anchor`; Rules section rewrites as `category + default + Override`; new Yearly budget table under Rules; three-column Rules table scrapped.

## Scope

| Change | Where | Source |
|---|---|---|
| `today_local()` Jinja global + default date on create forms | `web/app.py`, every create partial | ADR-0030 §1 |
| `static/js/numeric-input.js` + `data-numeric` on every amount input | `web/static/`, every amount field | ADR-0030 §2 |
| `_partials/combobox.html` macro + `static/js/combobox.js` | `web/templates/_partials/`, `web/static/` | ADR-0030 §3 |
| Category / account / dest / currency selects → combobox | transaction / planned / recurring / account forms + Override form | ADR-0030 §3 |
| `ISO_4217_CURRENCIES` constant | `domain/money.py` | ADR-0030 §3 |
| Reconcile modal → shared slide-over wrapper | `partials/accounts/_reconcile_modal.html` + `partials/_slideover.html` | ADR-0030 §4 |
| `data-reset-on-submit` listener on create forms | `base.html` scripts + every create partial | ADR-0030 §5 |
| Liability toggle relabel + conditional credit-limit markup | `partials/accounts/_form.html` | ADR-0030 §6 |
| Overview budget panel shows left-per-day | `templates/home/_month_panel.html` | §3.9 F4.6 relay |
| Overview Upcoming gains `+ Recurring` button | `templates/home/_upcoming_panel.html` | §3.9 F3.3 |
| Delete `/budget` Section 2b (income anchor) | `templates/budget/index.html` | ADR-0031 §1 |
| Add income anchor section to Preferences tab | `templates/settings/_prefs.html` | ADR-0031 §1 |
| Rewrite Rules section: `category + default inline + Override…` | `templates/budget/index.html` | ADR-0031 §2 |
| Override slide-over + `POST /budget/rules/{category_id}/overrides` dispatcher | `routers/budget.py`, `templates/partials/budget/_override_form.html` | ADR-0031 §2 |
| New Yearly budget table (`#budget-yearly`) + fragment endpoint | `templates/budget/_yearly.html`, `routers/budget.py` | ADR-0031 §3 |
| `services.budget.yearly_grid` projection helper | `services/budget.py` | ADR-0031 §3 |
| Ledger row Edit regression fix + Delete button | `partials/transactions/_row.html`, `partials/planned/_row.html`, `partials/recurring/_row.html` | §F1.5 |
| Category direction lockdown: `transit` + `adjustment` system-only | `templates/settings/_categories.html`, `routers/categories.py`, `services/categories.py` | §F1.6 |

## Task table

| ID | Task | Dep |
|---|---|---|
| T-110 | ADR-0030 + ADR-0031 + requirements + Phase 11 docs scaffolding (docs only) | — |
| T-111 | Shared form primitives (combobox / digit-only / default date / clear-on-save / close affordance / conditional field + liability relabel) | T-110 |
| T-112 | Overview enhancements (left-per-day on month panel + `+ Recurring` on upcoming panel) | T-110 |
| T-113 | Budget page v2 (anchor → Settings/Prefs + Rules redesign + Yearly table + Override dispatcher) | T-110, T-111 |
| T-114 | Ledger row actions: fix Edit regression + add Delete button | T-110 |
| T-115 | Lock `transit` direction out of user category creation | T-110 |

## Dependency map

- **T-110** unblocks every code task; it is the docs round itself.
- **T-111** underpins the combobox + slide-over + digit-only + default-date + conditional-field primitives that **T-113** composes from. T-113 must land after T-111 to pick up the shared macros.
- **T-112**, **T-114**, **T-115** are independent of T-111 / T-113 (narrow scope on `_month_panel.html` + `_upcoming_panel.html`, ledger row partials, and the categories form respectively).

Parallel-safe set once T-110 is in: `{T-111, T-112, T-114, T-115}`. T-113 waits on T-111.

Est. size: each code task ≤ 1 day; whole phase ~1 week sequential, ~2 days with full fan-out.

## Exit criteria (verification checklist)

- [ ] `just migrate` is a no-op (no migrations in this phase).
- [ ] `just seed` unchanged.
- [ ] `just test` — new unit + integration tests pass. Coverage ≥ 90%.
- [ ] `just lint` + `just typecheck` + `just ci` green.
- [ ] `just test-visual` — baselines refreshed on `/`, `/accounts`, `/budget`, `/ledger?view=actual|planned|recurring`, `/settings?tab=prefs`; byte-equal match thereafter.
- [ ] `frontend-visual-audit` sweep on every affected route at 1440 / 1024 / 375; non-zero `horizontalScroll` / `overflowingElements` / `duplicateIds` / `consoleErrors` / `requestFailures` triaged.
- [ ] Manual: `just dev` →
  - [ ] Overview `/` shows "left per day" under the "amount left" headline; `+ Recurring` button opens `/recurring/new` slide-over.
  - [ ] `/accounts` → `+ New account` opens a slide-over with a visible close `×`; currency field is a filterable combobox over ISO 4217; "Credit (liability)" toggle hides credit-limit when off; Save clears the form.
  - [ ] `/accounts/{id}/reconcile` modal has a visible close `×` and dismisses on Esc / backdrop click.
  - [ ] Transaction / planned / recurring forms: date defaults to today; amount rejects non-digit input; category / account / dest render as comboboxes that filter case-insensitively on typed substring.
  - [ ] `/budget` renders the new Rules section (`category + default + Override…`); clicking Override opens a slide-over with recurring / one-off radio; submit creates the override and the Yearly table + Monthly summary pick it up.
  - [ ] `/budget` renders the Yearly table under Rules; cells reflect tier dominance via typography; cell edit submits a one-off override; year picker switches via HTMX fragment.
  - [ ] `/settings?tab=prefs` carries the income anchor selector; changing it fires `HX-Trigger: budget-stale` and the Budget hero caption updates.
  - [ ] `/ledger?view=actual`: clicking **Edit** on a row swaps the row into its edit form (does not remove it); clicking **Delete** confirms + removes the row (soft-deleted server-side).
  - [ ] Settings → Categories → New: direction dropdown exposes only `income` + `expense`; posting `direction=transit` returns 422.
- [ ] `docs/CHANGELOG.md` entry for the phase landing day.

## See also

- Decisions: [ADR-0030](../../../adr/0030-shared-form-interaction-primitives.md), [ADR-0031](../../../adr/0031-budget-page-composition-v2.md).
- Prior phases: [Phase 8](../phase-8/) (first field-use round), [Phase 9](../phase-9/) (introduced the income anchor + left-daily-spend arithmetic).
- Related ADRs: [ADR-0014](../../../adr/0014-budget-flat-no-rollover-three-tier.md) (three-tier resolution — unchanged), [ADR-0023](../../../adr/0023-ux-redesign-information-architecture.md) (overlay stack, Quick-add FAB), [ADR-0024](../../../adr/0024-liability-accounts-and-credit-limit.md) (liability data contract), [ADR-0025](../../../adr/0025-user-preferences-and-income-anchor.md) (preference store), [ADR-0026](../../../adr/0026-fab-visibility-scope.md) (FAB scope — unchanged by `/budget` Override).
