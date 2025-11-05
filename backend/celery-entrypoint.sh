#!/bin/bash
set -e

echo "🚀 REIMS Celery Worker Starting..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h $POSTGRES_SERVER -p $POSTGRES_PORT -U $POSTGRES_USER; do
  sleep 1
done
echo "✅ PostgreSQL is ready!"

# No migrations needed for workers - backend handles that

# Start the celery worker
echo "🎯 Starting Celery Worker..."
exec "$@"

