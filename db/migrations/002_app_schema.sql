-- Spółki dostępne w aplikacji (uniwersum modelu)
CREATE TABLE IF NOT EXISTS instruments (
    ticker      VARCHAR(10)  PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    index_name  VARCHAR(20)  NOT NULL
);

-- Użytkownicy; hasło przechowujemy wyłącznie jako hash
CREATE TABLE IF NOT EXISTS users (
    id             SERIAL       PRIMARY KEY,
    email          VARCHAR(255) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    risk_profile   VARCHAR(20)  NOT NULL DEFAULT 'balanced'
                   CHECK (risk_profile IN ('conservative', 'balanced', 'dynamic')),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Portfele; jeden użytkownik może mieć kilka, ale o różnych nazwach
CREATE TABLE IF NOT EXISTS portfolios (
    id          SERIAL       PRIMARY KEY,
    user_id     INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

-- Historia transakcji; stan portfela jest z niej wyliczany
CREATE TABLE IF NOT EXISTS transactions (
    id            SERIAL         PRIMARY KEY,
    portfolio_id  INTEGER        NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    ticker        VARCHAR(10)    NOT NULL REFERENCES instruments(ticker),
    side          VARCHAR(4)     NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity      NUMERIC(14, 4) NOT NULL CHECK (quantity > 0),
    price         NUMERIC(12, 4) NOT NULL CHECK (price > 0),
    fee           NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (fee >= 0),
    trade_date    DATE           NOT NULL,
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON transactions(portfolio_id);

-- Oceny modelu: jedna na spółkę, miesiąc i wersję modelu
CREATE TABLE IF NOT EXISTS model_scores (
    date           DATE         NOT NULL,
    ticker         VARCHAR(10)  NOT NULL REFERENCES instruments(ticker),
    model_version  VARCHAR(50)  NOT NULL,
    score          NUMERIC(6, 5) NOT NULL CHECK (score BETWEEN 0 AND 1),
    explanation    JSONB,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (date, ticker, model_version)
);

-- Aktualny stan portfela: suma zakupów minus sprzedaży
CREATE OR REPLACE VIEW holdings AS
SELECT portfolio_id,
       ticker,
       SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) AS quantity
FROM transactions
GROUP BY portfolio_id, ticker
HAVING SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) > 0;