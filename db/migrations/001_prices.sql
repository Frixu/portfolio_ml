CREATE TABLE IF NOT EXISTS prices (
    ticker  VARCHAR(10)    NOT NULL,
    date    DATE           NOT NULL,
    open    NUMERIC(12, 4),
    high    NUMERIC(12, 4),
    low     NUMERIC(12, 4),
    close   NUMERIC(12, 4) NOT NULL,
    volume  BIGINT,
    PRIMARY KEY (ticker, date)
);