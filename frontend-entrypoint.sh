#!/bin/sh
set -e

echo "🚀 REIMS Frontend Starting..."

# Check for missing dependencies and install them
echo "🔍 Checking for missing dependencies..."
if [ -f "/app/package.json" ]; then
  # Check if node_modules exists and has content
  if [ ! -d "/app/node_modules" ] || [ ! "$(ls -A /app/node_modules 2>/dev/null)" ]; then
    echo "📦 node_modules missing or empty, installing dependencies..."
    npm install --prefer-offline --no-audit
    echo "✅ Dependencies installed"
  else
    # Check if package.json is newer than node_modules (indicates new dependencies)
    # Or check if package-lock.json exists and is newer
    PKG_MTIME=$(stat -c %Y /app/package.json 2>/dev/null || echo "0")
    NODE_MODULES_MTIME=$(stat -c %Y /app/node_modules 2>/dev/null || echo "0")
    LOCK_MTIME=$(stat -c %Y /app/package-lock.json 2>/dev/null || echo "0")
    
    # If package.json is newer than node_modules, or lock file is newer, reinstall
    if [ "$PKG_MTIME" -gt "$NODE_MODULES_MTIME" ] || [ "$LOCK_MTIME" -gt "$NODE_MODULES_MTIME" ]; then
      echo "📦 package.json or package-lock.json changed, updating dependencies..."
      npm install --prefer-offline --no-audit
      echo "✅ Dependencies updated"
    else
      # Quick check: verify critical packages exist (chart.js, react, etc.)
      if [ ! -d "/app/node_modules/chart.js" ] || [ ! -d "/app/node_modules/react" ]; then
        echo "📦 Critical dependencies missing, installing..."
        npm install --prefer-offline --no-audit
        echo "✅ Dependencies installed"
      else
        echo "✅ All dependencies are installed"
      fi
    fi
  fi
else
  echo "⚠️  package.json not found, skipping dependency check"
fi

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



