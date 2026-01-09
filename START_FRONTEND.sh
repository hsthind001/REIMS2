#!/bin/bash

# REIMS Frontend Quick Start Script
# This script installs dependencies and starts the React frontend

echo "======================================"
echo "🚀 REIMS Frontend Quick Start"
echo "======================================"
echo ""

# Navigate to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
    echo ""
else
    echo "✅ Dependencies already installed"
    echo ""
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating default .env file..."
    cat > .env << 'EOF'
# Backend API URL
REACT_APP_API_URL=http://localhost:8000

# App Configuration
REACT_APP_NAME=REIMS
REACT_APP_VERSION=1.0.0
EOF
    echo "✅ .env file created"
    echo ""
fi

echo "======================================"
echo "📍 Starting Development Server"
echo "======================================"
echo ""
echo "The app will open at: http://localhost:3000"
echo ""
echo "Available pages:"
echo "  • Dashboard (Option 1):       http://localhost:3000/"
echo "  • Property Details (Option 2): http://localhost:3000/property/ESP"
echo "  • NLQ Search:                 http://localhost:3000/nlq"
echo ""
echo "Make sure backend is running at: http://localhost:8000"
echo ""

# Start React app
npm start
