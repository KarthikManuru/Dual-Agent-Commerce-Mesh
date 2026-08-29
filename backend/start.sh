#!/bin/sh
set -e

echo "=== [Step 1/3] Running Database Migrations ==="
alembic upgrade head

echo "=== [Step 2/3] Seeding Initial Catalog Data ==="
python scripts/seed.py

echo "=== [Step 3/3] Starting Uvicorn Server on Port ${PORT:-8000} ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
