ALTER TABLE prices
    ADD CONSTRAINT fk_prices_instrument
    FOREIGN KEY (ticker) REFERENCES instruments(ticker);