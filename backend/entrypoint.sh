#!/usr/bin/env bash
# API container entrypoint: wait for Postgres, run migrations, seed, then serve (§9.1).
set -euo pipefail

echo "[entrypoint] Waiting for database..."
python - <<'PY'
import time
import sqlalchemy
from app.core.config import settings

engine = sqlalchemy.create_engine(settings.database_url)
for attempt in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        print("[entrypoint] Database is ready.")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] DB not ready ({attempt+1}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] Database never became ready")
PY

echo "[entrypoint] Running migrations..."
alembic upgrade head

echo "[entrypoint] Seeding (bucket + demo attorney)..."
python -m app.seed

echo "[entrypoint] Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
