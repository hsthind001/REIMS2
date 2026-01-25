#!/bin/bash
# Apply All Validation Rules Seed Files
# This script applies all 6 seed files to populate the validation_rules table

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  REIMS2 - Applying All Validation Rules Seed Files"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERROR: docker-compose not found. Please install docker-compose first.${NC}"
    exit 1
fi

# Check if database container is running
if ! docker-compose ps | grep -q "reims.*db.*Up"; then
    echo -e "${RED}ERROR: Database container is not running.${NC}"
    echo "Please start the containers with: docker-compose up -d"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILES=(
    "seed_balance_sheet_rules.sql"
    "seed_income_statement_rules.sql"
    "seed_three_statement_integration_rules.sql"
    "seed_cash_flow_rules.sql"
    "seed_mortgage_validation_rules.sql"
    "seed_rent_roll_validation_rules.sql"
)

echo -e "${BLUE}Found ${#SEED_FILES[@]} seed files to apply${NC}"
echo ""

# Copy all seed files to container
echo "📦 Copying seed files to database container..."
for seed_file in "${SEED_FILES[@]}"; do
    if [ ! -f "$SCRIPT_DIR/$seed_file" ]; then
        echo -e "${RED}ERROR: Seed file not found: $seed_file${NC}"
        exit 1
    fi
    
    echo "  • Copying $seed_file..."
    docker cp "$SCRIPT_DIR/$seed_file" reims-db:/tmp/ 2>/dev/null || \
    docker cp "$SCRIPT_DIR/$seed_file" $(docker-compose ps -q db):/tmp/
done

echo -e "${GREEN}✓ All seed files copied successfully${NC}"
echo ""

# Apply each seed file
echo "🔧 Applying seed files to database..."
echo ""

for seed_file in "${SEED_FILES[@]}"; do
    echo -e "${YELLOW}Applying: $seed_file${NC}"
    
    # Execute the seed file
    docker-compose exec -T db psql -U reims_user -d reims -f "/tmp/$seed_file" 2>&1 | grep -v "^$" | sed 's/^/  /'
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Applied successfully${NC}"
    else
        echo -e "${RED}  ✗ Failed to apply${NC}"
        exit 1
    fi
    echo ""
done

echo "════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ All seed files applied successfully!${NC}"
echo ""

# Verification
echo "📊 Verification - Counting rules by document type:"
echo ""

docker-compose exec -T db psql -U reims_user -d reims << 'EOF'
SELECT 
    document_type,
    COUNT(*) as rules,
    COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
    COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
    COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium,
    COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warning,
    COUNT(CASE WHEN severity = 'info' THEN 1 END) as info
FROM validation_rules
WHERE is_active = true
GROUP BY document_type
ORDER BY document_type;

-- Total count
SELECT 
    'TOTAL' as document_type,
    COUNT(*) as rules,
    COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
    COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
    COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium,
    COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warning,
    COUNT(CASE WHEN severity = 'info' THEN 1 END) as info
FROM validation_rules
WHERE is_active = true;
EOF

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}Expected Results:${NC}"
echo "  • Balance Sheet:              35 rules"
echo "  • Income Statement:           31 rules"
echo "  • Three Statement Integration: 23 rules"
echo "  • Cash Flow:                  23 rules"
echo "  • Mortgage Statement:         14 rules"
echo "  • Rent Roll:                   9 rules"
echo "  ─────────────────────────────────────"
echo "  • TOTAL:                     135 rules"
echo ""
echo -e "${GREEN}✅ Database seeding complete!${NC}"
echo ""
echo "🎯 Next Steps:"
echo "  1. Restart the backend: docker-compose restart backend"
echo "  2. Refresh the Financial Integrity Hub in your browser"
echo "  3. Click 'Validate' to run all 135 rules"
echo "  4. All 6 categories should now be visible!"
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo ""
