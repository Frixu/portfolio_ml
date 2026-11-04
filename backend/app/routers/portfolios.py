"""Portfele użytkownika, transakcje i rekomendacje."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Instrument, Portfolio, Transaction, User
from app.schemas import (HoldingOut, PortfolioCreate, PortfolioDetail, PortfolioOut,
                         RecommendationOut, RecommendationsOut, TransactionCreate, TransactionOut)
from app.services.portfolio import InsufficientSharesError, compute_positions
from app.services.recommendations import Candidate, recommend

router = APIRouter(prefix="/portfolios", tags=["Portfele"])

MARKET_SQL = text("""
    SELECT i.ticker, i.name, i.sector, last.close AS last_close
    FROM instruments i
    LEFT JOIN LATERAL (
        SELECT close FROM prices p WHERE p.ticker = i.ticker ORDER BY date DESC LIMIT 1
    ) last ON true
    WHERE i.ticker = ANY(:tickers)
""")

SCORES_SQL = text("""
    SELECT s.ticker, i.name, i.index_name, i.sector, s.score, s.explanation, s.date,
           PERCENT_RANK() OVER (ORDER BY s.score) AS score_percentile
    FROM model_scores s
    JOIN instruments i ON i.ticker = s.ticker
    WHERE s.model_version = :version
      AND s.date = (SELECT MAX(date) FROM model_scores WHERE model_version = :version)
""")

DISCLAIMER = ("Propozycje mają charakter edukacyjny i wspomagający. Nie stanowią rekomendacji "
              "inwestycyjnej ani doradztwa inwestycyjnego w rozumieniu przepisów prawa.")

def get_own_portfolio(portfolio_id: int, user: User, db: Session) -> Portfolio:
    """Zwraca portfel, jeśli należy do użytkownika. Cudzy portfel wygląda jak nieistniejący."""
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfel nie istnieje")
    return portfolio


def get_transactions(db: Session, portfolio_id: int) -> list[Transaction]:
    return list(db.scalars(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.trade_date, Transaction.id)
    ))

def current_weights(db: Session, portfolio_id: int) -> dict[str, float]:
    """Udział każdej posiadanej spółki w bieżącej wartości portfela."""
    positions = {t: p for t, p in compute_positions(get_transactions(db, portfolio_id)).items()
                 if p.quantity > 0}
    if not positions:
        return {}
    rows = db.execute(MARKET_SQL, {"tickers": list(positions)}).mappings()
    values = {r["ticker"]: float(positions[r["ticker"]].quantity * r["last_close"])
              for r in rows if r["last_close"] is not None}
    total = sum(values.values())
    return {t: v / total for t, v in values.items()} if total else {}

@router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED,
             summary="Utworzenie portfela")
def create_portfolio(data: PortfolioCreate, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    exists = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id,
                                               Portfolio.name == data.name))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Masz już portfel o tej nazwie")
    portfolio = Portfolio(user_id=user.id, name=data.name)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.get("", response_model=list[PortfolioOut], summary="Lista moich portfeli")
def list_portfolios(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Portfolio).where(Portfolio.user_id == user.id)
                      .order_by(Portfolio.id)).all()


@router.get("/{portfolio_id}", response_model=PortfolioDetail,
            summary="Stan portfela: pozycje, wartość, zysk")
def get_portfolio(portfolio_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    portfolio = get_own_portfolio(portfolio_id, user, db)
    positions = compute_positions(get_transactions(db, portfolio.id))
    open_positions = {t: p for t, p in positions.items() if p.quantity > 0}

    market = {}
    if open_positions:
        rows = db.execute(MARKET_SQL, {"tickers": list(open_positions)}).mappings()
        market = {r["ticker"]: r for r in rows}

    holdings = []
    for ticker, pos in sorted(open_positions.items()):
        last = market[ticker]["last_close"]
        value = pos.quantity * last if last is not None else None
        holdings.append({
            "ticker": ticker,
            "name": market[ticker]["name"],
            "quantity": pos.quantity,
            "sector": market[ticker]["sector"],
            "avg_cost": pos.avg_cost,
            "cost_basis": pos.cost,
            "last_close": last,
            "market_value": value,
            "unrealized_pnl": value - pos.cost if value is not None else None,
            "unrealized_pnl_pct": value / pos.cost - 1 if value is not None and pos.cost else None,
            "weight": None,
        })

    total_value = sum((h["market_value"] for h in holdings if h["market_value"] is not None), Decimal("0"))
    total_cost = sum((h["cost_basis"] for h in holdings), Decimal("0"))
    for h in holdings:
        if h["market_value"] is not None and total_value:
            h["weight"] = h["market_value"] / total_value

    return PortfolioDetail(
        id=portfolio.id,
        name=portfolio.name,
        created_at=portfolio.created_at,
        holdings=[HoldingOut(**h) for h in holdings],
        total_value=total_value,
        total_cost=total_cost,
        unrealized_pnl=total_value - total_cost,
        realized_pnl=sum((p.realized_pnl for p in positions.values()), Decimal("0")),
    )


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionOut],
            summary="Historia transakcji portfela")
def list_transactions(portfolio_id: int, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    portfolio = get_own_portfolio(portfolio_id, user, db)
    return get_transactions(db, portfolio.id)


@router.post("/{portfolio_id}/transactions", response_model=TransactionOut,
             status_code=status.HTTP_201_CREATED, summary="Dodanie transakcji kupna lub sprzedaży")
def add_transaction(portfolio_id: int, data: TransactionCreate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    portfolio = get_own_portfolio(portfolio_id, user, db)

    if db.get(Instrument, data.ticker) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"Nieznana spółka: {data.ticker}")

    # Sprawdzamy całą historię razem z nową transakcją - także sprzedaże z datą wsteczną
    try:
        compute_positions([*get_transactions(db, portfolio.id), data])
    except InsufficientSharesError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

    transaction = Transaction(portfolio_id=portfolio.id, **data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction

@router.get("/{portfolio_id}/recommendations", response_model=RecommendationsOut,
            summary="Propozycje zmian w portfelu: ocena modelu ML + reguły profilu ryzyka")
def get_recommendations(portfolio_id: int, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    portfolio = get_own_portfolio(portfolio_id, user, db)

    rows = db.execute(SCORES_SQL, {"version": settings.model_version}).mappings().all()
    candidates = {
        r["ticker"]: Candidate(
            ticker=r["ticker"], name=r["name"], index_name=r["index_name"], sector=r["sector"],
            score=float(r["score"]), score_percentile=float(r["score_percentile"]),
            explanation=r["explanation"],
        )
        for r in rows
    }
    recs = recommend(current_weights(db, portfolio.id), candidates, user.risk_profile) if candidates else []

    return RecommendationsOut(
        model_version=settings.model_version,
        scores_date=rows[0]["date"] if rows else None,
        risk_profile=user.risk_profile,
        recommendations=[RecommendationOut.model_validate(r) for r in recs],
        disclaimer=DISCLAIMER,
    )