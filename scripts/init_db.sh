#!/usr/bin/env bash

set -euo pipefail

echo "==> Loading environment variables..."
if [ -f .env ]; then
    # Load .env variables, ignoring comments
    export $(grep -v '^#' .env | xargs)
fi

# Determine python and alembic commands to use
if [ -d ".venv" ]; then
    PYTHON_CMD=".venv/bin/python"
    ALEMBIC_CMD=".venv/bin/alembic"
else
    PYTHON_CMD="python3"
    ALEMBIC_CMD="alembic"
fi

# Ensure src is in PYTHONPATH so python can import src.config
export PYTHONPATH=".:${PYTHONPATH:-}"

echo "==> Waiting for PostgreSQL to be ready..."

MAX_RETRIES=30
RETRY_COUNT=0
DB_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Use python and SQLAlchemy to check if DB is accessible using project config
    if $PYTHON_CMD -c "
import sys
from sqlalchemy import create_engine
from src.config import settings

try:
    engine = create_engine(settings.sync_database_url)
    with engine.connect() as connection:
        pass
    sys.exit(0)
except Exception:
    sys.exit(1)
" >/dev/null 2>&1; then
        DB_READY=true
        break
    fi

    echo "    PostgreSQL is unavailable - sleeping 1 second (Attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ "$DB_READY" = false ]; then
    echo "❌ Error: PostgreSQL did not become ready in time."
    exit 1
fi

echo "✅ PostgreSQL is ready."
echo "==> Running Alembic migrations..."

# Run alembic migrations safely. Alembic upgrade head is idempotent.
if $ALEMBIC_CMD upgrade head; then
    echo "✅ Database initialization complete. Schema is up to date."
else
    echo "❌ Error: Failed to apply database migrations."
    exit 1
fi
