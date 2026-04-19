-- 0001_initial.sql — ledger schema. Source: Architecture/Ledger §1.
--
-- Postgres-first. Alembic executes this string against whatever backend the
-- session points at. Syntax that is not portable to sqlite is translated by
-- alembic/env.py at apply time (see DDL_SQLITE_SUBS). The canonical file is
-- Postgres, because the invariants in Architecture/Ledger §2 depend on
-- Postgres features (advisory locks, jsonb, gen_random_uuid).

-- Wallets: exactly two rows, forever.
CREATE TABLE wallets (
    id               TEXT PRIMARY KEY CHECK (id IN ('paper', 'live')),
    balance_cents    BIGINT    NOT NULL,
    reserved_cents   BIGINT    NOT NULL DEFAULT 0,
    source_of_truth  TEXT      NOT NULL CHECK (source_of_truth IN ('internal','kalshi_api')),
    last_reconciled_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Strategy registry.
CREATE TABLE strategies (
    id                 TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    status             TEXT NOT NULL CHECK (status IN
                         ('proposed','backtest','paper','live_ready','live','paused','retired')),
    mode               TEXT NOT NULL CHECK (mode IN ('paper','live')),
    wallet_id          TEXT NOT NULL REFERENCES wallets(id),
    code_hash          TEXT NOT NULL,
    code_uri           TEXT,
    card_path          TEXT NOT NULL,
    version            TEXT NOT NULL DEFAULT '1',
    scan_interval_sec  INTEGER NOT NULL DEFAULT 60,
    target_markets     TEXT,
    risk_params        JSONB NOT NULL DEFAULT '{}'::jsonb,
    starting_balance_cents BIGINT NOT NULL DEFAULT 100000,
    state_json         TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- State transitions (audit log).
CREATE TABLE strategy_transitions (
    id                 BIGSERIAL PRIMARY KEY,
    strategy_id        TEXT NOT NULL REFERENCES strategies(id),
    from_status        TEXT NOT NULL,
    to_status          TEXT NOT NULL,
    reason             TEXT NOT NULL,
    actor              TEXT NOT NULL,
    paper_pnl_cents    BIGINT,
    live_pnl_cents     BIGINT,
    trade_count        INTEGER,
    transitioned_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Orders.
CREATE TABLE ledger_orders (
    id                  TEXT PRIMARY KEY,
    client_order_id     TEXT UNIQUE,
    kalshi_order_id     TEXT UNIQUE,
    strategy_id         TEXT NOT NULL REFERENCES strategies(id),
    wallet_id           TEXT NOT NULL REFERENCES wallets(id),
    ticker              TEXT NOT NULL,
    event_ticker        TEXT,
    side                TEXT NOT NULL CHECK (side IN ('yes','no')),
    action              TEXT NOT NULL CHECK (action IN ('buy','sell')),
    order_type          TEXT NOT NULL DEFAULT 'limit',
    price_cents         INTEGER NOT NULL CHECK (price_cents BETWEEN 1 AND 99),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    filled_quantity     INTEGER NOT NULL DEFAULT 0,
    avg_fill_price_cents INTEGER,
    fees_cents          INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL CHECK (status IN
                          ('submitted','routing','acked','resting','partial','filled',
                           'canceled','expired','rejected','failed','settled')),
    time_in_force       TEXT NOT NULL DEFAULT 'good_till_canceled',
    cancel_reason       TEXT,
    edge_cents_at_entry INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    settled_at          TIMESTAMPTZ
);
CREATE INDEX idx_orders_strategy_status ON ledger_orders (strategy_id, status);
CREATE INDEX idx_orders_ticker_status   ON ledger_orders (ticker, status);

-- Order events.
CREATE TABLE order_events (
    id           BIGSERIAL PRIMARY KEY,
    order_id     TEXT NOT NULL REFERENCES ledger_orders(id),
    event_type   TEXT NOT NULL CHECK (event_type IN
                   ('created','submitted','acked','resting','partial_fill','filled',
                    'cancelled','rejected','failed','expired','settled')),
    details      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_order_events_order ON order_events (order_id, created_at);

-- Fills. Immutable (enforced by trigger on Postgres; assertion in code on sqlite).
CREATE TABLE ledger_fills (
    id                       TEXT PRIMARY KEY,
    order_id                 TEXT NOT NULL REFERENCES ledger_orders(id),
    strategy_id              TEXT NOT NULL REFERENCES strategies(id),
    wallet_id                TEXT NOT NULL REFERENCES wallets(id),
    kalshi_fill_id           TEXT UNIQUE,
    ticker                   TEXT NOT NULL,
    side                     TEXT NOT NULL CHECK (side IN ('yes','no')),
    action                   TEXT NOT NULL CHECK (action IN ('buy','sell')),
    fill_price_cents         INTEGER NOT NULL CHECK (fill_price_cents BETWEEN 1 AND 100),
    quantity                 INTEGER NOT NULL CHECK (quantity > 0),
    is_taker                 BOOLEAN NOT NULL DEFAULT true,
    fees_cents               INTEGER NOT NULL DEFAULT 0,
    best_bid_cents_at_fill   INTEGER,
    best_ask_cents_at_fill   INTEGER,
    orderbook_snapshot_hash  TEXT,
    is_settlement            BOOLEAN NOT NULL DEFAULT false,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_fills_strategy_time ON ledger_fills (strategy_id, created_at DESC);
CREATE INDEX idx_fills_order         ON ledger_fills (order_id);
CREATE INDEX idx_fills_ticker_time   ON ledger_fills (ticker, created_at);

-- Positions.
CREATE TABLE positions (
    id                 BIGSERIAL PRIMARY KEY,
    strategy_id        TEXT NOT NULL REFERENCES strategies(id),
    wallet_id          TEXT NOT NULL REFERENCES wallets(id),
    ticker             TEXT NOT NULL,
    side               TEXT NOT NULL CHECK (side IN ('yes','no')),
    quantity           INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    avg_entry_cents    INTEGER NOT NULL DEFAULT 0,
    total_cost_cents   BIGINT  NOT NULL DEFAULT 0,
    realized_pnl_cents BIGINT  NOT NULL DEFAULT 0,
    total_fees_cents   BIGINT  NOT NULL DEFAULT 0,
    settled            BOOLEAN NOT NULL DEFAULT false,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (strategy_id, ticker, side)
);

-- Settlements.
CREATE TABLE settlements (
    id               BIGSERIAL PRIMARY KEY,
    ticker           TEXT UNIQUE NOT NULL,
    event_ticker     TEXT NOT NULL,
    result           TEXT NOT NULL CHECK (result IN ('yes','no')),
    yes_payout_cents INTEGER NOT NULL CHECK (yes_payout_cents IN (0, 100)),
    no_payout_cents  INTEGER NOT NULL CHECK (no_payout_cents IN (0, 100)),
    settled_at       TIMESTAMPTZ NOT NULL,
    observed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Orderbook snapshots (content-addressed).
CREATE TABLE orderbook_snapshots (
    hash         TEXT PRIMARY KEY,
    ticker       TEXT NOT NULL,
    captured_at  TIMESTAMPTZ NOT NULL,
    depth_json   JSONB NOT NULL
);
CREATE INDEX idx_snapshots_ticker_time ON orderbook_snapshots (ticker, captured_at);

-- Performance snapshots.
CREATE TABLE performance_snapshots (
    id                  BIGSERIAL PRIMARY KEY,
    strategy_id         TEXT NOT NULL REFERENCES strategies(id),
    balance_cents       BIGINT  NOT NULL,
    realized_pnl_cents  BIGINT  NOT NULL,
    unrealized_pnl_cents BIGINT NOT NULL,
    total_pnl_cents     BIGINT  NOT NULL,
    trade_count         INTEGER NOT NULL,
    win_count           INTEGER NOT NULL,
    loss_count          INTEGER NOT NULL,
    exposure_cents      BIGINT  NOT NULL,
    sharpe              REAL,
    max_drawdown_cents  BIGINT,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_perf_strategy_time ON performance_snapshots (strategy_id, captured_at DESC);

-- Risk-gate audit.
CREATE TABLE risk_gate_events (
    id                BIGSERIAL PRIMARY KEY,
    gate_name         TEXT NOT NULL,
    strategy_id       TEXT REFERENCES strategies(id),
    order_id          TEXT REFERENCES ledger_orders(id),
    wallet_balance_cents BIGINT,
    detail            JSONB,
    tripped_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at       TIMESTAMPTZ
);
