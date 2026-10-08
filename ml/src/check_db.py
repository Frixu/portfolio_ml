"""Sprawdza, czy baza danych z docker-compose działa i przyjmuje połączenia."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

url = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(url)
with engine.connect() as conn:
    version = conn.execute(text("SELECT version()")).scalar()
    print("Połączenie działa:", version)