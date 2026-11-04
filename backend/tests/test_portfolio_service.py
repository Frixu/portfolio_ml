"""Testy jednostkowe logiki portfela - bez bazy danych i bez HTTP."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.portfolio import InsufficientSharesError, compute_positions


def tx(side, quantity, price, fee=0, day="2026-01-15", ticker="PKO"):
    """Pomocnik: tworzy transakcję w formie wymaganej przez compute_positions."""
    return SimpleNamespace(
        ticker=ticker, side=side,
        quantity=Decimal(str(quantity)), price=Decimal(str(price)), fee=Decimal(str(fee)),
        trade_date=date.fromisoformat(day),
    )


def test_average_cost_includes_fees():
    positions = compute_positions([
        tx("BUY", 10, 100, fee=5, day="2026-01-15"),
        tx("BUY", 10, 120, fee=5, day="2026-03-10"),
    ])
    assert positions["PKO"].quantity == 20
    assert positions["PKO"].avg_cost == Decimal("110.5")


def test_sell_realizes_profit_and_keeps_average_cost():
    pos = compute_positions([
        tx("BUY", 10, 100, fee=5, day="2026-01-15"),
        tx("BUY", 10, 120, fee=5, day="2026-03-10"),
        tx("SELL", 5, 130, fee=5, day="2026-06-01"),
    ])["PKO"]
    assert pos.quantity == 15
    assert pos.avg_cost == Decimal("110.5")
    assert pos.realized_pnl == Decimal("92.5")


def test_selling_everything_closes_position():
    pos = compute_positions([
        tx("BUY", 10, 100, day="2026-01-15"),
        tx("SELL", 10, 90, day="2026-02-01"),
    ])["PKO"]
    assert pos.quantity == 0
    assert pos.cost == 0
    assert pos.realized_pnl == Decimal("-100")


def test_cannot_sell_more_than_held():
    with pytest.raises(InsufficientSharesError):
        compute_positions([
            tx("BUY", 10, 100, day="2026-01-15"),
            tx("SELL", 11, 100, day="2026-02-01"),
        ])


def test_backdated_sell_before_purchase_is_rejected():
    with pytest.raises(InsufficientSharesError):
        compute_positions([
            tx("BUY", 10, 100, day="2026-01-15"),
            tx("SELL", 1, 100, day="2026-01-01"),
        ])


def test_same_day_buy_is_processed_before_sell():
    pos = compute_positions([
        tx("SELL", 5, 110, day="2026-01-15"),  # podana pierwsza, ale tego samego dnia co zakup
        tx("BUY", 10, 100, day="2026-01-15"),
    ])["PKO"]
    assert pos.quantity == 5


def test_positions_are_tracked_separately_per_ticker():
    positions = compute_positions([
        tx("BUY", 10, 100, ticker="PKO"),
        tx("BUY", 3, 70, ticker="PZU"),
    ])
    assert positions["PKO"].quantity == 10
    assert positions["PZU"].quantity == 3