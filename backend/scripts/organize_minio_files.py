#!/usr/bin/env python3
"""
MinIO File Organization Script

Uploads PDF files from /home/gurpyar/REIMS_Uploaded to MinIO with proper folder structure.
Organization: Property → Year → Document Type

Usage:
    python backend/scripts/organize_minio_files.py
"""

import sys
import os
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from minio import Minio
from minio.error import S3Error
from app.core.config import settings


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


# Property definitions (aligned with database)
PROPERTIES = {
    "ESP001": "Eastern-Shore-Plaza",
    "HMND001": "Hammond-Aire",
    "TCSH001": "The-Crossings",
    "WEND001": "Wendover-Commons"
}

# File mapping: source filename → (property_code, year, doc_type, dest_filename)
FILE_MAPPING = {
    # ESP001 - Eastern Shore Plaza
    "ESP 2023 Balance Sheet.pdf": ("ESP001", 2023, "balance-sheet", "ESP_2023_Balance_Sheet.pdf"),
    "ESP 2023 Cash Flow Statement.pdf": ("ESP001", 2023, "cash-flow", "ESP_2023_Cash_Flow_Statement.pdf"),
    "ESP 2023 Income Statement.pdf": ("ESP001", 2023, "income-statement", "ESP_2023_Income_Statement.pdf"),
    "ESP 2024 Balance Sheet.pdf": ("ESP001", 2024, "balance-sheet", "ESP_2024_Balance_Sheet.pdf"),
    "ESP 2024 Cash Flow Statement.pdf": ("ESP001", 2024, "cash-flow", "ESP_2024_Cash_Flow_Statement.pdf"),
    "ESP 2024 Income Statement.pdf": ("ESP001", 2024, "income-statement", "ESP_2024_Income_Statement.pdf"),
    "ESP Roll April 2025.pdf": ("ESP001", 2025, "rent-roll", "ESP_2025_Rent_Roll_April.pdf"),
    
    # HMND001 - Hammond Aire
    "Hammond Aire 2023 Balance Sheet.pdf": ("HMND001", 2023, "balance-sheet", "HMND_2023_Balance_Sheet.pdf"),
    "Hammond Aire 2023 Cash Flow Statement.pdf": ("HMND001", 2023, "cash-flow", "HMND_2023_Cash_Flow_Statement.pdf"),
    "Hammond Aire 2023 Income Statement.pdf": ("HMND001", 2023, "income-statement", "HMND_2023_Income_Statement.pdf"),
    "Hammond Aire2024 Balance Sheet.pdf": ("HMND001", 2024, "balance-sheet", "HMND_2024_Balance_Sheet.pdf"),
    "Hammond Aire 2024 Cash Flow Statement.pdf": ("HMND001", 2024, "cash-flow", "HMND_2024_Cash_Flow_Statement.pdf"),
    "Hammond Aire 2024 Income Statement.pdf": ("HMND001", 2024, "income-statement", "HMND_2024_Income_Statement.pdf"),
    "Hammond Rent Roll April 2025.pdf": ("HMND001", 2025, "rent-roll", "HMND_2025_Rent_Roll_April.pdf"),
    
    # TCSH001 - The Crossings of Spring Hill
    "TCSH 2023 Balance Sheet.pdf": ("TCSH001", 2023, "balance-sheet", "TCSH_2023_Balance_Sheet.pdf"),
    "TCSH 2023 Cash FLow Statement.pdf": ("TCSH001", 2023, "cash-flow", "TCSH_2023_Cash_Flow_Statement.pdf"),
    "TCSH 2023 Income Statement.pdf": ("TCSH001", 2023, "income-statement", "TCSH_2023_Income_Statement.pdf"),
    "TCSH 2024 Balance Sheet.pdf": ("TCSH001", 2024, "balance-sheet", "TCSH_2024_Balance_Sheet.pdf"),
    "TCSH 2024 Cash Flow Statement.pdf": ("TCSH001", 2024, "cash-flow", "TCSH_2024_Cash_Flow_Statement.pdf"),
    "TCSH 2024 Income Statement.pdf": ("TCSH001", 2024, "income-statement", "TCSH_2024_Income_Statement.pdf"),
    "TCSH Rent Roll April 2025.pdf": ("TCSH001", 2025, "rent-roll", "TCSH_2025_Rent_Roll_April.pdf"),
    
    # WEND001 - Wendover Commons
    "Wendover Commons 2023 Balance Sheet.pdf": ("WEND001", 2023, "balance-sheet", "WEND_2023_Balance_Sheet.pdf"),
    "Wendover Commons 2023 Cash Flow Statement.pdf": ("WEND001", 2023, "cash-flow", "WEND_2023_Cash_Flow_Statement.pdf"),
    "Wendover Commons 2023 Income Statement.pdf": ("WEND001", 2023, "income-statement", "WEND_2023_Income_Statement.pdf"),
    "Wendover Commons 2024 Balance Sheet.pdf": ("WEND001", 2024, "balance-sheet", "WEND_2024_Balance_Sheet.pdf"),
    "Wendover Commons 2024 Cash Flow Statement.pdf": ("WEND001", 2024, "cash-flow", "WEND_2024_Cash_Flow_Statement.pdf"),
    "Wendover Commons 2024 Income Statement.pdf": ("WEND001", 2024, "income-statement", "WEND_2024_Income_Statement.pdf"),
    "Wendover Rent Roll April 2025.pdf": ("WEND001", 2025, "rent-roll", "WEND_2025_Rent_Roll_April.pdf"),
}


def get_minio_client():
    """Create MinIO client"""
    try:
        client = Minio(
            "localhost:9000",
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        return client
    except Exception as e:
        print(f"{Colors.RED}Error connecting to MinIO: {e}{Colors.ENDC}")
        sys.exit(1)


def ensure_bucket_exists(client, bucket_name):
    """Ensure bucket exists, create if not"""
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"{Colors.GREEN}✅ Created bucket: {bucket_name}{Colors.ENDC}")
        else:
            print(f"{Colors.BLUE}ℹ️  Bucket '{bucket_name}' already exists{Colors.ENDC}")
        return True
    except S3Error as e:
        print(f"{Colors.RED}❌ Error with bucket: {e}{Colors.ENDC}")
        return False


def upload_files(client, bucket_name, source_dir, dry_run=False):
    """Upload files to MinIO with organized structure"""
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Uploading Files to MinIO{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")
    
    uploaded_count = 0
    skipped_count = 0
    error_count = 0
    
    for source_filename, (prop_code, year, doc_type, dest_filename) in FILE_MAPPING.items():
        source_path = os.path.join(source_dir, source_filename)
        
        # Check if source file exists
        if not os.path.exists(source_path):
            print(f"{Colors.YELLOW}⚠️  File not found: {source_filename}{Colors.ENDC}")
            skipped_count += 1
            continue
        
        # Build destination path
        prop_name = PROPERTIES[prop_code]
        dest_path = f"{prop_code}-{prop_name}/{year}/{doc_type}/{dest_filename}"
        
        # Get file size
        file_size = os.path.getsize(source_path) / 1024  # KB
        
        if dry_run:
            print(f"{Colors.CYAN}[DRY RUN]{Colors.ENDC} Would upload:")
            print(f"  Source: {source_filename} ({file_size:.1f} KB)")
            print(f"  Dest:   {dest_path}")
            uploaded_count += 1
        else:
            try:
                # Upload file
                client.fput_object(
                    bucket_name,
                    dest_path,
                    source_path,
                    content_type="application/pdf"
                )
                print(f"{Colors.GREEN}✅{Colors.ENDC} {source_filename}")
                print(f"   → {dest_path} ({file_size:.1f} KB)")
                uploaded_count += 1
            except S3Error as e:
                print(f"{Colors.RED}❌ Error uploading {source_filename}: {e}{Colors.ENDC}")
                error_count += 1
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Upload Summary:{Colors.ENDC}")
    print(f"  {Colors.GREEN}✅ Uploaded: {uploaded_count}{Colors.ENDC}")
    print(f"  {Colors.YELLOW}⚠️  Skipped: {skipped_count}{Colors.ENDC}")
    print(f"  {Colors.RED}❌ Errors: {error_count}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    return uploaded_count, skipped_count, error_count


def list_bucket_contents(client, bucket_name):
    """List all objects in bucket to verify upload"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}Bucket Contents:{Colors.ENDC}\n")
    
    try:
        objects = client.list_objects(bucket_name, recursive=True)
        count = 0
        
        current_property = None
        for obj in objects:
            # Parse path
            parts = obj.object_name.split('/')
            if len(parts) >= 3:
                property_folder = parts[0]
                year = parts[1]
                doc_type = parts[2]
                filename = parts[3] if len(parts) > 3 else ''
                
                # Print property header
                if property_folder != current_property:
                    current_property = property_folder
                    print(f"\n{Colors.BOLD}{Colors.CYAN}{property_folder}/{Colors.ENDC}")
                
                # Print file
                if filename and not filename.startswith('.'):
                    print(f"  {year}/{doc_type}/{filename}")
                    count += 1
        
        print(f"\n{Colors.BOLD}Total files: {count}{Colors.ENDC}\n")
        return count
    except S3Error as e:
        print(f"{Colors.RED}Error listing bucket: {e}{Colors.ENDC}")
        return 0


def main():
    """Main function"""
    source_dir = "/home/gurpyar/REIMS_Uploaded"
    bucket_name = "reims"
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'*'*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}      MinIO File Organization - REIMS2{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'*'*60}{Colors.ENDC}\n")
    
    print(f"Source Directory: {source_dir}")
    print(f"MinIO Bucket: {bucket_name}")
    print(f"Total Files to Upload: {len(FILE_MAPPING)}\n")
    
    # Check if source directory exists
    if not os.path.exists(source_dir):
        print(f"{Colors.RED}❌ Source directory not found: {source_dir}{Colors.ENDC}")
        sys.exit(1)
    
    # Get MinIO client
    print("Connecting to MinIO...")
    client = get_minio_client()
    print(f"{Colors.GREEN}✅ Connected to MinIO{Colors.ENDC}\n")
    
    # Ensure bucket exists
    if not ensure_bucket_exists(client, bucket_name):
        sys.exit(1)
    
    # Check for dry run argument
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}DRY RUN MODE - No files will be uploaded{Colors.ENDC}\n")
    
    # Upload files
    uploaded, skipped, errors = upload_files(client, bucket_name, source_dir, dry_run)
    
    if not dry_run and uploaded > 0:
        # List bucket contents to verify
        list_bucket_contents(client, bucket_name)
    
    # Success message
    if errors == 0 and uploaded > 0:
        print(f"{Colors.BOLD}{Colors.GREEN}🎉 All files organized successfully!{Colors.ENDC}\n")
        print(f"View in MinIO Console: http://localhost:9001/browser/reims\n")
        sys.exit(0)
    elif dry_run:
        print(f"{Colors.BOLD}{Colors.CYAN}Dry run complete. Run without --dry-run to upload.{Colors.ENDC}\n")
        sys.exit(0)
    else:
        print(f"{Colors.BOLD}{Colors.RED}❌ Upload completed with errors{Colors.ENDC}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

