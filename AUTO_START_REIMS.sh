#!/bin/bash

# REIMS2 Automatic Startup Script
# This script will start all REIMS2 services and handle any issues
# Run this with: bash AUTO_START_REIMS.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  REIMS2 Automatic Service Startup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Navigate to REIMS2 directory
cd /home/hsthind/Documents/GitHub/REIMS2

echo -e "${YELLOW}[1/6] Checking Docker availability...${NC}"

# Test Docker access
if docker ps > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker is accessible${NC}"
    DOCKER_CMD="docker"
elif sudo docker ps > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Docker requires sudo (will use sudo for commands)${NC}"
    DOCKER_CMD="sudo docker"
else
    echo -e "${RED}✗ Docker is not accessible${NC}"
    echo -e "${YELLOW}Please ensure Docker Desktop is running${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[2/6] Stopping any existing REIMS2 services...${NC}"
$DOCKER_CMD compose down 2>/dev/null || true
echo -e "${GREEN}✓ Existing services stopped${NC}"

echo ""
echo -e "${YELLOW}[3/6] Starting REIMS2 services...${NC}"
$DOCKER_CMD compose up -d

echo ""
echo -e "${YELLOW}[4/6] Waiting for services to initialize (90 seconds)...${NC}"
for i in {1..90}; do
    echo -n "."
    sleep 1
done
echo ""
echo -e "${GREEN}✓ Initialization period complete${NC}"

echo ""
echo -e "${YELLOW}[5/6] Checking service status...${NC}"
$DOCKER_CMD compose ps

echo ""
echo -e "${YELLOW}[6/6] Running health checks...${NC}"

# Backend health check
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend API: Running (http://localhost:8000)${NC}"
else
    echo -e "${YELLOW}⚠ Backend API: Not ready yet (may need more time)${NC}"
fi

# Frontend health check
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Frontend: Running (http://localhost:5173)${NC}"
else
    echo -e "${YELLOW}⚠ Frontend: Not ready yet (may need more time)${NC}"
fi

# Flower health check
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5555 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Celery Monitor: Running (http://localhost:5555)${NC}"
else
    echo -e "${YELLOW}⚠ Celery Monitor: Not ready yet${NC}"
fi

# MinIO health check
if curl -s -o /dev/null -w "%{http_code}" http://localhost:9001 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ MinIO Console: Running (http://localhost:9001)${NC}"
else
    echo -e "${YELLOW}⚠ MinIO Console: Not ready yet${NC}"
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Access URLs${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${CYAN}Frontend:${NC}       http://localhost:5173"
echo -e "${CYAN}API Docs:${NC}       http://localhost:8000/docs"
echo -e "${CYAN}Celery Monitor:${NC} http://localhost:5555"
echo -e "${CYAN}MinIO Console:${NC}  http://localhost:9001"
echo -e "${CYAN}pgAdmin:${NC}        http://localhost:5050"
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Login Credentials${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${CYAN}REIMS2 Frontend:${NC}"
echo "  Username: admin"
echo "  Password: Admin123!"
echo ""
echo -e "${CYAN}MinIO Console:${NC}"
echo "  Username: minioadmin"
echo "  Password: minioadmin"
echo ""
echo -e "${CYAN}pgAdmin:${NC}"
echo "  Email: admin@pgadmin.com"
echo "  Password: admin"
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✓ REIMS2 services are starting!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View all logs:       $DOCKER_CMD compose logs -f"
echo "  Check status:        $DOCKER_CMD compose ps"
echo "  Stop services:       $DOCKER_CMD compose down"
echo "  Restart service:     $DOCKER_CMD compose restart <service>"
echo ""
echo -e "${CYAN}If services aren't ready yet, wait 2-3 more minutes.${NC}"
echo -e "${CYAN}For first-time startup, Docker needs to download images.${NC}"
echo ""
