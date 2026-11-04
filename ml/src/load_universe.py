"""Synchronizuje tabelę instruments z plikiem config/universe.csv (dodaje nowe, aktualizuje istniejące)."""
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import get_engine

UNIVERSE_FILE = Path(__file__).resolve().parents[1] / "config" / "universe.csv"


def main() -> None:
    universe = pd.read_csv(UNIVERSE_FILE).rename(columns={"index": "index_name"})
    sql = text("""
        INSERT INTO instruments (ticker, name, index_name, sector)
        VALUES (:ticker, :name, :index_name, :sector)
        ON CONFLICT (ticker) DO UPDATE SET
            name = EXCLUDED.name, index_name = EXCLUDED.index_name, sector = EXCLUDED.sector
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, universe.to_dict("records"))
    print(f"Zsynchronizowano {len(universe)} spółek z {UNIVERSE_FILE.name}")
    print(universe["sector"].value_counts().to_string())


if __name__ == "__main__":
    main()