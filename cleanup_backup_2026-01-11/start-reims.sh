#!/bin/bash

# REIMS2 Startup Script
# Quick script to start all REIMS2 services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}       REIMS2 Service Startup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found${NC}"
    echo -e "${YELLOW}Please run this script from the REIMS2 directory:${NC}"
    echo -e "${YELLOW}cd /home/hsthind/Documents/GitHub/REIMS2${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo -e "${YELLOW}Please create a .env file first${NC}"
    exit 1
fi

# Check if Docker is accessible
if ! docker ps &> /dev/null; then
    echo -e "${RED}Error: Cannot access Docker${NC}"
    echo -e "${YELLOW}Please run: newgrp docker${NC}"
    echo -e "${YELLOW}Or log out and log back in${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is accessible${NC}"
echo ""

# Start services
echo -e "${YELLOW}Starting REIMS2 services...${NC}"
docker compose up -d

echo ""
echo -e "${YELLOW}Waiting for services to initialize (60 seconds)...${NC}"
echo -e "${YELLOW}This may take longer on first run (downloading images)${NC}"

# Progress bar
for i in {1..60}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

# Check service status
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}       Service Status${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

docker compose ps

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}       Health Checks${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check backend
echo -n "Backend API (port 8000): "
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check frontend
echo -n "Frontend (port 5173): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check Flower
echo -n "Flower Monitor (port 5555): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5555 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check MinIO
echo -n "MinIO (port 9001): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:9001 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}       Access URLs${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${GREEN}Frontend:${NC}       http://localhost:5173"
echo -e "${GREEN}API Docs:${NC}       http://localhost:8000/docs"
echo -e "${GREEN}Celery Monitor:${NC} http://localhost:5555"
echo -e "${GREEN}MinIO Console:${NC}  http://localhost:9001"
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}       Login Credentials${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${GREEN}Username:${NC} admin"
echo -e "${GREEN}Password:${NC} Admin123!"
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✓ REIMS2 is ready!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${YELLOW}To view logs:${NC} docker compose logs -f"
echo -e "${YELLOW}To stop:${NC}      docker compose down"
echo ""
