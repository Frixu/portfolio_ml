"""Cechy i etykieta modelu - jedno źródło prawdy dla notatników, treningu i oceniania."""
import numpy as np
import pandas as pd
from sqlalchemy import Engine

FEATURES = ["mom_1m", "mom_3m", "mom_6m", "mom_12m", "vol_3m", "dist_high_12m", "liquidity_3m"]
MIN_TURNOVER = 100_000  # minimalny średni dzienny obrót w zł (filtr płynności)


def load_prices(engine: Engine) -> pd.DataFrame:
    prices = pd.read_sql(
        "SELECT ticker, date, close, volume FROM prices ORDER BY ticker, date",
        engine,
        parse_dates=["date"],
    )
    prices["close"] = prices["close"].astype(float)  # NUMERIC przychodzi jako Decimal
    return prices


def build_dataset(engine: Engine) -> pd.DataFrame:
    """Zbiór w formacie (data, spółka) z cechami, przyszłym zwrotem i etykietą.

    Cechy w danym miesiącu korzystają wyłącznie z danych do jego końca;
    etykieta i fwd_ret dotyczą miesiąca następnego.
    """
    prices = load_prices(engine)
    close = prices.pivot(index="date", columns="ticker", values="close")
    turnover = prices.assign(t=prices["close"] * prices["volume"]).pivot(
        index="date", columns="ticker", values="t"
    )

    # Ceny na koniec miesiąca; bieżący, niepełny miesiąc pomijamy
    monthly_close = close.resample("ME").last()
    if close.index.max() < monthly_close.index[-1] - pd.Timedelta(days=4):
        monthly_close = monthly_close.iloc[:-1]

    daily_ret = close / close.shift(1) - 1

    def at_month_end(df: pd.DataFrame) -> pd.DataFrame:
        return df.resample("ME").last().reindex(monthly_close.index)

    features = {
        "mom_1m": monthly_close / monthly_close.shift(1) - 1,
        "mom_3m": monthly_close / monthly_close.shift(3) - 1,
        "mom_6m": monthly_close / monthly_close.shift(6) - 1,
        "mom_12m": monthly_close / monthly_close.shift(12) - 1,
        "vol_3m": at_month_end(daily_ret.rolling(63, min_periods=50).std() * np.sqrt(252)),
        "dist_high_12m": at_month_end(close / close.rolling(252, min_periods=200).max() - 1),
        "liquidity_3m": at_month_end(np.log(turnover.rolling(63, min_periods=50).mean())),
    }

    # Etykieta: czy zwrot w następnym miesiącu przekroczył medianę płynnego uniwersum
    investable = features["liquidity_3m"] >= np.log(MIN_TURNOVER)
    fwd_ret = (monthly_close.shift(-1) / monthly_close - 1).where(investable)
    label = fwd_ret.gt(fwd_ret.median(axis=1), axis=0).astype(float).where(fwd_ret.notna())

    dataset = pd.concat({name: f.stack() for name, f in features.items()}, axis=1)
    dataset["fwd_ret"] = fwd_ret.stack()
    dataset["label"] = label.stack()
    dataset.index.names = ["date", "ticker"]
    return dataset


def training_rows(dataset: pd.DataFrame) -> pd.DataFrame:
    """Wiersze z kompletem cech i znaną etykietą - do treningu."""
    return dataset.dropna(subset=FEATURES + ["label"])


def scoring_rows(dataset: pd.DataFrame) -> tuple[pd.Timestamp, pd.DataFrame]:
    """Ostatni pełny miesiąc, płynne spółki z kompletem cech - do oceny modelem."""
    last_month = dataset.index.get_level_values("date").max()
    rows = dataset.xs(last_month, level="date").dropna(subset=FEATURES)
    return last_month, rows[rows["liquidity_3m"] >= np.log(MIN_TURNOVER)]

def cross_sectional_rank(X: pd.DataFrame) -> pd.DataFrame:
    """Zamienia cechy na rangi w obrębie miesiąca, przeskalowane liniowo do [-1, 1].

    -1 = najniższa wartość w miesiącu, 1 = najwyższa (Gu, Kelly, Xiu, 2020).
    Usuwa trendy w czasie (np. rosnące obroty na GPW) i wpływ wartości skrajnych.
    """
    if "date" in X.index.names:
        grouped = X[FEATURES].groupby(level="date")
        rank, count = grouped.rank(), grouped.transform("count")
    else:  # pojedynczy miesiąc - zbiór do oceny
        rank, count = X[FEATURES].rank(), X[FEATURES].count()
    return 2 * (rank - 1) / (count - 1) - 1