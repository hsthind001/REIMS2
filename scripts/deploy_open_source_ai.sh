#!/bin/bash

# ============================================================================
# REIMS Open-Source AI Deployment Script
# ============================================================================
# This script deploys the open-source generative AI stack for Market Intelligence
#
# Author: REIMS Development Team
# Date: 2025-01-09
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================================
# STEP 1: Prerequisites Check
# ============================================================================
print_header "Step 1: Checking Prerequisites"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
else
    print_success "Docker is installed: $(docker --version)"
fi

# Check Docker Compose
if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
else
    print_success "Docker Compose is installed: $(docker compose version)"
fi

# Check if NVIDIA GPU is available
if command -v nvidia-smi &> /dev/null; then
    print_success "NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    GPU_AVAILABLE=true
else
    print_warning "No NVIDIA GPU detected. Will use CPU inference (slower)."
    GPU_AVAILABLE=false
fi

# ============================================================================
# STEP 2: Configuration
# ============================================================================
print_header "Step 2: Configuration"

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "Created .env file from .env.example"
    else
        print_error ".env.example not found. Please create .env manually."
        exit 1
    fi
fi

# Add LLM configuration to .env if not present
if ! grep -q "OLLAMA_BASE_URL" .env; then
    print_info "Adding LLM configuration to .env..."
    cat >> .env << 'EOF'

# ============================================================================
# OPEN-SOURCE LLM CONFIGURATION
# ============================================================================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_DEFAULT_MODEL=llama3.3:70b-instruct-q4_K_M
GROQ_API_KEY=
LLM_PROVIDER=ollama
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4000
LLM_ENABLE_STREAMING=true
EOF
    print_success "Added LLM configuration to .env"
else
    print_info "LLM configuration already exists in .env"
fi

# ============================================================================
# STEP 3: GPU Configuration (if available)
# ============================================================================
if [ "$GPU_AVAILABLE" = true ]; then
    print_header "Step 3: GPU Configuration"

    # Check if nvidia-docker is installed
    if docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_success "NVIDIA Docker runtime is available"

        # Uncomment GPU configuration in docker-compose.ollama.yml
        print_info "Enabling GPU support in docker-compose.ollama.yml..."
        if [ -f docker-compose.ollama.yml ]; then
            # Use sed to uncomment GPU lines
            sed -i 's/#\s*device_requests:/      device_requests:/g' docker-compose.ollama.yml
            sed -i 's/#\s*- driver: nvidia/        - driver: nvidia/g' docker-compose.ollama.yml
            sed -i 's/#\s*count: 1/          count: 1/g' docker-compose.ollama.yml
            sed -i 's/#\s*capabilities: \[gpu\]/          capabilities: [gpu]/g' docker-compose.ollama.yml
            print_success "GPU support enabled in docker-compose.ollama.yml"
        fi
    else
        print_warning "NVIDIA Docker runtime not available. Installing..."
        print_info "Please run the following commands manually (requires sudo):"
        echo "  distribution=\$(. /etc/os-release;echo \$ID\$VERSION_ID)"
        echo "  curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -"
        echo "  curl -s -L https://nvidia.github.io/nvidia-docker/\$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list"
        echo "  sudo apt-get update && sudo apt-get install -y nvidia-docker2"
        echo "  sudo systemctl restart docker"
    fi
else
    print_header "Step 3: CPU-Only Configuration"
    print_info "Configuring for CPU inference..."
fi

# ============================================================================
# STEP 4: Start Services
# ============================================================================
print_header "Step 4: Starting Services"

# Build and start services
print_info "Starting REIMS services with Ollama..."
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d

print_success "Services started successfully!"

# ============================================================================
# STEP 5: Wait for Ollama to be Ready
# ============================================================================
print_header "Step 5: Waiting for Ollama Service"

print_info "Waiting for Ollama to start (this may take 1-2 minutes)..."
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_success "Ollama service is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    print_error "Ollama service failed to start. Check logs with: docker logs reims-ollama"
    exit 1
fi

# ============================================================================
# STEP 6: Pull Models
# ============================================================================
print_header "Step 6: Downloading Models"

print_warning "This step will download ~100GB of models. This may take 30-60 minutes."
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Skipping model download. You can pull models manually later with:"
    echo "  docker exec -it reims-ollama ollama pull llama3.3:70b-instruct-q4_K_M"
else
    print_info "Pulling Llama 3.2 3B (fast model, ~2GB)..."
    docker exec -it reims-ollama ollama pull llama3.2:3b-instruct-q4_K_M
    print_success "Llama 3.2 3B downloaded"

    print_info "Pulling Llama 3.3 70B (high quality, ~40GB) - This will take time..."
    docker exec -it reims-ollama ollama pull llama3.3:70b-instruct-q4_K_M
    print_success "Llama 3.3 70B downloaded"

    print_info "Pulling Qwen 2.5 32B (balanced, ~20GB)..."
    docker exec -it reims-ollama ollama pull qwen2.5:32b-instruct-q4_K_M
    print_success "Qwen 2.5 32B downloaded"

    print_info "Pulling LLaVA 13B (vision model, ~8GB)..."
    docker exec -it reims-ollama ollama pull llava:13b-v1.6-vicuna-q4_K_M
    print_success "LLaVA 13B downloaded"

    print_success "All models downloaded successfully!"
fi

# ============================================================================
# STEP 7: Verify Installation
# ============================================================================
print_header "Step 7: Verifying Installation"

# List available models
print_info "Available Ollama models:"
docker exec -it reims-ollama ollama list

# Test basic inference
print_info "Testing Llama 3.2 3B with a simple prompt..."
test_response=$(docker exec -it reims-ollama ollama run llama3.2:3b-instruct-q4_K_M "What is real estate investing in one sentence?" 2>&1)

if [ $? -eq 0 ]; then
    print_success "Model inference test passed!"
    echo "Response: $test_response"
else
    print_error "Model inference test failed. Check Ollama logs."
fi

# Check if backend can connect to Ollama
print_info "Testing backend connection to Ollama..."
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    print_success "Backend is running and accessible"
else
    print_warning "Backend may not be fully ready yet. Wait a few more seconds."
fi

# ============================================================================
# STEP 8: Summary
# ============================================================================
print_header "🎉 Deployment Complete!"

echo -e "${GREEN}Open-source AI stack is now running!${NC}\n"

echo "📊 Service URLs:"
echo "  - Backend API: http://localhost:8000"
echo "  - Frontend: http://localhost:5173"
echo "  - Ollama API: http://localhost:11434"
echo "  - Open WebUI: http://localhost:3000"
echo "  - Flower (Celery): http://localhost:5555"
echo ""

echo "🤖 Installed Models:"
docker exec reims-ollama ollama list 2>/dev/null || echo "  (Check with: docker exec -it reims-ollama ollama list)"
echo ""

echo "📚 Next Steps:"
echo "  1. Test AI insights generation:"
echo "     curl http://localhost:8000/api/v1/properties/ESP001/market-intelligence/insights"
echo ""
echo "  2. Access Open WebUI for interactive testing:"
echo "     http://localhost:3000"
echo ""
echo "  3. Monitor Ollama logs:"
echo "     docker logs -f reims-ollama"
echo ""
echo "  4. Read full documentation:"
echo "     docs/OPEN_SOURCE_AI_IMPLEMENTATION.md"
echo ""

print_success "Happy analyzing! 🚀"

# ============================================================================
# Optional: Performance Benchmark
# ============================================================================
read -p "Would you like to run a performance benchmark? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_header "Running Performance Benchmark"

    print_info "Testing Llama 3.2 3B inference speed..."
    start_time=$(date +%s)
    docker exec reims-ollama ollama run llama3.2:3b-instruct-q4_K_M "Explain SWOT analysis in real estate" > /dev/null 2>&1
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    print_success "Llama 3.2 3B completed in ${duration} seconds"

    if docker exec reims-ollama ollama list | grep -q "llama3.3"; then
        print_info "Testing Llama 3.3 70B inference speed..."
        start_time=$(date +%s)
        docker exec reims-ollama ollama run llama3.3:70b-instruct-q4_K_M "Explain SWOT analysis in real estate" > /dev/null 2>&1
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        print_success "Llama 3.3 70B completed in ${duration} seconds"
    fi

    if [ "$GPU_AVAILABLE" = true ]; then
        print_info "GPU Memory Usage:"
        nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
    fi
fi

exit 0
