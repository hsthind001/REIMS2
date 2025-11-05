#!/bin/bash
set -e

echo "🌺 REIMS Flower Starting..."

# Wait for Redis to be ready (Flower only needs Redis, not PostgreSQL)
echo "⏳ Waiting for Redis..."
until redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Redis is ready!"

# Start Flower
echo "🎯 Starting Flower..."
exec "$@"

