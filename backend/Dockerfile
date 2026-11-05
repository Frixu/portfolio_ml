FROM python:3.12-slim

WORKDIR /app

# Najpierw same zależności - Docker zapamięta ten krok i nie będzie
# instalował bibliotek od nowa przy każdej zmianie w kodzie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]