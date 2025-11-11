#!/bin/bash
###############################################################################
# Income Statement Template v1.0 - Deployment Script
# 
# Deploys the complete Income Statement implementation including:
# - Database migration (income_statement_headers table + header_id column)
# - Enhanced models with all Template v1.0 fields
# - Comprehensive extraction and insertion logic
# - 13 validation rules
###############################################################################

set -e  # Exit on error

echo "========================================="
echo "Income Statement Template v1.0 Deployment"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found${NC}"
    echo "Please run this script from the REIMS2 root directory"
    exit 1
fi

echo "Select deployment option:"
echo "1) Quick Deploy (restart services only - recommended if code already updated)"
echo "2) Full Rebuild (rebuild images and restart - use after major changes)"
echo "3) Database Migration Only (run migration without restarting services)"
echo ""
read -p "Enter option (1-3): " deploy_option

case $deploy_option in
    1)
        echo ""
        echo -e "${YELLOW}Option 1: Quick Deploy${NC}"
        echo "Restarting services with new code..."
        echo ""
        
        # Stop services
        echo "Stopping services..."
        docker-compose stop backend celery-worker flower
        
        # Run migration
        echo "Running database migration..."
        docker-compose run --rm backend alembic upgrade head
        
        # Restart services
        echo "Starting services..."
        docker-compose up -d backend celery-worker flower
        
        echo ""
        echo -e "${GREEN}✓ Quick deploy complete!${NC}"
        ;;
    
    2)
        echo ""
        echo -e "${YELLOW}Option 2: Full Rebuild${NC}"
        echo "This will rebuild images and restart all services..."
        echo ""
        read -p "Continue? (y/n): " confirm
        
        if [ "$confirm" != "y" ]; then
            echo "Deployment cancelled"
            exit 0
        fi
        
        # Stop all services
        echo "Stopping all services..."
        docker-compose down
        
        # Rebuild backend services
        echo "Rebuilding backend, celery-worker, and flower..."
        docker-compose build backend celery-worker flower
        
        # Start all services
        echo "Starting all services..."
        docker-compose up -d
        
        # Wait for backend to be ready
        echo "Waiting for backend to be ready..."
        sleep 10
        
        # Run migration
        echo "Running database migration..."
        docker-compose exec -T backend alembic upgrade head
        
        echo ""
        echo -e "${GREEN}✓ Full rebuild complete!${NC}"
        ;;
    
    3)
        echo ""
        echo -e "${YELLOW}Option 3: Database Migration Only${NC}"
        echo "Running migration..."
        echo ""
        
        docker-compose exec -T backend alembic upgrade head
        
        echo ""
        echo -e "${GREEN}✓ Migration complete!${NC}"
        echo -e "${YELLOW}Note: You may need to restart services for changes to take effect${NC}"
        ;;
    
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "Deployment Summary"
echo "========================================="
echo ""
echo "✓ Income Statement Template v1.0 deployed"
echo ""
echo "What was deployed:"
echo "  • IncomeStatementHeader model (30+ fields)"
echo "  • Enhanced IncomeStatementData with Template v1.0 fields"
echo "  • Complete extraction with hierarchy detection"
echo "  • Comprehensive insertion logic"
echo "  • Header totals calculation"
echo "  • 13 validation rules (already active)"
echo ""
echo "Next steps:"
echo "  1. Run verification: ./verify_income_statement_deployment.sh"
echo "  2. Upload test Income Statement PDFs"
echo "  3. Verify extraction results"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""

