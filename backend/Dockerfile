FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Los proveedores cloud asignan el puerto mediante PORT. Las migraciones y el seed
# son idempotentes; Docker Compose reemplaza este comando durante el desarrollo local.
CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.seed_superadmin && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
