#!/bin/bash

# REIMS2 Setup Script for New Laptop
# Ubuntu 24.04 LTS - Acer Predator PHN16-73
# Date: 2026-01-03

set -e  # Exit on error

echo "============================================"
echo "REIMS2 Development Environment Setup"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root or with sudo"
    exit 1
fi

echo "Step 1: Updating system packages..."
echo "--------------------------------------------"
sudo apt update
sudo apt upgrade -y
print_success "System packages updated"
echo ""

echo "Step 2: Installing Git..."
echo "--------------------------------------------"
if command -v git &> /dev/null; then
    print_info "Git is already installed: $(git --version)"
else
    sudo apt install -y git
    print_success "Git installed: $(git --version)"
fi

# Configure git if not already configured
if [ -z "$(git config --global user.name)" ]; then
    print_info "Git user.name not set. Please configure:"
    read -p "Enter your git username: " git_username
    git config --global user.name "$git_username"
fi

if [ -z "$(git config --global user.email)" ]; then
    print_info "Git user.email not set. Please configure:"
    read -p "Enter your git email: " git_email
    git config --global user.email "$git_email"
fi
print_success "Git configured"
echo ""

echo "Step 3: Installing Docker..."
echo "--------------------------------------------"
if command -v docker &> /dev/null; then
    print_info "Docker is already installed: $(docker --version)"
else
    # Remove old versions if any
    sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Install dependencies
    sudo apt install -y ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    print_success "Docker installed: $(docker --version)"
fi

# Add user to docker group
if ! groups $USER | grep -q docker; then
    sudo usermod -aG docker $USER
    print_success "Added $USER to docker group"
    print_info "You'll need to log out and log back in for docker group changes to take effect"
else
    print_info "User $USER already in docker group"
fi

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
print_success "Docker service started and enabled"
echo ""

echo "Step 4: Verifying Docker Compose..."
echo "--------------------------------------------"
if docker compose version &> /dev/null; then
    print_success "Docker Compose installed: $(docker compose version)"
else
    print_error "Docker Compose not found"
    exit 1
fi
echo ""

echo "Step 5: Installing Node.js and npm..."
echo "--------------------------------------------"
if command -v node &> /dev/null; then
    print_info "Node.js is already installed: $(node --version)"
else
    # Install Node.js 20.x LTS
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
    print_success "Node.js installed: $(node --version)"
    print_success "npm installed: $(npm --version)"
fi
echo ""

echo "Step 6: Installing additional development tools..."
echo "--------------------------------------------"
sudo apt install -y \
    build-essential \
    python3-pip \
    python3-venv \
    wget \
    curl \
    jq \
    vim \
    htop \
    net-tools
print_success "Additional tools installed"
echo ""

echo "Step 7: Initializing Git repository..."
echo "--------------------------------------------"
cd /home/hsthind/Documents/GitHub/REIMS2
if [ ! -d .git ]; then
    git init
    print_success "Git repository initialized"
else
    print_info "Git repository already initialized"
fi

# Add gitignore if not exists
if [ ! -f .gitignore ]; then
    cat > .gitignore << 'EOF'
# Environment variables
.env
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
.pytest_cache/

# Node
node_modules/
dist/
build/
*.log
.DS_Store

# Docker
*.pid
*.seed
*.pid.lock

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOF
    print_success "Created .gitignore file"
fi
echo ""

echo "Step 8: Creating environment configuration..."
echo "--------------------------------------------"
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
# PostgreSQL Configuration
POSTGRES_USER=reims
POSTGRES_PASSWORD=reims
POSTGRES_DB=reims
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://reims:reims@postgres:5432/reims

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# MinIO Configuration
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET_NAME=reims-documents
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# API Configuration
API_V1_STR=/api/v1
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Frontend Configuration
VITE_API_URL=http://localhost:8000
EOF
    print_success "Created .env file"
else
    print_info ".env file already exists"
fi
echo ""

echo "============================================"
echo "Installation Summary"
echo "============================================"
echo ""
print_success "Git: $(git --version)"
print_success "Docker: $(docker --version)"
print_success "Docker Compose: $(docker compose version)"
print_success "Node.js: $(node --version)"
print_success "npm: $(npm --version)"
echo ""

echo "============================================"
echo "Next Steps"
echo "============================================"
echo ""
echo "1. Log out and log back in (or run: newgrp docker)"
echo "   This is required for docker group membership to take effect"
echo ""
echo "2. Start REIMS2 services:"
echo "   cd /home/hsthind/Documents/GitHub/REIMS2"
echo "   docker compose up -d"
echo ""
echo "3. Wait for services to start (30-60 seconds)"
echo ""
echo "4. Access the application:"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo "   Flower (Celery): http://localhost:5555"
echo ""
echo "5. Login with default credentials:"
echo "   Username: admin"
echo "   Password: Admin123!"
echo ""
print_success "Setup complete!"
echo ""
