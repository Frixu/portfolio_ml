"""Sprawdza, czy baza danych z docker-compose działa i przyjmuje połączenia."""
import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

load_dotenv()

url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.environ["POSTGRES_DB"],
)

engine = create_engine(url)
with engine.connect() as conn:
    version = conn.execute(text("SELECT version()")).scalar()
    print("Połączenie działa:", version)