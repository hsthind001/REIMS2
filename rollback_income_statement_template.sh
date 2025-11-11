#!/bin/bash
###############################################################################
# Income Statement Template v1.0 - Rollback Script
#
# Safely rolls back the Income Statement implementation if issues are detected
###############################################################################

set -e

echo "================================================"
echo "Income Statement Template v1.0 - Rollback"
echo "================================================"
echo ""

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${RED}WARNING: This will rollback the Income Statement Template v1.0 deployment${NC}"
echo ""
echo "This will:"
echo "  • Rollback the database migration (drop income_statement_headers table)"
echo "  • Remove header_id column from income_statement_data"
echo "  • Restart services with previous code"
echo ""
echo -e "${YELLOW}Note: Line items data will be preserved, only header functionality removed${NC}"
echo ""
read -p "Are you sure you want to rollback? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo "Starting rollback..."
echo ""

# Get current migration revision
echo "Getting current migration revision..."
CURRENT_REV=$(docker-compose exec -T backend alembic current 2>/dev/null | grep -oP '(?<=Revision: )[a-f0-9]+' || echo "")

if [ -z "$CURRENT_REV" ]; then
    echo -e "${YELLOW}Warning: Could not determine current revision${NC}"
fi

echo "Current revision: $CURRENT_REV"
echo ""

# Rollback migration (target: previous version before income statement header)
echo "Rolling back database migration..."
echo "Target revision: 20251107_0200_cf_add_standardized_fields (one before income statement header)"
echo ""

docker-compose exec -T backend alembic downgrade 20251107_0200

echo ""
echo -e "${GREEN}✓ Migration rolled back${NC}"
echo ""

# Restart services
echo "Restarting services..."
docker-compose restart backend celery-worker flower

echo ""
echo -e "${GREEN}✓ Services restarted${NC}"
echo ""

echo "================================================"
echo "Rollback Complete"
echo "================================================"
echo ""
echo "What was rolled back:"
echo "  ✓ income_statement_headers table dropped"
echo "  ✓ header_id column removed from income_statement_data"
echo "  ✓ Foreign key constraints removed"
echo ""
echo "What remains (unchanged):"
echo "  • income_statement_data table (line items preserved)"
echo "  • Chart of accounts (100+ accounts still seeded)"
echo "  • Validation rules (13 rules still active)"
echo ""
echo "To redeploy:"
echo "  ./deploy_income_statement_template.sh"
echo ""
echo -e "${GREEN}Rollback successful${NC}"
echo ""

