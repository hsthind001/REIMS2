#!/bin/bash

# REIMS Docker Fix and Startup Script
# This script fixes the Docker daemon configuration and starts REIMS services

set -e

echo "============================================"
echo "  REIMS Docker Fix & Startup"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Fix Docker daemon configuration
echo -e "${YELLOW}Step 1: Fixing Docker daemon configuration...${NC}"
echo "This requires sudo access to edit /etc/docker/daemon.json"
echo ""

# Create the corrected daemon.json content
cat > /tmp/daemon.json.fixed << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-address-pools": [
    {
      "base": "172.80.0.0/16",
      "size": 24
    }
  ],
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check"
  ],
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 10
}
EOF

echo -e "${YELLOW}Backing up current daemon.json...${NC}"
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)

echo -e "${YELLOW}Applying fixed configuration...${NC}"
sudo cp /tmp/daemon.json.fixed /etc/docker/daemon.json
sudo chmod 644 /etc/docker/daemon.json

echo -e "${GREEN}✓ Configuration fixed${NC}"
echo ""

# Step 2: Stop Docker Desktop (if running)
echo -e "${YELLOW}Step 2: Stopping Docker Desktop (if running)...${NC}"
systemctl --user stop docker-desktop 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓ Docker Desktop stopped${NC}"
echo ""

# Step 3: Restart system Docker
echo -e "${YELLOW}Step 3: Restarting system Docker service...${NC}"
sudo systemctl restart docker

# Wait for Docker to be ready
echo -e "${YELLOW}Waiting for Docker to initialize...${NC}"
for i in {1..10}; do
    if sudo docker info > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Step 4: Switch context to default
echo -e "${YELLOW}Step 4: Setting Docker context to default...${NC}"
docker context use default
echo -e "${GREEN}✓ Context set to default${NC}"
echo ""

# Step 5: Navigate to REIMS directory
echo -e "${YELLOW}Step 5: Starting REIMS services...${NC}"
cd /home/hsthind/Documents/GitHub/REIMS2

# Stop any existing containers
echo "Stopping any existing containers..."
docker compose down 2>/dev/null || true

# Start all services
echo "Starting all REIMS services..."
docker compose up -d

echo ""
echo -e "${YELLOW}Waiting for services to initialize (90 seconds)...${NC}"
echo "This may take longer on first run (downloading images)"

# Progress indicator
for i in {1..90}; do
    echo -n "."
    sleep 1
    if [ $((i % 30)) -eq 0 ]; then
        echo " ${i}s"
    fi
done
echo ""
echo ""

# Step 6: Check service status
echo "============================================"
echo "  Service Status"
echo "============================================"
echo ""

docker compose ps

echo ""
echo "============================================"
echo "  Health Checks"
echo "============================================"
echo ""

# Check backend
echo -n "Backend API (port 8000): "
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not yet responding (may need more time)${NC}"
fi

# Check frontend
echo -n "Frontend (port 5173): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not yet responding (may need more time)${NC}"
fi

# Check Flower
echo -n "Flower Monitor (port 5555): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5555 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not yet responding (may need more time)${NC}"
fi

# Check MinIO
echo -n "MinIO (port 9001): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:9001 2>&1 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not yet responding (may need more time)${NC}"
fi

echo ""
echo "============================================"
echo "  Access URLs"
echo "============================================"
echo ""
echo -e "${GREEN}Frontend:${NC}       http://localhost:5173"
echo -e "${GREEN}API Docs:${NC}       http://localhost:8000/docs"
echo -e "${GREEN}Celery Monitor:${NC} http://localhost:5555"
echo -e "${GREEN}MinIO Console:${NC}  http://localhost:9001"
echo ""
echo "============================================"
echo "  Login Credentials"
echo "============================================"
echo ""
echo -e "${GREEN}Username:${NC} admin"
echo -e "${GREEN}Password:${NC} Admin123!"
echo ""
echo "============================================"
echo -e "${GREEN}✓ REIMS2 is starting up!${NC}"
echo "============================================"
echo ""
echo -e "${YELLOW}Note: If services show as 'Not yet responding', wait another"
echo -e "minute and check again with: docker compose ps${NC}"
echo ""
echo -e "${YELLOW}To view logs:${NC} docker compose logs -f"
echo -e "${YELLOW}To stop:${NC}      docker compose down"
echo ""
