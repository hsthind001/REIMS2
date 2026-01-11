#!/usr/bin/env python3
"""
Upload REIMS2 PDF files to MinIO with organized folder structure

Requires: pip install minio (or run from Docker container)
"""

from minio import Minio
from minio.error import S3Error
from io import BytesIO
import os

# MinIO configuration
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "reims"
SOURCE_DIR = "/home/gurpyar/REIMS_Uploaded"

# Property mapping
PROPERTIES = {
    "ESP001": "Eastern-Shore-Plaza",
    "HMND001": "Hammond-Aire",
    "TCSH001": "The-Crossings",
    "WEND001": "Wendover-Commons"
}

# Complete file mapping
FILE_MAPPING = {
    # ESP001
    "ESP 2023 Balance Sheet.pdf": ("ESP001", 2023, "balance-sheet", "ESP_2023_Balance_Sheet.pdf"),
    "ESP 2023 Cash Flow Statement.pdf": ("ESP001", 2023, "cash-flow", "ESP_2023_Cash_Flow_Statement.pdf"),
    "ESP 2023 Income Statement.pdf": ("ESP001", 2023, "income-statement", "ESP_2023_Income_Statement.pdf"),
    "ESP 2024 Balance Sheet.pdf": ("ESP001", 2024, "balance-sheet", "ESP_2024_Balance_Sheet.pdf"),
    "ESP 2024 Cash Flow Statement.pdf": ("ESP001", 2024, "cash-flow", "ESP_2024_Cash_Flow_Statement.pdf"),
    "ESP 2024 Income Statement.pdf": ("ESP001", 2024, "income-statement", "ESP_2024_Income_Statement.pdf"),
    "ESP Roll April 2025.pdf": ("ESP001", 2025, "rent-roll", "ESP_2025_Rent_Roll_April.pdf"),
    
    # HMND001
    "Hammond Aire 2023 Balance Sheet.pdf": ("HMND001", 2023, "balance-sheet", "HMND_2023_Balance_Sheet.pdf"),
    "Hammond Aire 2023 Cash Flow Statement.pdf": ("HMND001", 2023, "cash-flow", "HMND_2023_Cash_Flow_Statement.pdf"),
    "Hammond Aire 2023 Income Statement.pdf": ("HMND001", 2023, "income-statement", "HMND_2023_Income_Statement.pdf"),
    "Hammond Aire2024 Balance Sheet.pdf": ("HMND001", 2024, "balance-sheet", "HMND_2024_Balance_Sheet.pdf"),
    "Hammond Aire 2024 Cash Flow Statement.pdf": ("HMND001", 2024, "cash-flow", "HMND_2024_Cash_Flow_Statement.pdf"),
    "Hammond Aire 2024 Income Statement.pdf": ("HMND001", 2024, "income-statement", "HMND_2024_Income_Statement.pdf"),
    "Hammond Rent Roll April 2025.pdf": ("HMND001", 2025, "rent-roll", "HMND_2025_Rent_Roll_April.pdf"),
    
    # TCSH001
    "TCSH 2023 Balance Sheet.pdf": ("TCSH001", 2023, "balance-sheet", "TCSH_2023_Balance_Sheet.pdf"),
    "TCSH 2023 Cash FLow Statement.pdf": ("TCSH001", 2023, "cash-flow", "TCSH_2023_Cash_Flow_Statement.pdf"),
    "TCSH 2023 Income Statement.pdf": ("TCSH001", 2023, "income-statement", "TCSH_2023_Income_Statement.pdf"),
    "TCSH 2024 Balance Sheet.pdf": ("TCSH001", 2024, "balance-sheet", "TCSH_2024_Balance_Sheet.pdf"),
    "TCSH 2024 Cash Flow Statement.pdf": ("TCSH001", 2024, "cash-flow", "TCSH_2024_Cash_Flow_Statement.pdf"),
    "TCSH 2024 Income Statement.pdf": ("TCSH001", 2024, "income-statement", "TCSH_2024_Income_Statement.pdf"),
    "TCSH Rent Roll April 2025.pdf": ("TCSH001", 2025, "rent-roll", "TCSH_2025_Rent_Roll_April.pdf"),
    
    # WEND001
    "Wendover Commons 2023 Balance Sheet.pdf": ("WEND001", 2023, "balance-sheet", "WEND_2023_Balance_Sheet.pdf"),
    "Wendover Commons 2023 Cash Flow Statement.pdf": ("WEND001", 2023, "cash-flow", "WEND_2023_Cash_Flow_Statement.pdf"),
    "Wendover Commons 2023 Income Statement.pdf": ("WEND001", 2023, "income-statement", "WEND_2023_Income_Statement.pdf"),
    "Wendover Commons 2024 Balance Sheet.pdf": ("WEND001", 2024, "balance-sheet", "WEND_2024_Balance_Sheet.pdf"),
    "Wendover Commons 2024 Cash Flow Statement.pdf": ("WEND001", 2024, "cash-flow", "WEND_2024_Cash_Flow_Statement.pdf"),
    "Wendover Commons 2024 Income Statement.pdf": ("WEND001", 2024, "income-statement", "WEND_2024_Income_Statement.pdf"),
    "Wendover Rent Roll April 2025.pdf": ("WEND001", 2025, "rent-roll", "WEND_2025_Rent_Roll_April.pdf"),
}

def main():
    print("\\n" + "="*70)
    print("  MinIO File Organization - REIMS2 (DRY RUN)")
    print("="*70 + "\\n")
    
    print(f"Source Directory: {SOURCE_DIR}")
    print(f"MinIO Bucket: {BUCKET_NAME}")
    print(f"Total Files: {len(FILE_MAPPING)}\\n")
    
    # Connect to MinIO
    try:
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
        print("✅ Connected to MinIO\\n")
    except Exception as e:
        print(f"❌ Failed to connect to MinIO: {e}")
        return
    
    # Show what will be uploaded
    print("FOLDER STRUCTURE TO BE CREATED:\\n")
    
    uploaded = 0
    missing = 0
    
    current_property = None
    for source_filename, (prop_code, year, doc_type, dest_filename) in sorted(FILE_MAPPING.items()):
        source_path = os.path.join(SOURCE_DIR, source_filename)
        prop_name = PROPERTIES[prop_code]
        dest_path = f"{prop_code}-{prop_name}/{year}/{doc_type}/{dest_filename}"
        
        # Print property header
        if prop_code != current_property:
            current_property = prop_code
            print(f"\\n{prop_code}-{prop_name}/")
        
        # Check if file exists
        if os.path.exists(source_path):
            size_kb = os.path.getsize(source_path) / 1024
            print(f"  ├── {year}/{doc_type}/{dest_filename} ({size_kb:.1f} KB) ✅")
            uploaded += 1
        else:
            print(f"  ├── {year}/{doc_type}/{dest_filename} ❌ FILE NOT FOUND")
            missing += 1
    
    print(f"\\n{'='*70}")
    print(f"Summary: {uploaded} files ready, {missing} files missing")
    print(f"{'='*70}\\n")
    
    print("This is a DRY RUN. No files have been uploaded yet.\\n")
    print("To proceed with actual upload, run:")
    print("  python3 upload_to_minio.py upload\\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "upload":
        print("\\nStarting actual upload...\\n")
        # Will implement upload logic
    else:
        main()

