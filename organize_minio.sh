#!/bin/bash

# MinIO File Organization Script for REIMS2
# Uploads PDF files with Property → Year → Document Type structure

set -e

SOURCE_DIR="/home/gurpyar/REIMS_Uploaded"
BUCKET="reims"

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║         MinIO File Organization - REIMS2                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Source: $SOURCE_DIR"
echo "Bucket: $BUCKET"
echo "Organization: Property → Year → Document Type"
echo ""

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Count total files
TOTAL_FILES=$(ls "$SOURCE_DIR"/*.pdf 2>/dev/null | wc -l)
echo "Total PDF files found: $TOTAL_FILES"
echo ""

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo "❌ No PDF files found in $SOURCE_DIR"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "UPLOADING FILES TO MINIO..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Upload function using Python in container
docker exec reims-backend python3 << 'EOFPYTHON'
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import subprocess
import os

client = Minio("minio:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
bucket = "reims"

# Property mapping
PROPERTIES = {
    "ESP001": "Eastern-Shore-Plaza",
    "HMND001": "Hammond-Aire",
    "TCSH001": "The-Crossings",
    "WEND001": "Wendover-Commons"
}

# File mapping
mappings = [
    ("ESP 2023 Balance Sheet.pdf", "ESP001", 2023, "balance-sheet", "ESP_2023_Balance_Sheet.pdf"),
    ("ESP 2023 Cash Flow Statement.pdf", "ESP001", 2023, "cash-flow", "ESP_2023_Cash_Flow_Statement.pdf"),
    ("ESP 2023 Income Statement.pdf", "ESP001", 2023, "income-statement", "ESP_2023_Income_Statement.pdf"),
    ("ESP 2024 Balance Sheet.pdf", "ESP001", 2024, "balance-sheet", "ESP_2024_Balance_Sheet.pdf"),
    ("ESP 2024 Cash Flow Statement.pdf", "ESP001", 2024, "cash-flow", "ESP_2024_Cash_Flow_Statement.pdf"),
    ("ESP 2024 Income Statement.pdf", "ESP001", 2024, "income-statement", "ESP_2024_Income_Statement.pdf"),
    ("ESP Roll April 2025.pdf", "ESP001", 2025, "rent-roll", "ESP_2025_Rent_Roll_April.pdf"),
    
    ("Hammond Aire 2023 Balance Sheet.pdf", "HMND001", 2023, "balance-sheet", "HMND_2023_Balance_Sheet.pdf"),
    ("Hammond Aire 2023 Cash Flow Statement.pdf", "HMND001", 2023, "cash-flow", "HMND_2023_Cash_Flow_Statement.pdf"),
    ("Hammond Aire 2023 Income Statement.pdf", "HMND001", 2023, "income-statement", "HMND_2023_Income_Statement.pdf"),
    ("Hammond Aire2024 Balance Sheet.pdf", "HMND001", 2024, "balance-sheet", "HMND_2024_Balance_Sheet.pdf"),
    ("Hammond Aire 2024 Cash Flow Statement.pdf", "HMND001", 2024, "cash-flow", "HMND_2024_Cash_Flow_Statement.pdf"),
    ("Hammond Aire 2024 Income Statement.pdf", "HMND001", 2024, "income-statement", "HMND_2024_Income_Statement.pdf"),
    ("Hammond Rent Roll April 2025.pdf", "HMND001", 2025, "rent-roll", "HMND_2025_Rent_Roll_April.pdf"),
    
    ("TCSH 2023 Balance Sheet.pdf", "TCSH001", 2023, "balance-sheet", "TCSH_2023_Balance_Sheet.pdf"),
    ("TCSH 2023 Cash FLow Statement.pdf", "TCSH001", 2023, "cash-flow", "TCSH_2023_Cash_Flow_Statement.pdf"),
    ("TCSH 2023 Income Statement.pdf", "TCSH001", 2023, "income-statement", "TCSH_2023_Income_Statement.pdf"),
    ("TCSH 2024 Balance Sheet.pdf", "TCSH001", 2024, "balance-sheet", "TCSH_2024_Balance_Sheet.pdf"),
    ("TCSH 2024 Cash Flow Statement.pdf", "TCSH001", 2024, "cash-flow", "TCSH_2024_Cash_Flow_Statement.pdf"),
    ("TCSH 2024 Income Statement.pdf", "TCSH001", 2024, "income-statement", "TCSH_2024_Income_Statement.pdf"),
    ("TCSH Rent Roll April 2025.pdf", "TCSH001", 2025, "rent-roll", "TCSH_2025_Rent_Roll_April.pdf"),
    
    ("Wendover Commons 2023 Balance Sheet.pdf", "WEND001", 2023, "balance-sheet", "WEND_2023_Balance_Sheet.pdf"),
    ("Wendover Commons 2023 Cash Flow Statement.pdf", "WEND001", 2023, "cash-flow", "WEND_2023_Cash_Flow_Statement.pdf"),
    ("Wendover Commons 2023 Income Statement.pdf", "WEND001", 2023, "income-statement", "WEND_2023_Income_Statement.pdf"),
    ("Wendover Commons 2024 Balance Sheet.pdf", "WEND001", 2024, "balance-sheet", "WEND_2024_Balance_Sheet.pdf"),
    ("Wendover Commons 2024 Cash Flow Statement.pdf", "WEND001", 2024, "cash-flow", "WEND_2024_Cash_Flow_Statement.pdf"),
    ("Wendover Commons 2024 Income Statement.pdf", "WEND001", 2024, "income-statement", "WEND_2024_Income_Statement.pdf"),
    ("Wendover Rent Roll April 2025.pdf", "WEND001", 2025, "rent-roll", "WEND_2025_Rent_Roll_April.pdf"),
]

uploaded = 0
total = len(mappings)

print(f"Uploading {total} files to MinIO bucket '{bucket}'...")
print()

EOFPYTHON

# Now upload files one by one using docker cp + Python
UPLOADED=0
FAILED=0

for file in "$SOURCE_DIR"/*.pdf; do
    filename=$(basename "$file")
    
    # Copy file to container /tmp
    docker cp "$file" reims-backend:/tmp/ 2>/dev/null
    
    if [ $? -eq 0 ]; then
        ((UPLOADED++))
        echo "✅ Copied: $filename"
    else
        ((FAILED++))
        echo "❌ Failed: $filename"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Files copied to container: $UPLOADED"
echo "Failed: $FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Now organizing in MinIO..."
echo ""

# Run Python upload script in container
docker exec reims-backend bash << 'EOFBASH'
python3 << 'EOFPYTHON'
from minio import Minio
import os

client = Minio("minio:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
bucket = "reims"

# Property mapping
PROPERTIES = {
    "ESP001": "Eastern-Shore-Plaza",
    "HMND001": "Hammond-Aire",
    "TCSH001": "The-Crossings",
    "WEND001": "Wendover-Commons"
}

# Complete file mapping
mappings = [
    ("ESP 2023 Balance Sheet.pdf", "ESP001", 2023, "balance-sheet", "ESP_2023_Balance_Sheet.pdf"),
    ("ESP 2023 Cash Flow Statement.pdf", "ESP001", 2023, "cash-flow", "ESP_2023_Cash_Flow_Statement.pdf"),
    ("ESP 2023 Income Statement.pdf", "ESP001", 2023, "income-statement", "ESP_2023_Income_Statement.pdf"),
    ("ESP 2024 Balance Sheet.pdf", "ESP001", 2024, "balance-sheet", "ESP_2024_Balance_Sheet.pdf"),
    ("ESP 2024 Cash Flow Statement.pdf", "ESP001", 2024, "cash-flow", "ESP_2024_Cash_Flow_Statement.pdf"),
    ("ESP 2024 Income Statement.pdf", "ESP001", 2024, "income-statement", "ESP_2024_Income_Statement.pdf"),
    ("ESP Roll April 2025.pdf", "ESP001", 2025, "rent-roll", "ESP_2025_Rent_Roll_April.pdf"),
    ("Hammond Aire 2023 Balance Sheet.pdf", "HMND001", 2023, "balance-sheet", "HMND_2023_Balance_Sheet.pdf"),
    ("Hammond Aire 2023 Cash Flow Statement.pdf", "HMND001", 2023, "cash-flow", "HMND_2023_Cash_Flow_Statement.pdf"),
    ("Hammond Aire 2023 Income Statement.pdf", "HMND001", 2023, "income-statement", "HMND_2023_Income_Statement.pdf"),
    ("Hammond Aire2024 Balance Sheet.pdf", "HMND001", 2024, "balance-sheet", "HMND_2024_Balance_Sheet.pdf"),
    ("Hammond Aire 2024 Cash Flow Statement.pdf", "HMND001", 2024, "cash-flow", "HMND_2024_Cash_Flow_Statement.pdf"),
    ("Hammond Aire 2024 Income Statement.pdf", "HMND001", 2024, "income-statement", "HMND_2024_Income_Statement.pdf"),
    ("Hammond Rent Roll April 2025.pdf", "HMND001", 2025, "rent-roll", "HMND_2025_Rent_Roll_April.pdf"),
    ("TCSH 2023 Balance Sheet.pdf", "TCSH001", 2023, "balance-sheet", "TCSH_2023_Balance_Sheet.pdf"),
    ("TCSH 2023 Cash FLow Statement.pdf", "TCSH001", 2023, "cash-flow", "TCSH_2023_Cash_Flow_Statement.pdf"),
    ("TCSH 2023 Income Statement.pdf", "TCSH001", 2023, "income-statement", "TCSH_2023_Income_Statement.pdf"),
    ("TCSH 2024 Balance Sheet.pdf", "TCSH001", 2024, "balance-sheet", "TCSH_2024_Balance_Sheet.pdf"),
    ("TCSH 2024 Cash Flow Statement.pdf", "TCSH001", 2024, "cash-flow", "TCSH_2024_Cash_Flow_Statement.pdf"),
    ("TCSH 2024 Income Statement.pdf", "TCSH001", 2024, "income-statement", "TCSH_2024_Income_Statement.pdf"),
    ("TCSH Rent Roll April 2025.pdf", "TCSH001", 2025, "rent-roll", "TCSH_2025_Rent_Roll_April.pdf"),
    ("Wendover Commons 2023 Balance Sheet.pdf", "WEND001", 2023, "balance-sheet", "WEND_2023_Balance_Sheet.pdf"),
    ("Wendover Commons 2023 Cash Flow Statement.pdf", "WEND001", 2023, "cash-flow", "WEND_2023_Cash_Flow_Statement.pdf"),
    ("Wendover Commons 2023 Income Statement.pdf", "WEND001", 2023, "income-statement", "WEND_2023_Income_Statement.pdf"),
    ("Wendover Commons 2024 Balance Sheet.pdf", "WEND001", 2024, "balance-sheet", "WEND_2024_Balance_Sheet.pdf"),
    ("Wendover Commons 2024 Cash Flow Statement.pdf", "WEND001", 2024, "cash-flow", "WEND_2024_Cash_Flow_Statement.pdf"),
    ("Wendover Commons 2024 Income Statement.pdf", "WEND001", 2024, "income-statement", "WEND_2024_Income_Statement.pdf"),
    ("Wendover Rent Roll April 2025.pdf", "WEND001", 2025, "rent-roll", "WEND_2025_Rent_Roll_April.pdf"),
]

uploaded = 0
current_prop = None

for source_name, prop_code, year, doc_type, dest_name in mappings:
    prop_name = PROPERTIES[prop_code]
    dest_path = f"{prop_code}-{prop_name}/{year}/{doc_type}/{dest_name}"
    temp_path = f"/tmp/{dest_name}"
    
    # Print property header
    if prop_code != current_prop:
        current_prop = prop_code
        print(f"\n{prop_code}-{prop_name}/")
    
    # Check if source file exists
    if not os.path.exists(f"/tmp/{source_name}"):
        print(f"  ❌ Missing: {source_name}")
        continue
    
    try:
        # Upload to MinIO
        client.fput_object(bucket, dest_path, f"/tmp/{source_name}", content_type="application/pdf")
        size_kb = os.path.getsize(f"/tmp/{source_name}") / 1024
        print(f"  ✅ {year}/{doc_type}/{dest_name} ({size_kb:.1f} KB)")
        uploaded += 1
    except Exception as e:
        print(f"  ❌ Error: {dest_name} - {e}")

print(f"\n✅ Uploaded {uploaded} files to MinIO")
print(f"\nView at: http://localhost:9001/browser/reims")

EOFPYTHON
EOFBASH

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    UPLOAD COMPLETE ✅                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "MinIO Console: http://localhost:9001"
echo "Username: minioadmin"
echo "Password: minioadmin"
echo ""

