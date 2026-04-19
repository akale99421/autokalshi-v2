"""Strategy-facing types from Architecture/Strategies §3.

These are the pydantic shapes every strategy sees. They are the contract:
the engine can refactor internals freely, but these models do not change
without a version bump. All money is integer cents in the trading path —
only statistical metrics may be float.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_frozen = ConfigDict(frozen=True, extra="forbid")

Side = Literal["yes", "no"]
Action = Literal["buy", "sell"]
TIF = Literal["good_till_canceled", "immediate_or_cancel", "fill_or_kill"]
OrderStatus = Literal[
    "submitted",
    "routing",
    "acked",
    "resting",
    "partial",
    "filled",
    "canceled",
    "expired",
    "rejected",
    "failed",
    "settled",
]


class Market(BaseModel):
    model_config = _frozen
    ticker: str
    event_ticker: str
    series_ticker: str
    title: str
    status: Literal["open", "closed", "settled", "finalized"]
    yes_bid_cents: int | None
    yes_ask_cents: int | None
    yes_bid_size: int | None
    yes_ask_size: int | None
    last_price_cents: int | None
    volume: int
    open_interest: int
    close_time: datetime
    observed_at: datetime
    result: Literal["yes", "no"] | None = None


class OrderbookLevel(BaseModel):
    model_config = _frozen
    price_cents: int
    size: int


class Orderbook(BaseModel):
    model_config = _frozen
    ticker: str
    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    captured_at: datetime


class Position(BaseModel):
    model_config = _frozen
    ticker: str
    side: Side
    quantity: int
    avg_entry_cents: int
    realized_pnl_cents: int
    unrealized_pnl_cents: int | None
    total_fees_cents: int
    settled: bool


class Balance(BaseModel):
    model_config = _frozen
    strategy_id: str
    starting_cents: int
    available_cents: int
    reserved_cents: int
    total_invested_cents: int
    total_fees_cents: int
    realized_pnl_cents: int
    unrealized_pnl_cents: int
    total_pnl_cents: int


class OrderIntent(BaseModel):
    model_config = _frozen
    ticker: str
    side: Side
    action: Action
    price_cents: int = Field(ge=1, le=99)
    quantity: int = Field(ge=1)
    time_in_force: TIF = "good_till_canceled"
    client_order_id: str | None = None
    edge_cents: int | None = None


class Order(BaseModel):
    model_config = _frozen
    id: str
    client_order_id: str | None
    kalshi_order_id: str | None
    strategy_id: str
    ticker: str
    side: Side
    action: Action
    price_cents: int
    quantity: int
    filled_quantity: int
    avg_fill_price_cents: int | None
    fees_cents: int
    status: OrderStatus
    time_in_force: TIF
    created_at: datetime
    updated_at: datetime


class Fill(BaseModel):
    model_config = _frozen
    id: str
    order_id: str
    strategy_id: str
    ticker: str
    side: Side
    action: Action
    price_cents: int
    quantity: int
    is_taker: bool
    fees_cents: int
    best_bid_cents_at_fill: int | None
    best_ask_cents_at_fill: int | None
    orderbook_snapshot_hash: str | None
    is_settlement: bool
    created_at: datetime


class Settlement(BaseModel):
    model_config = _frozen
    ticker: str
    event_ticker: str
    result: Side
    yes_payout_cents: int
    no_payout_cents: int
    settled_at: datetime


class OrderAck(BaseModel):
    model_config = _frozen
    order_id: str
    client_order_id: str | None
    status: OrderStatus
    reject_reason: str | None = None


class CancelAck(BaseModel):
    model_config = _frozen
    order_id: str
    status: OrderStatus


__all__ = [
    "Action",
    "Balance",
    "CancelAck",
    "Fill",
    "Market",
    "Order",
    "OrderAck",
    "OrderIntent",
    "OrderStatus",
    "Orderbook",
    "OrderbookLevel",
    "Position",
    "Settlement",
    "Side",
    "TIF",
]
