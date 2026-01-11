#!/bin/bash

# Comprehensive MinIO files status checker
# Shows all files in MinIO with their database upload and extraction status

REIMS_DIR="/home/hsthind/Documents/GitHub/REIMS2"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     REIMS2 - Complete MinIO Files Status Report                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo -e "${BLUE}Generated: ${TIMESTAMP}${NC}"
echo ""

# Get all files from MinIO using mc (MinIO client) or list from database
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📋 Fetching all files from MinIO and database...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Query database for all document uploads with their status
FILES_DATA=$(docker compose -f "$REIMS_DIR/docker-compose.yml" exec -T postgres psql -U reims -d reims -t -A -F'|' -c "
    SELECT 
        COALESCE(du.file_path, '') as file_path,
        COALESCE(du.file_name, '') as file_name,
        COALESCE(p.property_code, '') as property_code,
        COALESCE(fp.period_year::text, '') as year,
        COALESCE(fp.period_month::text, '') as month,
        COALESCE(du.document_type, '') as document_type,
        COALESCE(du.extraction_status, '') as extraction_status,
        CASE 
            WHEN du.extraction_status = 'completed' THEN '✅ PASS'
            WHEN du.extraction_status = 'failed' THEN '❌ FAIL'
            WHEN du.extraction_status IN ('extracting', 'validating') THEN '🔄 IN PROGRESS'
            WHEN du.extraction_status = 'pending' THEN '⏳ PENDING'
            WHEN du.extraction_status IS NULL THEN '❓ NOT UPLOADED'
            ELSE COALESCE(UPPER(du.extraction_status), 'UNKNOWN')
        END as status_display,
        COALESCE(du.extraction_task_id, '') as extraction_task_id,
        CASE 
            WHEN du.extraction_started_at IS NOT NULL AND du.extraction_completed_at IS NULL 
            THEN EXTRACT(EPOCH FROM (NOW() - du.extraction_started_at))::int::text
            ELSE ''
        END as processing_seconds,
        COALESCE(du.extraction_completed_at::text, '') as extraction_completed_at
    FROM document_uploads du
    JOIN properties p ON du.property_id = p.id
    JOIN financial_periods fp ON du.period_id = fp.id
    ORDER BY p.property_code, fp.period_year DESC, fp.period_month DESC, du.document_type, du.upload_date DESC;
" 2>&1 | grep -v "^$" | grep -v "ERROR" | grep -v "rows)")

# Count statistics
STATS=$(docker compose -f "$REIMS_DIR/docker-compose.yml" exec -T postgres psql -U reims -d reims -t -A -F'|' -c "
    SELECT 
        COUNT(*)::text as total,
        COUNT(CASE WHEN extraction_status = 'completed' THEN 1 END)::text as completed,
        COUNT(CASE WHEN extraction_status = 'pending' THEN 1 END)::text as pending,
        COUNT(CASE WHEN extraction_status IN ('extracting', 'validating') THEN 1 END)::text as in_progress,
        COUNT(CASE WHEN extraction_status = 'failed' THEN 1 END)::text as failed,
        COUNT(CASE WHEN extraction_status IS NULL THEN 1 END)::text as not_uploaded
    FROM document_uploads;
" 2>&1 | head -1 | tr -d '\r\n')

# Parse stats
if [ ! -z "$STATS" ]; then
    TOTAL=$(echo "$STATS" | cut -d'|' -f1 | tr -d ' ')
    COMPLETED=$(echo "$STATS" | cut -d'|' -f2 | tr -d ' ')
    PENDING=$(echo "$STATS" | cut -d'|' -f3 | tr -d ' ')
    IN_PROGRESS=$(echo "$STATS" | cut -d'|' -f4 | tr -d ' ')
    FAILED=$(echo "$STATS" | cut -d'|' -f5 | tr -d ' ')
    NOT_UPLOADED=$(echo "$STATS" | cut -d'|' -f6 | tr -d ' ')
    
    TOTAL=${TOTAL:-0}
    COMPLETED=${COMPLETED:-0}
    PENDING=${PENDING:-0}
    IN_PROGRESS=${IN_PROGRESS:-0}
    FAILED=${FAILED:-0}
    NOT_UPLOADED=${NOT_UPLOADED:-0}
    
    if [ "$TOTAL" -gt 0 ] 2>/dev/null; then
        PERCENT=$((COMPLETED * 100 / TOTAL))
    else
        PERCENT=0
    fi
fi

# Display statistics
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 OVERALL STATISTICS:${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "   Total Files in Database:    ${BLUE}${TOTAL}${NC}"
echo -e "   ${GREEN}✅ Completed (PASS):        ${COMPLETED} (${PERCENT}%)${NC}"
if [ "$IN_PROGRESS" -gt 0 ] 2>/dev/null; then
    echo -e "   ${YELLOW}🔄 In Progress:           ${IN_PROGRESS}${NC}"
fi
if [ "$PENDING" -gt 0 ] 2>/dev/null; then
    echo -e "   ${BLUE}⏳ Pending in Queue:       ${PENDING}${NC}"
fi
if [ "$FAILED" -gt 0 ] 2>/dev/null; then
    echo -e "   ${RED}❌ Failed (FAIL):          ${FAILED}${NC}"
fi
if [ "$NOT_UPLOADED" -gt 0 ] 2>/dev/null; then
    echo -e "   ${RED}❓ Not Uploaded:           ${NOT_UPLOADED}${NC}"
fi
echo ""

# Display file details
if [ ! -z "$FILES_DATA" ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}📁 FILE DETAILS:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    printf "%-15s %-6s %-6s %-20s %-15s %-12s\n" "Property" "Year" "Month" "Document Type" "File Name" "Status"
    echo "────────────────────────────────────────────────────────────────────────────────────────────────────────"
    
    echo "$FILES_DATA" | while IFS='|' read -r file_path file_name property_code year month doc_type extraction_status status_display task_id processing_seconds completed_at; do
        # Trim whitespace
        property_code=$(echo "$property_code" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        year=$(echo "$year" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        month=$(echo "$month" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        doc_type=$(echo "$doc_type" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        file_name=$(echo "$file_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        status_display=$(echo "$status_display" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        processing_seconds=$(echo "$processing_seconds" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Truncate long file names
        if [ ${#file_name} -gt 25 ]; then
            file_name="${file_name:0:22}..."
        fi
        
        # Format document type
        doc_type_formatted=$(echo "$doc_type" | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
        
        # Color code status
        case "$extraction_status" in
            "completed")
                status_color="${GREEN}"
                ;;
            "failed")
                status_color="${RED}"
                ;;
            "extracting"|"validating")
                status_color="${YELLOW}"
                if [ ! -z "$processing_seconds" ]; then
                    status_display="${status_display} (${processing_seconds}s)"
                fi
                ;;
            "pending")
                status_color="${BLUE}"
                ;;
            *)
                status_color="${RED}"
                ;;
        esac
        
        printf "%-15s %-6s %-6s %-20s %-25s ${status_color}%-30s${NC}\n" \
            "$property_code" "$year" "$month" "$doc_type_formatted" "$file_name" "$status_display"
    done
    echo ""
fi

# Check for files in MinIO that might not be in database
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}💡 NOTE:${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "   This report shows all files that have been uploaded to the database."
echo "   Files in MinIO that haven't been registered in the database won't appear here."
echo "   Status meanings:"
echo "   • ✅ PASS = Successfully extracted and stored in database"
echo "   • ❌ FAIL = Extraction failed"
echo "   • 🔄 IN PROGRESS = Currently being processed"
echo "   • ⏳ PENDING = Queued for processing"
echo "   • ❓ NOT UPLOADED = File record exists but not uploaded"
echo ""

