"""Verify `alembic upgrade head` produces the expected 11 ledger tables."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

EXPECTED_TABLES = {
    "wallets",
    "strategies",
    "strategy_transitions",
    "ledger_orders",
    "order_events",
    "ledger_fills",
    "positions",
    "settlements",
    "orderbook_snapshots",
    "performance_snapshots",
    "risk_gate_events",
}

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_alembic_upgrade_head_on_sqlite(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "migration-check.db"
    env = os.environ.copy()
    env["AUTOKALSHI_DB_URL"] = f"sqlite:///{db_path}"
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"alembic failed: {result.stderr}"

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "AND name != 'alembic_version'"
        ).fetchall()
    names = {r[0] for r in rows}
    assert EXPECTED_TABLES.issubset(names), (
        f"missing tables: {EXPECTED_TABLES - names}; got: {names}"
    )
