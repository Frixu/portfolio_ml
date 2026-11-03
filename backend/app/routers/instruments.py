"""Endpointy dotyczące spółek i ich notowań."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InstrumentOut, PricePoint

router = APIRouter(prefix="/instruments", tags=["Spółki"])

LIST_SQL = text("""
    SELECT i.ticker, i.name, i.index_name,
           last.date  AS last_date,
           last.close AS last_close,
           ROUND(last.close / prev.close - 1, 4) AS change_1d
    FROM instruments i
    LEFT JOIN LATERAL (
        SELECT date, close FROM prices p
        WHERE p.ticker = i.ticker ORDER BY date DESC LIMIT 1
    ) last ON true
    LEFT JOIN LATERAL (
        SELECT close FROM prices p
        WHERE p.ticker = i.ticker ORDER BY date DESC OFFSET 1 LIMIT 1
    ) prev ON true
    ORDER BY i.index_name = 'WIG20' DESC, i.ticker
""")


@router.get("", response_model=list[InstrumentOut], summary="Lista spółek z ostatnią ceną")
def list_instruments(db: Session = Depends(get_db)):
    return [dict(row) for row in db.execute(LIST_SQL).mappings()]


@router.get("/{ticker}/prices", response_model=list[PricePoint], summary="Historia cen spółki")
def get_prices(ticker: str, start: date | None = None, db: Session = Depends(get_db)):
    ticker = ticker.upper()
    if db.execute(text("SELECT 1 FROM instruments WHERE ticker = :t"), {"t": ticker}).first() is None:
        raise HTTPException(status_code=404, detail=f"Nieznana spółka: {ticker}")

    start = start or date.today() - timedelta(days=365)
    rows = db.execute(
        text("SELECT date, close FROM prices WHERE ticker = :t AND date >= :start ORDER BY date"),
        {"t": ticker, "start": start},
    ).mappings()
    return [dict(row) for row in rows]