#!/bin/bash

# Quick extraction status check

REIMS_DIR="/home/hsthind/Documents/GitHub/REIMS2"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Get counts (using -t -A -F'|' for pipe-separated output)
COUNTS=$(docker compose -f "$REIMS_DIR/docker-compose.yml" exec -T postgres psql -U reims -d reims -t -A -F'|' -c "
    SELECT 
        COUNT(*)::text,
        COUNT(CASE WHEN extraction_status = 'completed' THEN 1 END)::text,
        COUNT(CASE WHEN extraction_status = 'pending' THEN 1 END)::text,
        COUNT(CASE WHEN extraction_status = 'validating' THEN 1 END)::text,
        COUNT(CASE WHEN extraction_status = 'extracting' THEN 1 END)::text,
        COUNT(CASE WHEN extraction_status = 'failed' THEN 1 END)::text
    FROM document_uploads 
    WHERE file_path LIKE '%ESP_2025_%Income_Statement%';
" 2>&1 | head -1 | tr -d '\r\n')

# Get file details
DETAILS=$(docker compose -f "$REIMS_DIR/docker-compose.yml" exec -T postgres psql -U reims -d reims -t -A -F'|' -c "
    SELECT 
        SUBSTRING(file_path FROM 'ESP_2025_\d+') as file,
        extraction_status,
        COALESCE(
            CASE 
                WHEN extraction_started_at IS NOT NULL AND extraction_completed_at IS NULL 
                THEN EXTRACT(EPOCH FROM (NOW() - extraction_started_at))::int::text
                ELSE NULL
            END,
            ''
        ) as processing_seconds
    FROM document_uploads 
    WHERE file_path LIKE '%ESP_2025_%Income_Statement%'
    ORDER BY id;
" 2>&1 | grep -v "^$")

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          REIMS2 - Extraction Status Check                        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo -e "${BLUE}Time: ${TIMESTAMP}${NC}"
echo ""

# Parse counts (pipe-separated values from -F'|')
if [ ! -z "$COUNTS" ]; then
    # Remove any leading/trailing whitespace and split by pipe
    COUNTS_CLEAN=$(echo "$COUNTS" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    TOTAL=$(echo "$COUNTS_CLEAN" | cut -d'|' -f1 | tr -d ' ')
    COMPLETED=$(echo "$COUNTS_CLEAN" | cut -d'|' -f2 | tr -d ' ')
    PENDING=$(echo "$COUNTS_CLEAN" | cut -d'|' -f3 | tr -d ' ')
    VALIDATING=$(echo "$COUNTS_CLEAN" | cut -d'|' -f4 | tr -d ' ')
    EXTRACTING=$(echo "$COUNTS_CLEAN" | cut -d'|' -f5 | tr -d ' ')
    FAILED=$(echo "$COUNTS_CLEAN" | cut -d'|' -f6 | tr -d ' ')
    
    # Ensure numeric values
    TOTAL=${TOTAL:-0}
    COMPLETED=${COMPLETED:-0}
    PENDING=${PENDING:-0}
    VALIDATING=${VALIDATING:-0}
    EXTRACTING=${EXTRACTING:-0}
    FAILED=${FAILED:-0}
    
    if [ "$TOTAL" -gt 0 ] 2>/dev/null; then
        PERCENT=$((COMPLETED * 100 / TOTAL))
    else
        PERCENT=0
    fi
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}📊 OVERALL STATUS:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "   Total Files:    ${BLUE}${TOTAL}${NC}"
    echo -e "   ${GREEN}✅ Completed:    ${COMPLETED} (${PERCENT}%)${NC}"
    if [ "$EXTRACTING" -gt 0 ]; then
        echo -e "   ${YELLOW}🔄 Extracting:    ${EXTRACTING}${NC}"
    fi
    if [ "$VALIDATING" -gt 0 ]; then
        echo -e "   ${YELLOW}🔍 Validating:    ${VALIDATING}${NC}"
    fi
    if [ "$PENDING" -gt 0 ]; then
        echo -e "   ${BLUE}⏳ Pending:       ${PENDING}${NC}"
    fi
    if [ "$FAILED" -gt 0 ]; then
        echo -e "   ${RED}❌ Failed:        ${FAILED}${NC}"
    fi
    echo ""
fi

# Display file details
if [ ! -z "$DETAILS" ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}📋 FILE STATUS:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo "$DETAILS" | while IFS='|' read -r file status seconds; do
        file=$(echo "$file" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        status=$(echo "$status" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        seconds=$(echo "$seconds" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        case "$status" in
            "completed")
                echo -e "   ${GREEN}✅ ${file}${NC} │ ${GREEN}Completed${NC}"
                ;;
            "extracting")
                if [ ! -z "$seconds" ] && [ "$seconds" != "NULL" ]; then
                    echo -e "   ${YELLOW}🔄 ${file}${NC} │ ${YELLOW}Extracting${NC} (${seconds}s)"
                else
                    echo -e "   ${YELLOW}🔄 ${file}${NC} │ ${YELLOW}Extracting${NC}"
                fi
                ;;
            "validating")
                if [ ! -z "$seconds" ] && [ "$seconds" != "NULL" ]; then
                    echo -e "   ${YELLOW}🔍 ${file}${NC} │ ${YELLOW}Validating${NC} (${seconds}s)"
                else
                    echo -e "   ${YELLOW}🔍 ${file}${NC} │ ${YELLOW}Validating${NC}"
                fi
                ;;
            "pending")
                echo -e "   ${BLUE}⏳ ${file}${NC} │ ${BLUE}Pending${NC} (queued)"
                ;;
            "failed")
                echo -e "   ${RED}❌ ${file}${NC} │ ${RED}Failed${NC}"
                ;;
            *)
                echo -e "   ${file} │ ${status}"
                ;;
        esac
    done
    echo ""
fi
