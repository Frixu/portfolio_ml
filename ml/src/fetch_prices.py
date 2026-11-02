"""Pobiera dzienne notowania spółek z uniwersum i zapisuje je w tabeli prices."""
import os
import time
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

# yfinance używa składni, którą nowy pandas oznacza jako przestarzałą - wyciszamy tylko to
warnings.filterwarnings("ignore", message=".*inplace keyword.*")

UNIVERSE_FILE = Path(__file__).resolve().parents[1] / "config" / "universe.csv"
START = "2010-01-01"


def get_engine():
    load_dotenv()
    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url)


def fetch(ticker: str) -> pd.DataFrame:
    df = yf.download(f"{ticker}.WA", start=START, auto_adjust=True, progress=False)
    if df.empty:
        return df
    # yfinance czasem zwraca kolumny dwupoziomowe (cena, ticker) - spłaszczamy
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index().rename(columns=str.lower)
    df["ticker"] = ticker
    df["date"] = df["date"].dt.date
    df["volume"] = df["volume"].fillna(0).astype("int64")
    df = df.dropna(subset=["close"])
    # Yahoo wstawia dni świąteczne (GPW zamknięta) jako wiersze z zerowym wolumenem
    df = df[df["volume"] > 0]
    return df[["ticker", "date", "open", "high", "low", "close", "volume"]]


def save(engine, df: pd.DataFrame) -> None:
    sql = text("""
        INSERT INTO prices (ticker, date, open, high, low, close, volume)
        VALUES (:ticker, :date, :open, :high, :low, :close, :volume)
        ON CONFLICT (ticker, date) DO UPDATE SET
            open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
            close = EXCLUDED.close, volume = EXCLUDED.volume
    """)
    with engine.begin() as conn:
        conn.execute(sql, df.to_dict("records"))


def main() -> None:
    engine = get_engine()
    tickers = pd.read_csv(UNIVERSE_FILE)["ticker"].tolist()
    print(f"Uniwersum: {len(tickers)} spółek z {UNIVERSE_FILE.name}")
    missing = []
    for ticker in tickers:
        df = fetch(ticker)
        if df.empty:
            print(f"{ticker}: brak danych")
            missing.append(ticker)
            continue
        save(engine, df)
        print(f"{ticker}: {len(df)} dni, od {df['date'].min()} do {df['date'].max()}")
        time.sleep(1)  # żeby nie przeciążać serwera Yahoo
    print(f"\nGotowe. Brak danych dla {len(missing)} spółek: {', '.join(missing) or '-'}")


if __name__ == "__main__":
    main()