#!/bin/bash
set -e

###############################################################################
# REIMS2 Disk Space Cleanup Script
###############################################################################
#
# This script safely cleans up disk space by removing:
# 1. Docker unused images, containers, volumes, and build cache
# 2. System caches (npm, pip, apt)
# 3. Temporary files
# 4. Coverage reports (htmlcov/)
# 5. Old logs
#
# SAFE: Only removes unused/regenerable items
# IMPACT: Can free up 40-50+ GB of disk space
#
###############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Track what we've freed
SPACE_FREED=0

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         REIMS2 Comprehensive Disk Space Cleanup              ║${NC}"
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo ""

# Function to calculate freed space
calculate_freed() {
    local before=$1
    local after=$2
    local freed=$((before - after))
    echo $freed
}

# Function to get disk usage
get_disk_usage() {
    df / | tail -1 | awk '{print $3}'
}

# Initial disk usage
INITIAL_USAGE=$(get_disk_usage)
echo -e "${YELLOW}📊 Initial disk usage: $(df -h / | tail -1 | awk '{print $3}') / $(df -h / | tail -1 | awk '{print $2}')${NC}"
echo ""

###############################################################################
# 1. DOCKER CLEANUP (Biggest impact: ~50GB)
###############################################################################

echo -e "${GREEN}🐳 Docker Cleanup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v docker &> /dev/null; then
    echo "Current Docker disk usage:"
    docker system df
    echo ""

    read -p "Remove unused Docker images, containers, volumes, and build cache? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BEFORE=$(get_disk_usage)

        echo -e "${YELLOW}Stopping REIMS containers first...${NC}"
        cd "$PROJECT_ROOT"
        docker compose down 2>/dev/null || true

        echo -e "${YELLOW}Removing unused images...${NC}"
        docker image prune -a -f

        echo -e "${YELLOW}Removing unused volumes...${NC}"
        docker volume prune -f

        echo -e "${YELLOW}Removing build cache...${NC}"
        docker builder prune -a -f

        echo -e "${YELLOW}Removing unused containers...${NC}"
        docker container prune -f

        echo -e "${YELLOW}Removing unused networks...${NC}"
        docker network prune -f

        AFTER=$(get_disk_usage)
        FREED=$(calculate_freed $BEFORE $AFTER)
        SPACE_FREED=$((SPACE_FREED + FREED))

        echo -e "${GREEN}✅ Docker cleanup freed: $((FREED / 1024 / 1024)) GB${NC}"
        echo ""
        echo "New Docker disk usage:"
        docker system df
    else
        echo -e "${YELLOW}⏭️  Skipped Docker cleanup${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not found, skipping${NC}"
fi
echo ""

###############################################################################
# 2. PROJECT-SPECIFIC CLEANUP
###############################################################################

echo -e "${GREEN}📁 Project-Specific Cleanup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$PROJECT_ROOT"

# Remove htmlcov (37MB - already in .gitignore)
if [ -d "htmlcov" ]; then
    BEFORE=$(get_disk_usage)
    echo -e "${YELLOW}Removing htmlcov/ (37MB)...${NC}"
    rm -rf htmlcov/
    AFTER=$(get_disk_usage)
    FREED=$(calculate_freed $BEFORE $AFTER)
    SPACE_FREED=$((SPACE_FREED + FREED))
    echo -e "${GREEN}✅ Removed htmlcov/: $((FREED / 1024)) MB freed${NC}"
fi

# Remove Python cache
if [ -d "backend/__pycache__" ]; then
    echo -e "${YELLOW}Removing Python cache...${NC}"
    find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find backend -type f -name "*.pyc" -delete 2>/dev/null || true
    find backend -type f -name "*.pyo" -delete 2>/dev/null || true
    echo -e "${GREEN}✅ Removed Python cache${NC}"
fi

# Remove .venv if it exists (can be recreated)
if [ -d ".venv" ]; then
    read -p "Remove .venv/ directory? (can be recreated with pip install) (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BEFORE=$(get_disk_usage)
        echo -e "${YELLOW}Removing .venv/...${NC}"
        rm -rf .venv/
        AFTER=$(get_disk_usage)
        FREED=$(calculate_freed $BEFORE $AFTER)
        SPACE_FREED=$((SPACE_FREED + FREED))
        echo -e "${GREEN}✅ Removed .venv/: $((FREED / 1024 / 1024)) GB freed${NC}"
    fi
fi

# Remove node_modules if desired (604MB - can be recreated with npm install)
if [ -d "node_modules" ]; then
    read -p "Remove node_modules/ directory? (can be recreated with npm install) (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BEFORE=$(get_disk_usage)
        echo -e "${YELLOW}Removing node_modules/...${NC}"
        rm -rf node_modules/
        AFTER=$(get_disk_usage)
        FREED=$(calculate_freed $BEFORE $AFTER)
        SPACE_FREED=$((SPACE_FREED + FREED))
        echo -e "${GREEN}✅ Removed node_modules/: $((FREED / 1024 / 1024)) GB freed${NC}"
    fi
fi

# Remove dist/ (build artifacts)
if [ -d "dist" ]; then
    BEFORE=$(get_disk_usage)
    echo -e "${YELLOW}Removing dist/ (build artifacts)...${NC}"
    rm -rf dist/
    AFTER=$(get_disk_usage)
    FREED=$(calculate_freed $BEFORE $AFTER)
    SPACE_FREED=$((SPACE_FREED + FREED))
    echo -e "${GREEN}✅ Removed dist/: $((FREED / 1024)) MB freed${NC}"
fi

echo ""

###############################################################################
# 3. SYSTEM CACHE CLEANUP
###############################################################################

echo -e "${GREEN}🗑️  System Cache Cleanup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# NPM cache (1.7GB)
if command -v npm &> /dev/null; then
    read -p "Clean npm cache (1.7GB)? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BEFORE=$(get_disk_usage)
        echo -e "${YELLOW}Cleaning npm cache...${NC}"
        npm cache clean --force
        AFTER=$(get_disk_usage)
        FREED=$(calculate_freed $BEFORE $AFTER)
        SPACE_FREED=$((SPACE_FREED + FREED))
        echo -e "${GREEN}✅ npm cache cleaned: $((FREED / 1024 / 1024)) GB freed${NC}"
    fi
fi

# Pip cache
if command -v pip3 &> /dev/null; then
    read -p "Clean pip cache? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BEFORE=$(get_disk_usage)
        echo -e "${YELLOW}Cleaning pip cache...${NC}"
        pip3 cache purge 2>/dev/null || true
        AFTER=$(get_disk_usage)
        FREED=$(calculate_freed $BEFORE $AFTER)
        SPACE_FREED=$((SPACE_FREED + FREED))
        echo -e "${GREEN}✅ pip cache cleaned: $((FREED / 1024)) MB freed${NC}"
    fi
fi

# General cache (3.2GB)
if [ -d "$HOME/.cache" ]; then
    read -p "Clean ~/.cache directory (3.2GB)? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BEFORE=$(get_disk_usage)
        echo -e "${YELLOW}Cleaning ~/.cache...${NC}"
        # Keep some important caches, remove the rest
        find ~/.cache -type f -atime +30 -delete 2>/dev/null || true
        AFTER=$(get_disk_usage)
        FREED=$(calculate_freed $BEFORE $AFTER)
        SPACE_FREED=$((SPACE_FREED + FREED))
        echo -e "${GREEN}✅ ~/.cache cleaned: $((FREED / 1024 / 1024)) GB freed${NC}"
    fi
fi

echo ""

###############################################################################
# 4. APT CLEANUP (System packages)
###############################################################################

echo -e "${GREEN}📦 APT Package Cleanup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

read -p "Clean apt cache and remove old packages? (requires sudo) (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BEFORE=$(get_disk_usage)

    echo -e "${YELLOW}Cleaning apt cache...${NC}"
    sudo apt-get clean

    echo -e "${YELLOW}Removing old packages...${NC}"
    sudo apt-get autoremove -y

    echo -e "${YELLOW}Removing old kernels (keep current + 1 previous)...${NC}"
    sudo apt-get autopurge -y

    AFTER=$(get_disk_usage)
    FREED=$(calculate_freed $BEFORE $AFTER)
    SPACE_FREED=$((SPACE_FREED + FREED))
    echo -e "${GREEN}✅ APT cleanup: $((FREED / 1024 / 1024)) GB freed${NC}"
fi

echo ""

###############################################################################
# 5. JOURNALCTL LOGS
###############################################################################

echo -e "${GREEN}📝 System Log Cleanup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

read -p "Clean old system logs (keep last 7 days)? (requires sudo) (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BEFORE=$(get_disk_usage)
    echo -e "${YELLOW}Cleaning journalctl logs...${NC}"
    sudo journalctl --vacuum-time=7d
    AFTER=$(get_disk_usage)
    FREED=$(calculate_freed $BEFORE $AFTER)
    SPACE_FREED=$((SPACE_FREED + FREED))
    echo -e "${GREEN}✅ Logs cleaned: $((FREED / 1024)) MB freed${NC}"
fi

echo ""

###############################################################################
# 6. SNAP CLEANUP (2.8GB found earlier)
###############################################################################

echo -e "${GREEN}📸 Snap Package Cleanup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v snap &> /dev/null; then
    read -p "Remove old snap revisions? (keeps current only) (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BEFORE=$(get_disk_usage)
        echo -e "${YELLOW}Removing old snap revisions...${NC}"

        # Remove old revisions
        LANG=C snap list --all | awk '/disabled/{print $1, $3}' | while read snapname revision; do
            sudo snap remove "$snapname" --revision="$revision" 2>/dev/null || true
        done

        AFTER=$(get_disk_usage)
        FREED=$(calculate_freed $BEFORE $AFTER)
        SPACE_FREED=$((SPACE_FREED + FREED))
        echo -e "${GREEN}✅ Snap cleanup: $((FREED / 1024 / 1024)) GB freed${NC}"
    fi
fi

echo ""

###############################################################################
# SUMMARY
###############################################################################

FINAL_USAGE=$(get_disk_usage)
TOTAL_FREED=$(calculate_freed $INITIAL_USAGE $FINAL_USAGE)

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    CLEANUP SUMMARY                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Initial Disk Usage:${NC}  $(df -h / | tail -1 | awk '{print $3}') / $(df -h / | tail -1 | awk '{print $2}') ($(df -h / | tail -1 | awk '{print $5}'))"
echo -e "${GREEN}Final Disk Usage:${NC}    $(df -h / | tail -1 | awk '{print $3}') / $(df -h / | tail -1 | awk '{print $2}') ($(df -h / | tail -1 | awk '{print $5}'))"
echo -e "${GREEN}Total Space Freed:${NC}   $((TOTAL_FREED / 1024 / 1024)) GB"
echo ""

if [ $TOTAL_FREED -gt 0 ]; then
    echo -e "${GREEN}✅ Cleanup successful!${NC}"
else
    echo -e "${YELLOW}⚠️  No space was freed (either nothing to clean or cleanup was skipped)${NC}"
fi

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   RECOMMENDATIONS                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "1. Run this script monthly to prevent disk buildup"
echo "2. Monitor Docker disk usage: docker system df"
echo "3. Consider moving Docker data to separate partition if space-constrained"
echo "4. Use 'docker system prune -a' regularly to clean unused images"
echo "5. Set up log rotation for application logs"
echo ""

# Restart REIMS if it was running
read -p "Restart REIMS Docker services? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Starting REIMS services...${NC}"
    cd "$PROJECT_ROOT"
    docker compose up -d
    echo -e "${GREEN}✅ REIMS services started${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Disk cleanup complete!${NC}"
