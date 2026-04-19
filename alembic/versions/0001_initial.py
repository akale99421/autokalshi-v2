"""initial ledger schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-18
"""

from __future__ import annotations

import re
from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


_SQLITE_SUBS: tuple[tuple[str, str], ...] = (
    (r"\bTIMESTAMPTZ\b", "TIMESTAMP"),
    (r"\bBIGSERIAL\b", "INTEGER"),
    (r"\bJSONB\b", "TEXT"),
    (r"DEFAULT '\{\}'::jsonb", "DEFAULT '{}'"),
    (r"DEFAULT now\(\)", "DEFAULT CURRENT_TIMESTAMP"),
)


def _sql_for_dialect(dialect_name: str) -> str:
    sql_path = Path(__file__).resolve().parent.parent.parent / "migrations" / "0001_initial.sql"
    sql = sql_path.read_text()
    if dialect_name == "sqlite":
        for pat, sub in _SQLITE_SUBS:
            sql = re.sub(pat, sub, sql)
    return sql


def _split_statements(sql: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                out.append(stmt)
            buf = []
    return out


def upgrade() -> None:
    bind = op.get_bind()
    sql = _sql_for_dialect(bind.dialect.name)
    for stmt in _split_statements(sql):
        op.execute(stmt)


def downgrade() -> None:
    for table in (
        "risk_gate_events",
        "performance_snapshots",
        "orderbook_snapshots",
        "settlements",
        "positions",
        "ledger_fills",
        "order_events",
        "ledger_orders",
        "strategy_transitions",
        "strategies",
        "wallets",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
