"""Logika portfela: odtwarzanie pozycji z historii transakcji.

Moduł nie zależy od bazy danych ani od HTTP - działa na dowolnych obiektach
z polami ticker, side, quantity, price, fee, trade_date, dzięki czemu
łatwo go testować.
"""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal


class InsufficientSharesError(ValueError):
    """Próba sprzedaży większej liczby akcji, niż było w portfelu."""


@dataclass
class Position:
    quantity: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")          # koszt nabycia posiadanych akcji, z prowizjami
    realized_pnl: Decimal = Decimal("0")  # zrealizowany zysk/strata ze sprzedaży

    @property
    def avg_cost(self) -> Decimal:
        return self.cost / self.quantity if self.quantity else Decimal("0")


def compute_positions(transactions) -> dict[str, Position]:
    """Odtwarza pozycje metodą średniego kosztu nabycia.

    Transakcje są przetwarzane chronologicznie; w ramach jednego dnia
    zakupy przed sprzedażami.
    """
    positions: dict[str, Position] = defaultdict(Position)
    ordered = sorted(transactions, key=lambda t: (t.trade_date, 0 if t.side == "BUY" else 1))

    for t in ordered:
        pos = positions[t.ticker]
        if t.side == "BUY":
            pos.quantity += t.quantity
            pos.cost += t.quantity * t.price + t.fee
        else:
            if t.quantity > pos.quantity:
                raise InsufficientSharesError(
                    f"{t.ticker}: sprzedaż {t.quantity} akcji w dniu {t.trade_date}, "
                    f"a w portfelu jest ich {pos.quantity}"
                )
            sold_cost = pos.avg_cost * t.quantity
            pos.realized_pnl += t.quantity * t.price - t.fee - sold_cost
            pos.cost -= sold_cost
            pos.quantity -= t.quantity

    return dict(positions)