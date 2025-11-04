#!/bin/bash
#
# Quick Sample Data Upload
# Uploads all 28 sample PDFs without waiting for extraction
# Extraction happens asynchronously in background via Celery
#

API_URL="http://localhost:8000/api/v1"
SAMPLE_DIR="/home/gurpyar/REIMS_Uploaded/uploads/Sampledata"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Quick Sample Data Upload${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

upload_count=0
success_count=0
error_count=0

# Function to upload a file
upload_file() {
    local property_code=$1
    local year=$2
    local month=$3
    local doc_type=$4
    local filename=$5
    
    echo -n "Uploading: $property_code $year-$(printf '%02d' $month) $doc_type... "
    
    response=$(curl -s -X POST "$API_URL/documents/upload" \
        -F "property_code=$property_code" \
        -F "period_year=$year" \
        -F "period_month=$month" \
        -F "document_type=$doc_type" \
        -F "file=@$SAMPLE_DIR/$filename" \
        -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -1)
    
    if [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓${NC}"
        ((success_count++))
    else
        echo -e "${YELLOW}✗ (HTTP $http_code)${NC}"
        ((error_count++))
    fi
    
    ((upload_count++))
}

# ESP001 - Esplanade
upload_file "ESP001" 2023 12 "balance_sheet" "ESP 2023 Balance Sheet.pdf"
upload_file "ESP001" 2023 12 "income_statement" "ESP 2023 Income Statement.pdf"
upload_file "ESP001" 2023 12 "cash_flow" "ESP 2023 Cash Flow Statement.pdf"
upload_file "ESP001" 2024 12 "balance_sheet" "ESP 2024 Balance Sheet.pdf"
upload_file "ESP001" 2024 12 "income_statement" "ESP 2024 Income Statement.pdf"
upload_file "ESP001" 2024 12 "cash_flow" "ESP 2024 Cash Flow Statement.pdf"
upload_file "ESP001" 2025 4 "rent_roll" "ESP Roll April 2025.pdf"

# HMND001 - Hammond Aire
upload_file "HMND001" 2023 12 "balance_sheet" "Hammond Aire 2023 Balance Sheet.pdf"
upload_file "HMND001" 2023 12 "income_statement" "Hammond Aire 2023 Income Statement.pdf"
upload_file "HMND001" 2023 12 "cash_flow" "Hammond Aire 2023 Cash Flow Statement.pdf"
upload_file "HMND001" 2024 12 "balance_sheet" "Hammond Aire2024 Balance Sheet.pdf"
upload_file "HMND001" 2024 12 "income_statement" "HMND 2024 Income Statement.pdf"
upload_file "HMND001" 2024 12 "cash_flow" "HMND 2024 Cash Flow Statement.pdf"
upload_file "HMND001" 2025 4 "rent_roll" "Hammond Rent Roll April 2025.pdf"

# TCSH001 - Town Center Shopping
upload_file "TCSH001" 2023 12 "balance_sheet" "TCSH 2023 Balance Sheet.pdf"
upload_file "TCSH001" 2023 12 "income_statement" "TCSH 2023 Income Statement.pdf"
upload_file "TCSH001" 2023 12 "cash_flow" "TCSH 2023 Cash FLow Statement.pdf"
upload_file "TCSH001" 2024 12 "balance_sheet" "TCSH 2024 Balance Sheet.pdf"
upload_file "TCSH001" 2024 12 "income_statement" "TCSH 2024 Income Statement.pdf"
upload_file "TCSH001" 2024 12 "cash_flow" "TCSH 2024 Cash Flow Statement.pdf"
upload_file "TCSH001" 2025 4 "rent_roll" "TCSH Rent Roll April 2025.pdf"

# WEND001 - Wendover Commons
upload_file "WEND001" 2023 12 "balance_sheet" "Wendover Commons 2023 Balance Sheet.pdf"
upload_file "WEND001" 2023 12 "income_statement" "Wendover Commons 2023 Income Statement.pdf"
upload_file "WEND001" 2023 12 "cash_flow" "Wendover Commons 2023 Cash Flow Statement.pdf"
upload_file "WEND001" 2024 12 "balance_sheet" "Wendover Commons 2024 Balance Sheet.pdf"
upload_file "WEND001" 2024 12 "income_statement" "Wendover Commons 2024 Income Statement.pdf"
upload_file "WEND001" 2024 12 "cash_flow" "Wendover Commons 2024 Cash Flow Statement.pdf"
upload_file "WEND001" 2025 4 "rent_roll" "Wendover Rent Roll April 2025.pdf"

echo ""
echo -e "${CYAN}========================================${NC}"
echo "Total files: $upload_count"
echo -e "${GREEN}Successful: $success_count${NC}"
if [ $error_count -gt 0 ]; then
    echo -e "${YELLOW}Errors: $error_count${NC}"
fi
echo -e "${CYAN}========================================${NC}"
echo ""
echo "Note: Extraction is running in background via Celery."
echo "Check status with: docker logs reims-celery-worker -f"
echo ""

