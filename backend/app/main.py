"""Punkt startowy API."""
from fastapi import FastAPI

from app.routers import auth, instruments

app = FastAPI(
    title="Portfolio ML API",
    description="API aplikacji do zarządzania portfelem inwestycyjnym z rekomendacjami ML.",
    version="0.1.0",
)

app.include_router(instruments.router)
app.include_router(auth.router)

@app.get("/health", tags=["System"], summary="Sprawdzenie, czy API działa")
def health():
    return {"status": "ok"}