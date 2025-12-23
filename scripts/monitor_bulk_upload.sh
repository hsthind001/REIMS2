#!/bin/bash
# Bulk Document Upload Monitoring Script
# 
# Real-time monitoring for bulk document uploads
# Monitors: API, Database, Celery workers, MinIO, Extraction tasks
#
# Usage:
#   ./scripts/monitor_bulk_upload.sh
#   ./scripts/monitor_bulk_upload.sh --interval 5  # Update every 5 seconds
#   ./scripts/monitor_bulk_upload.sh --once         # Run once and exit

set -e

# Configuration
INTERVAL=${MONITOR_INTERVAL:-10}
RUN_ONCE=false
API_BASE_URL="http://localhost:8000/api/v1"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --once)
            RUN_ONCE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--interval SECONDS] [--once]"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if docker compose is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker command not found${NC}"
    exit 1
fi

# Check if services are running
check_services() {
    if ! docker compose ps | grep -q "reims-backend.*Up"; then
        echo -e "${RED}Warning: Backend service is not running${NC}"
    fi
    if ! docker compose ps | grep -q "reims-celery-worker.*Up"; then
        echo -e "${YELLOW}Warning: Celery worker is not running${NC}"
    fi
    if ! docker compose ps | grep -q "reims-postgres.*Up"; then
        echo -e "${RED}Error: PostgreSQL is not running${NC}"
        exit 1
    fi
}

# Get queue status
get_queue_status() {
    curl -s "${API_BASE_URL}/documents/queue-status" 2>/dev/null || echo '{"error": "API unavailable"}'
}

# Format queue status
format_queue_status() {
    local status=$(get_queue_status)
    local queue_depth=$(echo "$status" | grep -o '"queue_depth":[0-9]*' | cut -d: -f2 || echo "0")
    local workers=$(echo "$status" | grep -o '"workers_available":[0-9]*' | cut -d: -f2 || echo "0")
    local pending=$(echo "$status" | grep -o '"pending_uploads":[0-9]*' | cut -d: -f2 || echo "0")
    
    echo -e "${CYAN}Queue Depth:${NC} ${queue_depth} tasks"
    echo -e "${CYAN}Workers Available:${NC} ${workers}"
    echo -e "${CYAN}Pending Uploads:${NC} ${pending}"
    
    if [ "$workers" = "0" ]; then
        echo -e "${RED}⚠️  WARNING: No Celery workers available!${NC}"
    fi
    
    if [ "$queue_depth" -gt 50 ]; then
        echo -e "${YELLOW}⚠️  WARNING: Queue depth is high (>50 tasks)${NC}"
    fi
}

# Get recent uploads from database
get_recent_uploads() {
    docker compose exec -T postgres psql -U reims -d reims -c "
        SELECT 
            id, 
            file_name, 
            document_type,
            extraction_status, 
            EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_ago
        FROM document_uploads 
        WHERE upload_date > NOW() - INTERVAL '5 minutes'
        ORDER BY upload_date DESC
        LIMIT 10;
    " 2>/dev/null || echo "Database query failed"
}

# Get failed uploads
get_failed_uploads() {
    docker compose exec -T postgres psql -U reims -d reims -c "
        SELECT 
            id, 
            file_name, 
            extraction_status, 
            LEFT(notes, 100) as error_summary,
            EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_ago
        FROM document_uploads 
        WHERE extraction_status = 'failed' 
          AND upload_date > NOW() - INTERVAL '1 hour'
        ORDER BY upload_date DESC
        LIMIT 5;
    " 2>/dev/null || echo "Database query failed"
}

# Get stuck uploads (pending > 10 minutes)
get_stuck_uploads() {
    docker compose exec -T postgres psql -U reims -d reims -c "
        SELECT 
            id, 
            file_name, 
            extraction_status, 
            EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_pending
        FROM document_uploads 
        WHERE extraction_status = 'pending' 
          AND upload_date < NOW() - INTERVAL '10 minutes'
        ORDER BY upload_date ASC
        LIMIT 5;
    " 2>/dev/null || echo "Database query failed"
}

# Get upload summary by status
get_upload_summary() {
    docker compose exec -T postgres psql -U reims -d reims -c "
        SELECT 
            extraction_status, 
            COUNT(*) as count
        FROM document_uploads
        WHERE upload_date > NOW() - INTERVAL '1 hour'
        GROUP BY extraction_status
        ORDER BY count DESC;
    " 2>/dev/null || echo "Database query failed"
}

# Check for errors in backend logs
check_backend_errors() {
    local error_count=$(docker compose logs backend --tail 100 2>/dev/null | grep -iE "(error|failed|exception)" | wc -l || echo "0")
    if [ "$error_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found ${error_count} error(s) in recent backend logs${NC}"
        echo -e "${CYAN}Recent errors:${NC}"
        docker compose logs backend --tail 50 2>/dev/null | grep -iE "(error|failed|exception)" | tail -3 || true
    else
        echo -e "${GREEN}✓ No recent errors in backend logs${NC}"
    fi
}

# Check for errors in Celery logs
check_celery_errors() {
    local error_count=$(docker compose logs celery-worker --tail 100 2>/dev/null | grep -iE "(error|failed|exception)" | wc -l || echo "0")
    if [ "$error_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found ${error_count} error(s) in recent Celery logs${NC}"
    else
        echo -e "${GREEN}✓ No recent errors in Celery logs${NC}"
    fi
}

# Main monitoring loop
monitor_loop() {
    while true; do
        clear
        echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║${NC}  ${CYAN}Bulk Document Upload Monitor${NC}                          ${BLUE}║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
        echo -e "${CYAN}Time:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        
        # Queue Status
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}📊 Queue Status${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        format_queue_status
        echo ""
        
        # Upload Summary
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}📈 Upload Summary (Last Hour)${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        get_upload_summary
        echo ""
        
        # Recent Uploads
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}📄 Recent Uploads (Last 5 Minutes)${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        get_recent_uploads
        echo ""
        
        # Stuck Uploads
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}⏱️  Stuck Uploads (Pending > 10 Minutes)${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        local stuck=$(get_stuck_uploads)
        if echo "$stuck" | grep -q "0 rows"; then
            echo -e "${GREEN}✓ No stuck uploads${NC}"
        else
            echo -e "${YELLOW}$stuck${NC}"
        fi
        echo ""
        
        # Failed Uploads
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}❌ Failed Uploads (Last Hour)${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        local failed=$(get_failed_uploads)
        if echo "$failed" | grep -q "0 rows"; then
            echo -e "${GREEN}✓ No failed uploads${NC}"
        else
            echo -e "${RED}$failed${NC}"
        fi
        echo ""
        
        # Error Checks
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}🔍 Error Checks${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        check_backend_errors
        check_celery_errors
        echo ""
        
        # Service Status
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}🔧 Service Status${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "(reims-backend|reims-celery-worker|reims-postgres|reims-minio)" || true
        echo ""
        
        echo -e "${CYAN}Press Ctrl+C to stop monitoring${NC}"
        echo -e "${CYAN}Refreshing in ${INTERVAL} seconds...${NC}"
        
        if [ "$RUN_ONCE" = true ]; then
            break
        fi
        
        sleep "$INTERVAL"
    done
}

# Main execution
main() {
    check_services
    monitor_loop
}

# Run main function
main

