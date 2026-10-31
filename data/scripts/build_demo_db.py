"""Build an anonymized demo SQLite DB from the prod DB.

Usage:
    python data/scripts/build_demo_db.py --from data/budget.sqlite --to data/demo.sqlite [--force]

Behaviour:
- Copies the source DB file to the target path (refuses to clobber unless
  ``--force`` is passed).
- Rewrites account names to generic English labels keyed by (type, index).
- Rewrites non-system category names to generic English labels.
- Scrubs all transaction / planned / recurring / override descriptions.
- Scales monetary values by a fixed factor with deterministic per-row jitter
  so shapes stay realistic but values diverge from prod. Signs are preserved
  (reconciliation adjustment direction uses signed amounts — see ADR-0008).
- Clears the audit_log (user-identifiable history).
- VACUUMs the result.

The script never touches the source DB. The source filename is enforced
to end with ``budget.sqlite`` as a tripwire against accidental swaps.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Final

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCALE_FACTOR: Final = 0.73
JITTER_RANGE: Final = 0.15  # ±15% deterministic jitter per row


def _jitter(seed: str) -> float:
    """Deterministic jitter in [1 - JITTER_RANGE, 1 + JITTER_RANGE]."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    # First 8 bytes → unsigned int → map to [-1.0, 1.0]
    n = int.from_bytes(digest[:8], "big")
    unit = (n / 2**64) * 2.0 - 1.0
    return 1.0 + unit * JITTER_RANGE


def _scale(amount: int, seed: str) -> int:
    """Scale a signed minor-unit amount with deterministic jitter.

    Preserves sign; floors magnitude at 1 for non-zero inputs so direction
    stays legible.
    """
    if amount == 0:
        return 0
    scaled = amount * SCALE_FACTOR * _jitter(seed)
    rounded = round(scaled)
    if rounded == 0:
        rounded = 1 if amount > 0 else -1
    return rounded


# -- Renaming maps ----------------------------------------------------------

# Generic account names keyed by (type, 1-based index within type).
_ACCOUNT_NAME_BY_TYPE: Final[dict[str | None, list[str]]] = {
    "bank": ["Checking", "Checking EUR", "Everyday Spending"],
    "savings": ["Savings"],
    "investment": ["Investments A", "Investments B", "Investments C", "Investments D"],
    "credit_card": ["Credit Card"],
    "cash": ["Cash Wallet"],
    None: ["Account"],
}

# English generics for non-system categories. Keyed by direction so the
# anonymizer stays stable even if prod category rows change.
_CATEGORY_LABELS_BY_DIRECTION: Final[dict[str, list[str]]] = {
    "income": [
        "Salary",
        "Side Income",
        "Interest",
        "Profit Share",
        "VAT Refund",
    ],
    "expense": [
        "Taxes",
        "Fixed Costs",
        "Subscriptions",
        "Groceries",
        "Sport & Hobby",
        "Health & Beauty",
        "Car",
        "Nights Out",
        "Travel",
        "Big Purchases",
        "Transport",
        "Entertainment",
        "Other",
        "Gifts",
        "Takeaway",
        "Bank Fees",
    ],
}


def _assign_account_names(rows: list[sqlite3.Row]) -> dict[int, str]:
    """Build a stable id → generic-name mapping grouped by account type."""
    counters: dict[str | None, int] = {}
    mapping: dict[int, str] = {}
    for row in rows:
        acc_type = row["type"]
        pool = _ACCOUNT_NAME_BY_TYPE.get(acc_type, _ACCOUNT_NAME_BY_TYPE[None])
        idx = counters.get(acc_type, 0)
        counters[acc_type] = idx + 1
        # Fallback name never repeats an exact earlier one.
        name = pool[idx] if idx < len(pool) else f"{pool[-1]} #{idx + 1}"
        mapping[row["id"]] = name
    return mapping


def _assign_category_names(rows: list[sqlite3.Row]) -> dict[int, str]:
    """Build a stable id → generic-name mapping for non-system categories."""
    counters: dict[str, int] = {}
    mapping: dict[int, str] = {}
    for row in rows:
        if row["is_system"]:
            continue
        direction = row["direction"]
        pool = _CATEGORY_LABELS_BY_DIRECTION.get(direction, ["Other"])
        idx = counters.get(direction, 0)
        counters[direction] = idx + 1
        name = pool[idx] if idx < len(pool) else f"{pool[-1]} #{idx + 1}"
        mapping[row["id"]] = name
    return mapping


# -- Anonymizer -------------------------------------------------------------


def anonymize(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row

    # Snapshot category directions + names before we mutate anything —
    # we need them to derive placeholder descriptions.
    cat_rows = list(conn.execute("SELECT id, name, direction, is_system FROM categories"))
    cat_name_map = _assign_category_names(cat_rows)
    # Final (post-rename) category name per id, used for description text.
    final_cat_name: dict[int, str] = {}
    for row in cat_rows:
        final_cat_name[row["id"]] = cat_name_map.get(row["id"], row["name"])

    acc_rows = list(conn.execute("SELECT id, type FROM accounts ORDER BY id"))
    acc_name_map = _assign_account_names(acc_rows)

    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        # Accounts — rename + scale opening balance / credit limit.
        for row in conn.execute(
            "SELECT id, opening_balance, credit_limit_minor FROM accounts"
        ).fetchall():
            new_name = acc_name_map[row["id"]]
            new_opening = _scale(row["opening_balance"], f"acc_open:{row['id']}")
            new_limit = (
                _scale(row["credit_limit_minor"], f"acc_limit:{row['id']}")
                if row["credit_limit_minor"] is not None
                else None
            )
            cur.execute(
                "UPDATE accounts SET name = ?, opening_balance = ?, credit_limit_minor = ?"
                " WHERE id = ?",
                (new_name, new_opening, new_limit, row["id"]),
            )

        # Categories — rename non-system ones.
        for cid, new_name in cat_name_map.items():
            cur.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, cid))

        # Transactions — scrub description + scale amount.
        for row in conn.execute("SELECT id, category_id, amount FROM transactions").fetchall():
            new_desc = final_cat_name.get(row["category_id"], "Entry")
            new_amount = _scale(row["amount"], f"txn:{row['id']}")
            cur.execute(
                "UPDATE transactions SET description = ?, amount = ? WHERE id = ?",
                (new_desc, new_amount, row["id"]),
            )

        # Planned transactions.
        for row in conn.execute(
            "SELECT id, category_id, amount FROM planned_transactions"
        ).fetchall():
            new_desc = final_cat_name.get(row["category_id"], "Planned")
            new_amount = _scale(row["amount"], f"plan:{row['id']}")
            cur.execute(
                "UPDATE planned_transactions SET description = ?, amount = ? WHERE id = ?",
                (new_desc, new_amount, row["id"]),
            )

        # Recurring rules — scrub default_description + scale default_amount.
        # Formula amounts stay as-is (symbolic references to other rule ids).
        for row in conn.execute(
            "SELECT id, category_id, default_amount FROM recurring_rules"
        ).fetchall():
            new_desc = final_cat_name.get(row["category_id"], "Recurring")
            new_amount = _scale(row["default_amount"], f"rr:{row['id']}")
            cur.execute(
                "UPDATE recurring_rules SET default_description = ?, default_amount = ?"
                " WHERE id = ?",
                (new_desc, new_amount, row["id"]),
            )

        # Recurring rule overrides — scrub description + scale amount override.
        for row in conn.execute(
            "SELECT id, amount_override FROM recurring_rule_overrides"
        ).fetchall():
            new_amount = (
                _scale(row["amount_override"], f"rro:{row['id']}")
                if row["amount_override"] is not None
                else None
            )
            cur.execute(
                "UPDATE recurring_rule_overrides SET description_override = NULL,"
                " amount_override = ? WHERE id = ?",
                (new_amount, row["id"]),
            )

        # Snapshots — scale balance, scrub note.
        for row in conn.execute("SELECT id, balance FROM account_snapshots").fetchall():
            new_balance = _scale(row["balance"], f"snap:{row['id']}")
            cur.execute(
                "UPDATE account_snapshots SET balance = ?, note = '' WHERE id = ?",
                (new_balance, row["id"]),
            )

        # Budget defaults.
        for row in conn.execute("SELECT id, amount FROM budget_defaults").fetchall():
            new_amount = _scale(row["amount"], f"bd:{row['id']}")
            cur.execute(
                "UPDATE budget_defaults SET amount = ? WHERE id = ?",
                (new_amount, row["id"]),
            )

        # Budget one-off overrides.
        for row in conn.execute("SELECT id, amount FROM budget_one_off_overrides").fetchall():
            new_amount = _scale(row["amount"], f"boo:{row['id']}")
            cur.execute(
                "UPDATE budget_one_off_overrides SET amount = ? WHERE id = ?",
                (new_amount, row["id"]),
            )

        # Budget recurring overrides.
        for row in conn.execute("SELECT id, amount FROM budget_recurring_overrides").fetchall():
            new_amount = _scale(row["amount"], f"bro:{row['id']}")
            cur.execute(
                "UPDATE budget_recurring_overrides SET amount = ? WHERE id = ?",
                (new_amount, row["id"]),
            )

        # Audit log — contains free-text diffs of user data. Drop it entirely.
        cur.execute("DELETE FROM audit_log")

        # Users — rename default user.
        cur.execute("UPDATE users SET name = 'demo' WHERE id = 1")

        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise

    conn.execute("VACUUM")


# -- Entry point ------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from",
        dest="src",
        default=str(PROJECT_ROOT / "data" / "budget.sqlite"),
        help="Source SQLite file (prod). Must end with 'budget.sqlite'.",
    )
    parser.add_argument(
        "--to",
        dest="dst",
        default=str(PROJECT_ROOT / "data" / "demo.sqlite"),
        help="Target SQLite file (demo).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target file if it already exists.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    if not src.exists():
        print(f"[build-demo] source not found: {src}", file=sys.stderr)
        return 2
    if not src.name.endswith("budget.sqlite"):
        print(
            "[build-demo] refusing: source basename must end with 'budget.sqlite'"
            f" (got {src.name})",
            file=sys.stderr,
        )
        return 2
    if src == dst:
        print("[build-demo] refusing: source and target are the same file", file=sys.stderr)
        return 2
    if dst.exists() and not args.force:
        print(f"[build-demo] target exists (use --force to overwrite): {dst}", file=sys.stderr)
        return 2

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    # Drop any WAL/SHM sidecars so the demo DB opens cleanly.
    for suffix in ("-wal", "-shm"):
        side = dst.with_name(dst.name + suffix)
        if side.exists():
            side.unlink()

    print(f"[build-demo] copied {src} -> {dst}")

    conn = sqlite3.connect(dst)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        anonymize(conn)
    finally:
        conn.close()

    print(f"[build-demo] anonymized {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
