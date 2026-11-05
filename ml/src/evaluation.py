"""Walidacja walk-forward i backtest strategii - wspólne dla notatników."""
from collections.abc import Callable

import numpy as np
import pandas as pd

from features import FEATURES, cross_sectional_rank


def walk_forward_predictions(data: pd.DataFrame, make_model: Callable, first_test_year: int = 2016,
                             ranked: bool = True) -> pd.DataFrame:
    """Oceny modelu dla każdego roku testowego, z modelu trenowanego wyłącznie na wcześniejszych danych.

    Między treningiem a testem jest miesiąc przerwy: etykieta grudnia zależy od zwrotu w styczniu.
    Zwraca kolumny: date, ticker, score, label, fwd_ret.
    """
    X = cross_sectional_rank(data) if ranked else data[FEATURES]
    dates = data.index.get_level_values("date")
    results = []
    for year in range(first_test_year, dates.year.max() + 1):
        train = dates < pd.Timestamp(f"{year - 1}-12-01")
        test = dates.year == year
        model = make_model().fit(X[train], data.loc[train, "label"])
        score = model.predict_proba(X[test])[:, 1]
        results.append(data.loc[test, ["label", "fwd_ret"]].assign(score=score))
    return pd.concat(results).reset_index()


Selector = Callable[[pd.DataFrame], pd.Index]


def top_k(k: int) -> Selector:
    """k spółek z najwyższą oceną."""
    return lambda month: month.nlargest(k, "score").index


def top_k_per_sector(k: int, sectors: dict[str, str], per_sector: int = 2) -> Selector:
    """k spółek z najwyższą oceną, najwyżej per_sector z jednego sektora (jak w aplikacji)."""
    def select(month: pd.DataFrame) -> pd.Index:
        chosen, count = [], {}
        for ticker in month.sort_values("score", ascending=False).index:
            sector = sectors.get(ticker, "Inne")
            if count.get(sector, 0) < per_sector:
                chosen.append(ticker)
                count[sector] = count.get(sector, 0) + 1
            if len(chosen) == k:
                break
        return pd.Index(chosen)
    return select


def all_stocks(month: pd.DataFrame) -> pd.Index:
    """Wszystkie płynne spółki - portfel równych wag."""
    return month.index


def run_strategy(preds: pd.DataFrame, select: Selector, cost: float = 0.003) -> pd.DataFrame:
    """Symulacja miesięcznego rebalansowania z kosztami transakcyjnymi.

    Na koniec każdego miesiąca kupujemy wybrane spółki po równo i trzymamy je przez miesiąc.
    Koszt = cost × wartość obrotu (suma zmian wag względem portfela po zmianach cen).
    Indeks wyniku to koniec miesiąca, w którym zrealizowano zwrot.
    """
    held = pd.Series(dtype=float)  # wagi z poprzedniego miesiąca po zmianach cen
    rows = []
    for date, month in preds.groupby("date"):
        month = month.set_index("ticker")
        chosen = select(month)
        target = pd.Series(1 / len(chosen), index=chosen)

        tickers = target.index.union(held.index)
        turnover = (target.reindex(tickers, fill_value=0) - held.reindex(tickers, fill_value=0)).abs().sum()

        returns = month.loc[chosen, "fwd_ret"]
        gross = float((target * returns).sum())
        rows.append({"date": date + pd.offsets.MonthEnd(1), "gross": gross,
                     "net": gross - cost * turnover, "turnover": turnover})

        grown = target * (1 + returns)
        held = grown / grown.sum()
    return pd.DataFrame(rows).set_index("date")


def performance(returns: pd.Series) -> dict[str, float]:
    """Miary efektywności dla miesięcznych stóp zwrotu."""
    equity = (1 + returns).cumprod()
    years = len(returns) / 12
    drawdown = equity / equity.cummax().clip(lower=1) - 1
    return {
        "Roczna stopa zwrotu": equity.iloc[-1] ** (1 / years) - 1,
        "Zmienność roczna": returns.std() * np.sqrt(12),
        "Sharpe (rf = 0)": returns.mean() / returns.std() * np.sqrt(12),
        "Maks. obsunięcie": drawdown.min(),
        "Miesięcy na plusie": (returns > 0).mean(),
    }