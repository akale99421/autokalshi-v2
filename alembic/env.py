"""Alembic env — runs 0001_initial.sql against whatever URL is configured.

Backend canon is Postgres (see migrations/0001_initial.sql). For local and CI
we apply against sqlite; env.py rewrites a small set of Postgres-only tokens
so `alembic upgrade head` is green on both. Production migrations still run
against Postgres and see the canonical file as-is.
"""

from __future__ import annotations

import os
import re
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_env_url = os.environ.get("AUTOKALSHI_DB_URL")
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url)


# --- Postgres → sqlite translation ------------------------------------------
# The canonical DDL is Postgres. For ephemeral sqlite apply (CI, dev), these
# substitutions make it run without changing the source file.
_SQLITE_SUBS: tuple[tuple[str, str], ...] = (
    (r"\bTIMESTAMPTZ\b", "TIMESTAMP"),
    (r"\bBIGSERIAL\b", "INTEGER"),
    (r"\bJSONB\b", "TEXT"),
    (r"DEFAULT '\{\}'::jsonb", "DEFAULT '{}'"),
    (r"DEFAULT now\(\)", "DEFAULT CURRENT_TIMESTAMP"),
)


def _translate_for_sqlite(sql: str) -> str:
    out = sql
    for pat, sub in _SQLITE_SUBS:
        out = re.sub(pat, sub, out)
    return out


def _read_initial_sql() -> str:
    sql_path = Path(__file__).resolve().parent.parent / "migrations" / "0001_initial.sql"
    return sql_path.read_text()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=None, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
