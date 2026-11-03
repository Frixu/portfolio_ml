"""Wspólne połączenie z bazą danych dla skryptów i notatników."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, Engine, create_engine

# .env leży w głównym katalogu projektu (dwa poziomy nad ml/src)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_engine() -> Engine:
    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url)