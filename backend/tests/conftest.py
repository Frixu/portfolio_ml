"""Wspólne przygotowanie testów: baza testowa, klient HTTP, logowanie."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"

test_engine = create_engine(URL.create(
    drivername="postgresql+psycopg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=f"{settings.postgres_db}_test",  # nigdy prawdziwa baza
))
TestingSession = sessionmaker(bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Raz na uruchomienie: czysta baza, wszystkie migracje i minimalne dane rynkowe."""
    with test_engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            # Usuwamy komentarze przed podziałem na polecenia - mogą zawierać średniki
            sql = "\n".join(line for line in migration.read_text().splitlines()
                            if not line.strip().startswith("--"))
            for statement in sql.split(";"):
                if statement.strip():
                    conn.exec_driver_sql(statement)

        conn.exec_driver_sql("""
            INSERT INTO instruments (ticker, name, index_name) VALUES
                ('PKO', 'PKO BP', 'WIG20'),
                ('PZU', 'PZU', 'WIG20')
        """)
        conn.exec_driver_sql("""
            INSERT INTO prices (ticker, date, close, volume) VALUES
                ('PKO', '2026-10-30', 110.00, 1000),
                ('PKO', '2026-11-02', 112.30, 1000),
                ('PZU', '2026-11-02', 72.28, 1000)
        """)
    yield

@pytest.fixture(autouse=True)
def clean_user_data():
    """Po każdym teście czyścimy dane użytkowników, żeby testy były od siebie niezależne."""
    yield
    with test_engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE users, portfolios, transactions RESTART IDENTITY CASCADE")
        conn.exec_driver_sql("TRUNCATE users, portfolios, transactions, model_scores RESTART IDENTITY CASCADE")


@pytest.fixture
def client():
    def override_get_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    """Rejestruje i loguje użytkownika; zwraca nagłówek z tokenem."""
    def _login(email="test@example.com", password="haslo1234"):
        client.post("/auth/register", json={"email": email, "password": password})
        response = client.post("/auth/login", data={"username": email, "password": password})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    return _login

@pytest.fixture
def db_engine():
    return test_engine