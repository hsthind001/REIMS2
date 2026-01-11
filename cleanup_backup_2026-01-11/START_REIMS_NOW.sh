#!/bin/bash

# REIMS2 One-Click Startup
# This script opens a new terminal and starts REIMS2 services
# The new terminal will have proper docker group activation

# Create the startup command script
cat > /tmp/reims-startup-commands.sh << 'SCRIPT_EOF'
#!/bin/bash

echo "============================================"
echo "  Starting REIMS2 Services"
echo "============================================"
echo ""

# Navigate to REIMS2
cd /home/hsthind/Documents/GitHub/REIMS2

# Try docker without sudo first, fallback to sudo if needed
echo "Attempting to start services..."
if docker ps > /dev/null 2>&1; then
    echo "✓ Docker accessible without sudo"
    docker compose down 2>/dev/null
    docker compose up -d
    DOCKER_CMD="docker"
else
    echo "⚠ Using sudo for Docker commands..."
    sudo docker compose down 2>/dev/null
    sudo docker compose up -d
    DOCKER_CMD="sudo docker"
fi

echo ""
echo "Waiting for services to initialize (90 seconds)..."
sleep 90

echo ""
echo "Service Status:"
$DOCKER_CMD compose ps

echo ""
echo "============================================"
echo "  REIMS2 Access Information"
echo "============================================"
echo ""
echo "Frontend:       http://localhost:5173"
echo "API Docs:       http://localhost:8000/docs"
echo "Celery Monitor: http://localhost:5555"
echo "MinIO Console:  http://localhost:9001"
echo ""
echo "Login: admin / Admin123!"
echo ""
echo "Press Ctrl+C to close this window (services will keep running)"
echo ""

# Keep terminal open
read -p "Press Enter to close this window..."
SCRIPT_EOF

chmod +x /tmp/reims-startup-commands.sh

# Open a new terminal and run the command
# Try gnome-terminal first (Ubuntu default), then other options
if command -v gnome-terminal > /dev/null 2>&1; then
    gnome-terminal -- bash -c "/tmp/reims-startup-commands.sh; exec bash"
elif command -v xterm > /dev/null 2>&1; then
    xterm -e "/tmp/reims-startup-commands.sh; bash"
elif command -v konsole > /dev/null 2>&1; then
    konsole -e "/tmp/reims-startup-commands.sh; bash"
else
    echo "No terminal emulator found. Running in current terminal..."
    bash /tmp/reims-startup-commands.sh
fi

echo "REIMS2 startup initiated in new terminal window!"
echo "If no window appeared, the terminal is starting in the background."
echo ""
echo "You can also start manually with:"
echo "  cd ~/Documents/GitHub/REIMS2"
echo "  docker compose up -d"
