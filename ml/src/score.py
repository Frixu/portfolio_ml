"""Trenuje model na całej historii i zapisuje oceny ostatniego pełnego miesiąca do model_scores.

Model produkcyjny: regresja logistyczna na cechach w postaci rang miesięcznych
(wybrana na podstawie walidacji walk-forward - patrz notatnik 02_model).
Uruchamiany raz w miesiącu, po pobraniu notowań (fetch_prices.py).
"""
import json

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import QuantileTransformer
from sqlalchemy import Engine, text

from db import get_engine
from features import FEATURES, build_dataset, cross_sectional_rank, scoring_rows, training_rows

MODEL_VERSION = "logreg-rank-v2"


def make_model() -> LogisticRegression:
    # Cechy są już rangami w [-1, 1], więc nie wymagają dodatkowego skalowania
    return LogisticRegression(max_iter=1000)


def shap_contributions(model: LogisticRegression, X_train: pd.DataFrame, X: pd.DataFrame) -> pd.DataFrame:
    """Wartości SHAP modelu liniowego: współczynnik × (cecha − średnia cechy w zbiorze treningowym)."""
    return model.coef_[0] * (X - X_train.mean())


def save_scores(engine: Engine, month: pd.Timestamp, raw: pd.DataFrame, ranks: pd.DataFrame,
                scores: pd.Series, contributions: pd.DataFrame) -> None:
    rows = [
        {
            "date": month.date(),
            "ticker": ticker,
            "version": MODEL_VERSION,
            "score": round(float(scores[ticker]), 5),
            "explanation": json.dumps({
                "features": raw.loc[ticker, FEATURES].round(4).to_dict(),     # wartości do wyświetlenia
                "percentiles": ((ranks.loc[ticker] + 1) / 2).round(3).to_dict(),  # 0 = najgorsza, 1 = najlepsza       # pozycja względem innych spółek
                "contributions": contributions.loc[ticker].round(4).to_dict(),  # wpływ na ocenę (SHAP)
            }),
        }
        for ticker in ranks.index
    ]
    sql = text("""
        INSERT INTO model_scores (date, ticker, model_version, score, explanation)
        VALUES (:date, :ticker, :version, :score, CAST(:explanation AS jsonb))
        ON CONFLICT (date, ticker, model_version) DO UPDATE SET
            score = EXCLUDED.score, explanation = EXCLUDED.explanation, created_at = now()
    """)
    with engine.begin() as conn:
        conn.execute(sql, rows)


def main() -> None:
    engine = get_engine()
    dataset = build_dataset(engine)
    train = training_rows(dataset)
    month, to_score = scoring_rows(dataset)

    X_train, y_train = cross_sectional_rank(train), train["label"]
    X = cross_sectional_rank(to_score)

    print(f"Model: {MODEL_VERSION}")
    print(f"Trening: {len(train)} przykładów, "
          f"{train.index.get_level_values('date').min().date()} - "
          f"{train.index.get_level_values('date').max().date()}")
    print(f"Ocena: {len(X)} spółek, stan na {month.date()}")

    model = make_model().fit(X_train, y_train)
    scores = pd.Series(model.predict_proba(X)[:, 1], index=X.index)
    contributions = shap_contributions(model, X_train, X)
    save_scores(engine, month, to_score, X, scores, contributions)

    print("\nWspółczynniki modelu:")
    print(pd.Series(model.coef_[0], index=FEATURES).sort_values().round(3).to_string())

    print("\nTop 10 spółek i dwa najważniejsze powody:")
    for ticker in scores.sort_values(ascending=False).head(10).index:
        reasons = contributions.loc[ticker].sort_values(ascending=False).head(2)
        reasons_txt = ", ".join(f"{name} ({value:+.2f})" for name, value in reasons.items())
        print(f"  {ticker:4} {scores[ticker]:.3f}   {reasons_txt}")


if __name__ == "__main__":
    main()