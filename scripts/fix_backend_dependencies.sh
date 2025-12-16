#!/bin/bash
# Quick fix script for backend dependencies
# Use this when services are running but need dependency fixes

echo "🔧 Applying backend dependency fixes..."

# Install missing structlog
docker exec -u root reims-backend pip install structlog==22.3.0

# Create log directory with proper permissions
docker exec -u root reims-backend mkdir -p /var/log/reims2
docker exec -u root reims-backend chown -R appuser:appgroup /var/log/reims2

# Restart backend
echo "🔄 Restarting backend..."
docker compose restart backend

# Wait and check health
sleep 5
echo "🏥 Checking backend health..."
curl -s http://localhost:8000/api/v1/health && echo ""

echo "✅ Fixes applied!"

