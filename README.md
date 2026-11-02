# portfolio-ml

Praca inżynierska: **Projekt i implementacja aplikacji webowej do zarządzania portfelem inwestycyjnym z modułem rekomendacji opartym na uczeniu maszynowym.**

## Struktura

| Katalog | Zawartość |
| --- | --- |
| `ml/notebooks/` | Eksperymenty i prototyp modelu |
| `ml/src/` | Kod docelowy: pobieranie danych, cechy, trening |
| `backend/` | API w FastAPI |
| `frontend/` | Interfejs w React + TypeScript |

## Uruchomienie

1. Skopiuj plik ze zmiennymi środowiskowymi i uzupełnij hasło:

```bash
   cp .env.example .env
```

2. Uruchom bazę danych:

```bash
   docker compose up -d
```

3. Utwórz środowisko Pythona i zainstaluj zależności:

```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r ml/requirements.txt
```

4. Sprawdź połączenie z bazą:

```bash
   python ml/src/check_db.py
```