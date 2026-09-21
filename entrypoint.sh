#!/bin/sh
set -e

echo "Running migrations..."
alembic upgrade head

echo "Seeding units..."
python -m scripts.seed_units

echo "Starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1