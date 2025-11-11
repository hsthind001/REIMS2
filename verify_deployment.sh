#!/bin/bash
echo "========================================="
echo "REIMS2 DEPLOYMENT VERIFICATION"
echo "========================================="
echo ""

echo "1. Checking all services..."
docker ps --filter "name=reims" --format "{{.Names}}: {{.Status}}" | head -10
echo ""

echo "2. Checking Cash Flow accounts count..."
CF_COUNT=$(docker exec reims-postgres psql -U reims -d reims -t -c "SELECT COUNT(*) FROM chart_of_accounts WHERE 'cash_flow' = ANY(document_types);" 2>/dev/null | tr -d ' ')
echo "Cash Flow accounts: $CF_COUNT (expected: ~154)"
echo ""

echo "3. Checking if new migrations exist..."
docker exec reims-postgres psql -U reims -d reims -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null
echo ""

echo "4. Checking new constraint..."
docker exec reims-postgres psql -U reims -d reims -c "\d cash_flow_data" 2>/dev/null | grep "uq_cf" | head -2
echo ""

echo "5. Backend health..."
curl -s http://localhost:8000/api/v1/health || echo "Backend not responding"
echo ""

echo "========================================="
echo "VERIFICATION COMPLETE"
echo "========================================="

