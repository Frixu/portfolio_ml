"""Testy integracyjne API - prawdziwe zapytania HTTP na bazie testowej."""
from datetime import date, timedelta

import pytest

import json

from sqlalchemy import text

from app.config import settings


def buy(quantity, price, fee=5, day="2026-01-15", ticker="PKO"):
    return {"ticker": ticker, "side": "BUY", "quantity": quantity, "price": price,
            "fee": fee, "trade_date": day}


def sell(quantity, price, fee=5, day="2026-06-01", ticker="PKO"):
    return {**buy(quantity, price, fee, day, ticker), "side": "SELL"}


# --- System i spółki ---

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_instruments_have_latest_price(client):
    instruments = {i["ticker"]: i for i in client.get("/instruments").json()}
    assert instruments["PKO"]["last_close"] == pytest.approx(112.30)
    assert instruments["PKO"]["change_1d"] == pytest.approx(112.30 / 110 - 1, abs=1e-4)


def test_unknown_instrument_prices_return_404(client):
    assert client.get("/instruments/XYZ/prices").status_code == 404


# --- Uwierzytelnianie ---

def test_register_returns_user_without_password(client):
    response = client.post("/auth/register", json={"email": "a@example.com", "password": "haslo1234"})
    assert response.status_code == 201
    assert "password" not in response.text
    assert response.json()["risk_profile"] == "balanced"


def test_register_duplicate_email_returns_409(client):
    data = {"email": "a@example.com", "password": "haslo1234"}
    client.post("/auth/register", json=data)
    assert client.post("/auth/register", json=data).status_code == 409


def test_register_rejects_short_password(client):
    response = client.post("/auth/register", json={"email": "a@example.com", "password": "abc"})
    assert response.status_code == 422


def test_login_with_wrong_password_returns_401(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "haslo1234"})
    response = client.post("/auth/login", data={"username": "a@example.com", "password": "zle-haslo"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_logged_in_user(client, login):
    headers = login("ja@example.com")
    assert client.get("/auth/me", headers=headers).json()["email"] == "ja@example.com"


# --- Portfele i transakcje ---

def test_full_portfolio_scenario(client, login):
    headers = login()
    portfolio_id = client.post("/portfolios", json={"name": "Mój portfel"}, headers=headers).json()["id"]
    url = f"/portfolios/{portfolio_id}/transactions"

    assert client.post(url, json=buy(10, 100, day="2026-01-15"), headers=headers).status_code == 201
    assert client.post(url, json=buy(10, 120, day="2026-03-10"), headers=headers).status_code == 201
    assert client.post(url, json=sell(5, 130, day="2026-06-01"), headers=headers).status_code == 201

    detail = client.get(f"/portfolios/{portfolio_id}", headers=headers).json()
    holding = detail["holdings"][0]
    assert holding["quantity"] == 15
    assert holding["avg_cost"] == pytest.approx(110.5)
    assert holding["market_value"] == pytest.approx(15 * 112.30)
    assert holding["weight"] == pytest.approx(1.0)
    assert detail["realized_pnl"] == pytest.approx(92.5)
    assert detail["unrealized_pnl"] == pytest.approx(15 * 112.30 - 15 * 110.5)


def test_ticker_is_normalized_to_uppercase(client, login):
    headers = login()
    portfolio_id = client.post("/portfolios", json={"name": "P"}, headers=headers).json()["id"]
    response = client.post(f"/portfolios/{portfolio_id}/transactions",
                           json=buy(1, 100, ticker=" pko "), headers=headers)
    assert response.json()["ticker"] == "PKO"


@pytest.mark.parametrize("transaction", [
    sell(1, 100),                                     # sprzedaż bez posiadanych akcji
    buy(1, 100, ticker="XYZ"),                        # nieznana spółka
    buy(0, 100),                                      # zerowa ilość
    buy(1, -5),                                       # ujemna cena
    buy(1, 100, day=str(date.today() + timedelta(days=1))),  # data z przyszłości
])
def test_invalid_transactions_return_422(client, login, transaction):
    headers = login()
    portfolio_id = client.post("/portfolios", json={"name": "P"}, headers=headers).json()["id"]
    response = client.post(f"/portfolios/{portfolio_id}/transactions", json=transaction, headers=headers)
    assert response.status_code == 422


def test_duplicate_portfolio_name_returns_409(client, login):
    headers = login()
    client.post("/portfolios", json={"name": "P"}, headers=headers)
    assert client.post("/portfolios", json={"name": "P"}, headers=headers).status_code == 409


def test_user_cannot_access_other_users_portfolio(client, login):
    owner = login("wlasciciel@example.com")
    portfolio_id = client.post("/portfolios", json={"name": "P"}, headers=owner).json()["id"]

    intruder = login("intruz@example.com")
    assert client.get("/portfolios", headers=intruder).json() == []
    assert client.get(f"/portfolios/{portfolio_id}", headers=intruder).status_code == 404
    response = client.post(f"/portfolios/{portfolio_id}/transactions", json=buy(1, 100), headers=intruder)
    assert response.status_code == 404

# --- Rekomendacje ---

FEATURES = ["mom_1m", "mom_3m", "mom_6m", "mom_12m", "vol_3m", "dist_high_12m", "liquidity_3m"]


def insert_scores(engine, scores):
    """Wstawia oceny modelu do bazy testowej (zamiast uruchamiania score.py)."""
    explanation = json.dumps({
        "features": {f: 0.1 for f in FEATURES} | {"liquidity_3m": 15.0},
        "percentiles": {f: 0.5 for f in FEATURES},
        "contributions": {f: 0.0 for f in FEATURES} | {"mom_12m": 0.1},
    })
    with engine.begin() as conn:
        for ticker, score in scores.items():
            conn.execute(
                text("INSERT INTO model_scores (date, ticker, model_version, score, explanation) "
                     "VALUES ('2026-10-31', :t, :v, :s, CAST(:e AS jsonb))"),
                {"t": ticker, "v": settings.model_version, "s": score, "e": explanation},
            )


def test_recommendations_without_model_scores_are_empty(client, login):
    headers = login()
    portfolio_id = client.post("/portfolios", json={"name": "P"}, headers=headers).json()["id"]
    response = client.get(f"/portfolios/{portfolio_id}/recommendations", headers=headers)
    assert response.status_code == 200
    assert response.json()["recommendations"] == []
    assert response.json()["scores_date"] is None


def test_recommendations_for_empty_portfolio_propose_best_stock(client, login, db_engine):
    insert_scores(db_engine, {"PKO": 0.60, "PZU": 0.40})
    headers = login()
    portfolio_id = client.post("/portfolios", json={"name": "P"}, headers=headers).json()["id"]

    body = client.get(f"/portfolios/{portfolio_id}/recommendations", headers=headers).json()
    assert body["scores_date"] == "2026-10-31"
    assert body["recommendations"][0]["ticker"] == "PKO"
    assert body["recommendations"][0]["action"] == "ADD"
    assert body["disclaimer"]


def test_recommendations_flag_oversized_position(client, login, db_engine):
    insert_scores(db_engine, {"PKO": 0.60, "PZU": 0.40})
    headers = login()
    portfolio_id = client.post("/portfolios", json={"name": "P"}, headers=headers).json()["id"]
    client.post(f"/portfolios/{portfolio_id}/transactions", json=buy(10, 100), headers=headers)

    recs = client.get(f"/portfolios/{portfolio_id}/recommendations", headers=headers).json()["recommendations"]
    pko = next(r for r in recs if r["ticker"] == "PKO")
    assert pko["action"] == "REDUCE"  # 100% portfela w jednej spółce


def test_user_can_change_risk_profile(client, login):
    headers = login()
    response = client.patch("/auth/me", json={"risk_profile": "conservative"}, headers=headers)
    assert response.status_code == 200
    assert client.get("/auth/me", headers=headers).json()["risk_profile"] == "conservative"


def test_other_user_cannot_get_recommendations(client, login):
    owner = login("wlasciciel@example.com")
    portfolio_id = client.post("/portfolios", json={"name": "P"}, headers=owner).json()["id"]
    intruder = login("intruz@example.com")
    assert client.get(f"/portfolios/{portfolio_id}/recommendations", headers=intruder).status_code == 404