# autokalshi-v2

Typed prediction-market trading platform for Kalshi.

- **Strategies** declare a small Protocol; the engine owns data, clock, orders, DB.
- **Ledger** is the source of truth. Integer cents, immutable fills, single writer.
- **Paper and live share the same tables** — only `wallet_id` differs.

See `Projects/AutoKalshi/` in the Ohara vault for architecture and plans.

## Quick start

```bash
pip install -e ".[dev]"
pre-commit install
pytest -q
ruff check .
mypy autokalshi
```

Apply the initial schema to an ephemeral sqlite:

```bash
alembic upgrade head
```
