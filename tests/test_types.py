"""Round-trip tests for every strategy-facing pydantic type in autokalshi.types."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from autokalshi.types import (
    Balance,
    CancelAck,
    Fill,
    Market,
    Order,
    OrderAck,
    Orderbook,
    OrderbookLevel,
    OrderIntent,
    Position,
    Settlement,
)

NOW = datetime(2026, 4, 18, 12, 0, 0, tzinfo=UTC)


def _roundtrip(instance):  # type: ignore[no-untyped-def]
    """Assert model_validate(model_dump()) returns an equal instance."""
    cls = type(instance)
    rebuilt = cls.model_validate(instance.model_dump())
    assert rebuilt == instance
    return rebuilt


def test_market_roundtrip() -> None:
    m = Market(
        ticker="KXHIGHNY-26APR18-T75",
        event_ticker="KXHIGHNY-26APR18",
        series_ticker="KXHIGHNY",
        title="NY high 75°F?",
        status="open",
        yes_bid_cents=42,
        yes_ask_cents=44,
        yes_bid_size=100,
        yes_ask_size=200,
        last_price_cents=43,
        volume=1000,
        open_interest=500,
        close_time=NOW,
        observed_at=NOW,
        result=None,
    )
    _roundtrip(m)


def test_orderbook_level_roundtrip() -> None:
    lvl = OrderbookLevel(price_cents=42, size=100)
    _roundtrip(lvl)


def test_orderbook_roundtrip() -> None:
    ob = Orderbook(
        ticker="KXHIGHNY-26APR18-T75",
        bids=[OrderbookLevel(price_cents=42, size=100), OrderbookLevel(price_cents=41, size=50)],
        asks=[OrderbookLevel(price_cents=44, size=200)],
        captured_at=NOW,
    )
    _roundtrip(ob)


def test_position_roundtrip() -> None:
    p = Position(
        ticker="KXHIGHNY-26APR18-T75",
        side="yes",
        quantity=10,
        avg_entry_cents=42,
        realized_pnl_cents=0,
        unrealized_pnl_cents=80,
        total_fees_cents=5,
        settled=False,
    )
    _roundtrip(p)


def test_position_unrealized_none_roundtrip() -> None:
    p = Position(
        ticker="KXHIGHNY-26APR18-T75",
        side="no",
        quantity=0,
        avg_entry_cents=0,
        realized_pnl_cents=-150,
        unrealized_pnl_cents=None,
        total_fees_cents=10,
        settled=True,
    )
    _roundtrip(p)


def test_balance_roundtrip() -> None:
    b = Balance(
        strategy_id="bracket-arb-v1-all",
        starting_cents=100_000,
        available_cents=99_000,
        reserved_cents=500,
        total_invested_cents=500,
        total_fees_cents=10,
        realized_pnl_cents=0,
        unrealized_pnl_cents=20,
        total_pnl_cents=20,
    )
    _roundtrip(b)


def test_order_intent_roundtrip() -> None:
    oi = OrderIntent(
        ticker="KXHIGHNY-26APR18-T75",
        side="yes",
        action="buy",
        price_cents=42,
        quantity=10,
        client_order_id="strat-42",
        edge_cents=3,
    )
    _roundtrip(oi)


def test_order_intent_rejects_price_out_of_range() -> None:
    with pytest.raises(ValidationError):
        OrderIntent(
            ticker="KXHIGHNY-26APR18-T75",
            side="yes",
            action="buy",
            price_cents=100,
            quantity=1,
        )
    with pytest.raises(ValidationError):
        OrderIntent(
            ticker="KXHIGHNY-26APR18-T75",
            side="yes",
            action="buy",
            price_cents=0,
            quantity=1,
        )


def test_order_intent_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        OrderIntent(
            ticker="KXHIGHNY-26APR18-T75",
            side="yes",
            action="buy",
            price_cents=42,
            quantity=0,
        )


def test_order_roundtrip() -> None:
    o = Order(
        id="ord-1",
        client_order_id="strat-42",
        kalshi_order_id=None,
        strategy_id="bracket-arb-v1-all",
        ticker="KXHIGHNY-26APR18-T75",
        side="yes",
        action="buy",
        price_cents=42,
        quantity=10,
        filled_quantity=0,
        avg_fill_price_cents=None,
        fees_cents=0,
        status="resting",
        time_in_force="good_till_canceled",
        created_at=NOW,
        updated_at=NOW,
    )
    _roundtrip(o)


def test_fill_roundtrip() -> None:
    f = Fill(
        id="fill-1",
        order_id="ord-1",
        strategy_id="bracket-arb-v1-all",
        ticker="KXHIGHNY-26APR18-T75",
        side="yes",
        action="buy",
        price_cents=42,
        quantity=10,
        is_taker=True,
        fees_cents=5,
        best_bid_cents_at_fill=41,
        best_ask_cents_at_fill=42,
        orderbook_snapshot_hash="deadbeef",
        is_settlement=False,
        created_at=NOW,
    )
    _roundtrip(f)


def test_settlement_roundtrip() -> None:
    s = Settlement(
        ticker="KXHIGHNY-26APR18-T75",
        event_ticker="KXHIGHNY-26APR18",
        result="yes",
        yes_payout_cents=100,
        no_payout_cents=0,
        settled_at=NOW,
    )
    _roundtrip(s)


def test_order_ack_roundtrip() -> None:
    a = OrderAck(
        order_id="ord-1",
        client_order_id="strat-42",
        status="acked",
        reject_reason=None,
    )
    _roundtrip(a)


def test_cancel_ack_roundtrip() -> None:
    c = CancelAck(order_id="ord-1", status="canceled")
    _roundtrip(c)


def test_frozen_rejects_mutation() -> None:
    c = CancelAck(order_id="ord-1", status="canceled")
    with pytest.raises(ValidationError):
        c.order_id = "ord-2"  # type: ignore[misc]


def test_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        OrderbookLevel.model_validate({"price_cents": 42, "size": 100, "extra": "nope"})
