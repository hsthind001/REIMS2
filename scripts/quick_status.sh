#!/bin/bash
# Quick Status Check for Bulk Upload Monitoring
#
# Provides one-liner commands to quickly check upload status
# Usage: ./scripts/quick_status.sh [command]
#
# Commands:
#   queue      - Check queue depth and workers
#   recent     - Recent uploads count
#   failed     - Failed uploads count
#   stuck      - Stuck uploads count
#   summary    - Full summary (default)
#   all        - All checks

set -e

API_BASE_URL="http://localhost:8000/api/v1"
COMMAND=${1:-summary}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

check_queue() {
    local status=$(curl -s "${API_BASE_URL}/documents/queue-status" 2>/dev/null || echo '{}')
    local queue_depth=$(echo "$status" | grep -o '"queue_depth":[0-9]*' | cut -d: -f2 || echo "0")
    local workers=$(echo "$status" | grep -o '"workers_available":[0-9]*' | cut -d: -f2 || echo "0")
    local pending=$(echo "$status" | grep -o '"pending_uploads":[0-9]*' | cut -d: -f2 || echo "0")
    
    echo "Queue: ${queue_depth} tasks | Workers: ${workers} | Pending: ${pending} uploads"
}

check_recent() {
    local count=$(docker compose exec -T postgres psql -U reims -d reims -t -c "
        SELECT COUNT(*) 
        FROM document_uploads 
        WHERE upload_date > NOW() - INTERVAL '10 minutes';
    " 2>/dev/null | tr -d ' ' || echo "0")
    echo "Recent uploads (last 10 min): ${count}"
}

check_failed() {
    local count=$(docker compose exec -T postgres psql -U reims -d reims -t -c "
        SELECT COUNT(*) 
        FROM document_uploads 
        WHERE extraction_status = 'failed' 
          AND upload_date > NOW() - INTERVAL '1 hour';
    " 2>/dev/null | tr -d ' ' || echo "0")
    echo "Failed uploads (last hour): ${count}"
}

check_stuck() {
    local count=$(docker compose exec -T postgres psql -U reims -d reims -t -c "
        SELECT COUNT(*) 
        FROM document_uploads 
        WHERE extraction_status = 'pending' 
          AND upload_date < NOW() - INTERVAL '10 minutes';
    " 2>/dev/null | tr -d ' ' || echo "0")
    echo "Stuck uploads (>10 min pending): ${count}"
}

check_summary() {
    echo "=== Quick Status Summary ==="
    check_queue
    check_recent
    check_failed
    check_stuck
}

case "$COMMAND" in
    queue)
        check_queue
        ;;
    recent)
        check_recent
        ;;
    failed)
        check_failed
        ;;
    stuck)
        check_stuck
        ;;
    all|summary)
        check_summary
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Available commands: queue, recent, failed, stuck, summary, all"
        exit 1
        ;;
esac

