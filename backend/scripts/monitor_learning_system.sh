#!/bin/bash
# Monitor Self-Learning Forensic Reconciliation System
# Usage: ./monitor_learning_system.sh

echo "=========================================="
echo "Self-Learning Reconciliation System Monitor"
echo "=========================================="
echo

# Check if we're in docker or local
if [ -f /.dockerenv ]; then
    DB_CMD="psql -h postgres -U reims_user -d reims_db"
else
    DB_CMD="docker compose exec -T postgres psql -U reims_user -d reims_db"
fi

echo "1. Recent Learning Activities"
echo "----------------------------"
$DB_CMD <<EOF
SELECT 
    activity_type,
    activity_name,
    matches_improved,
    patterns_discovered,
    rules_created,
    created_at
FROM reconciliation_learning_log
ORDER BY created_at DESC
LIMIT 10;
EOF

echo
echo "2. Discovered Account Codes Summary"
echo "-----------------------------------"
$DB_CMD <<EOF
SELECT 
    document_type,
    COUNT(*) as total_codes,
    SUM(occurrence_count) as total_occurrences,
    COUNT(DISTINCT property_id) as properties_using
FROM discovered_account_codes
GROUP BY document_type
ORDER BY document_type;
EOF

echo
echo "3. Top Learned Patterns"
echo "----------------------"
$DB_CMD <<EOF
SELECT 
    pattern_name,
    source_document_type || ' -> ' || target_document_type as relationship,
    success_rate,
    match_count,
    average_confidence
FROM learned_match_patterns
WHERE is_active = true
ORDER BY success_rate DESC, match_count DESC
LIMIT 10;
EOF

echo
echo "4. Account Code Synonyms"
echo "-----------------------"
$DB_CMD <<EOF
SELECT 
    canonical_account_code,
    synonym_name,
    combined_confidence,
    success_rate,
    usage_count
FROM account_code_synonyms
WHERE is_active = true
ORDER BY combined_confidence DESC
LIMIT 10;
EOF

echo
echo "5. Pattern Statistics"
echo "--------------------"
$DB_CMD <<EOF
SELECT 
    pattern_type,
    COUNT(*) as pattern_count,
    AVG(match_count) as avg_matches,
    AVG(success_rate) as avg_success_rate
FROM account_code_patterns
WHERE is_active = true
GROUP BY pattern_type
ORDER BY pattern_count DESC;
EOF

echo
echo "=========================================="
echo "Monitoring complete!"
echo "=========================================="

