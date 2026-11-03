"""Połączenie z bazą danych i sesja dla każdego zapytania HTTP."""
from collections.abc import Iterator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    URL.create(
        drivername="postgresql+psycopg",
        username=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )
)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """Daje sesję na czas jednego zapytania i zawsze ją zamyka."""
    with SessionLocal() as session:
        yield session