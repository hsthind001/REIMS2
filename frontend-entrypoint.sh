#!/bin/sh
set -e

echo "🚀 REIMS Frontend Starting..."

# Clear Vite cache to prevent module resolution issues
if [ -d "/app/node_modules/.vite" ]; then
  echo "🧹 Clearing Vite cache..."
  rm -rf /app/node_modules/.vite
  echo "✅ Vite cache cleared"
else
  echo "ℹ️  No Vite cache to clear"
fi

# Check if backend is reachable (optional health check)
echo "⏳ Waiting for backend to be ready..."
BACKEND_URL=${VITE_API_URL:-http://localhost:8000}
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if wget -q --spider "${BACKEND_URL}/api/v1/health" 2>/dev/null; then
    echo "✅ Backend is ready!"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "⏳ Waiting for backend... (${RETRY_COUNT}/${MAX_RETRIES})"
  sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "⚠️  Backend not responding, starting anyway..."
fi

# Start Vite dev server
echo "🎯 Starting Vite dev server..."
exec "$@"



