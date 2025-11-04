"""
Sample Data Seeding Script

Loads the 28 annual PDF files from /home/gurpyar/REIMS_Uploaded/uploads/Sampledata
into the REIMS2 database.

Features:
- Idempotent (safe to run multiple times)
- Creates properties if missing
- Creates financial periods automatically
- Uploads PDFs via API
- Monitors extraction progress
- Generates summary report

Usage:
    python scripts/seed_sample_data.py --all
    python scripts/seed_sample_data.py --property ESP001
    python scripts/seed_sample_data.py --year 2024
    python scripts/seed_sample_data.py --dry-run
"""

import os
import sys
import argparse
import time
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import date

# Add parent directory to path to import seed_properties
sys.path.insert(0, str(Path(__file__).parent.parent))

from seed_properties import PROPERTIES, get_property_by_code


# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
SAMPLE_DATA_DIR = "/home/gurpyar/REIMS_Uploaded/uploads/Sampledata"


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def create_property(property_data: Dict) -> Optional[int]:
    """Create a property via API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/properties/",
            json=property_data,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"Created property: {property_data['property_code']} - {property_data['property_name']}")
            return data['id']
        elif response.status_code == 400 and "already exists" in response.text:
            print_info(f"Property {property_data['property_code']} already exists, fetching ID...")
            # Get existing property
            return get_property_id(property_data['property_code'])
        else:
            print_error(f"Failed to create property {property_data['property_code']}: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Error creating property {property_data['property_code']}: {str(e)}")
        return None


def get_property_id(property_code: str) -> Optional[int]:
    """Get property ID by property code"""
    try:
        response = requests.get(f"{API_BASE_URL}/properties/{property_code}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['id']
        return None
    except Exception as e:
        print_error(f"Error getting property ID for {property_code}: {str(e)}")
        return None


def parse_filename(filename: str) -> Optional[Dict]:
    """
    Parse PDF filename to extract property, year, and document type
    
    Examples:
        "ESP 2024 Balance Sheet.pdf" -> {property: ESP, year: 2024, type: balance_sheet}
        "Hammond Aire 2023 Income Statement.pdf" -> {property: HMND, year: 2023, type: income_statement}
        "TCSH 2024 Cash Flow Statement.pdf" -> {property: TCSH, year: 2024, type: cash_flow}
        "Wendover Rent Roll April 2025.pdf" -> {property: WEND, year: 2025, month: 4, type: rent_roll}
    """
    original_filename = filename
    filename = filename.replace(".pdf", "")
    
    # Extract property code
    property_code = None
    if filename.startswith("ESP") or "ESP" in filename:
        property_code = "ESP001"
    elif "Hammond" in filename or "HMND" in filename:
        property_code = "HMND001"
    elif filename.startswith("TCSH") or "TCSH" in filename:
        property_code = "TCSH001"
    elif "Wendover" in filename or "WEND" in filename:
        property_code = "WEND001"
    
    if not property_code:
        return None
    
    # Extract year (handle both spaced and non-spaced formats)
    year = None
    import re
    year_match = re.search(r'(20\d{2})', filename)
    if year_match:
        year = int(year_match.group(1))
    
    if not year:
        return None
    
    # Extract month (for rent rolls)
    month = None
    months = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    for month_name, month_num in months.items():
        if month_name in filename:
            month = month_num
            break
    
    # Extract document type
    document_type = None
    if "Balance Sheet" in filename:
        document_type = "balance_sheet"
    elif "Income Statement" in filename or "Income" in filename:
        document_type = "income_statement"
    elif "Cash Flow" in filename or "Cash FLow" in filename:  # Handle typo
        document_type = "cash_flow"
    elif "Rent Roll" in filename or " Roll " in filename or filename.endswith(" Roll"):
        document_type = "rent_roll"
    
    if not document_type:
        return None
    
    return {
        "property_code": property_code,
        "year": year,
        "month": month or 12,  # Default to December for annual files
        "document_type": document_type,
        "filename": filename + ".pdf"
    }


def upload_document(property_code: str, year: int, month: int, 
                    document_type: str, file_path: str, dry_run: bool = False) -> Optional[Dict]:
    """Upload a document via API"""
    if dry_run:
        print_info(f"[DRY RUN] Would upload: {property_code} {year}-{month:02d} {document_type}")
        return {"success": True, "dry_run": True}
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            data = {
                'property_code': property_code,
                'period_year': year,
                'period_month': month,
                'document_type': document_type
            }
            
            response = requests.post(
                f"{API_BASE_URL}/documents/upload",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                print_success(f"Uploaded: {property_code} {year}-{month:02d} {document_type}")
                return result
            else:
                print_error(f"Upload failed ({response.status_code}): {property_code} {year}-{month:02d} {document_type}")
                print_error(f"Response: {response.text[:200]}")
                return None
    except Exception as e:
        print_error(f"Error uploading {property_code} {year}-{month:02d} {document_type}: {str(e)}")
        return None


def check_task_status(task_id: str, max_wait: int = 60) -> Dict:
    """Monitor Celery task until completion"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE_URL}/tasks/{task_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                if status == 'SUCCESS':
                    return {'status': 'completed', 'result': data.get('result')}
                elif status in ['FAILURE', 'REVOKED']:
                    return {'status': 'failed', 'error': data.get('error')}
                
                # Still processing
                time.sleep(2)
            else:
                time.sleep(2)
        except Exception as e:
            print_warning(f"Error checking task status: {str(e)}")
            time.sleep(2)
    
    return {'status': 'timeout'}


def load_sample_data(property_filter: Optional[str] = None, 
                     year_filter: Optional[int] = None,
                     dry_run: bool = False):
    """Main function to load all sample data"""
    
    print_header("REIMS2 Sample Data Loader")
    
    # Step 1: Create properties
    print_header("Step 1: Creating Properties")
    
    properties_to_load = PROPERTIES
    if property_filter:
        properties_to_load = [p for p in PROPERTIES if p['property_code'] == property_filter]
        if not properties_to_load:
            print_error(f"Property {property_filter} not found in definitions")
            return
    
    property_ids = {}
    for prop in properties_to_load:
        if not dry_run:
            prop_id = create_property(prop)
            if prop_id:
                property_ids[prop['property_code']] = prop_id
        else:
            print_info(f"[DRY RUN] Would create property: {prop['property_code']}")
    
    # Step 2: Scan sample data directory
    print_header("Step 2: Scanning Sample Data Directory")
    
    if not os.path.exists(SAMPLE_DATA_DIR):
        print_error(f"Sample data directory not found: {SAMPLE_DATA_DIR}")
        return
    
    pdf_files = sorted([f for f in os.listdir(SAMPLE_DATA_DIR) if f.endswith('.pdf')])
    print_info(f"Found {len(pdf_files)} PDF files")
    
    # Step 3: Parse and upload files
    print_header("Step 3: Uploading Documents")
    
    upload_results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for pdf_file in pdf_files:
        parsed = parse_filename(pdf_file)
        
        if not parsed:
            print_warning(f"Could not parse filename: {pdf_file}")
            upload_results['skipped'] += 1
            continue
        
        # Apply filters
        if property_filter and parsed['property_code'] != property_filter:
            upload_results['skipped'] += 1
            continue
        
        if year_filter and parsed['year'] != year_filter:
            upload_results['skipped'] += 1
            continue
        
        upload_results['total'] += 1
        
        file_path = os.path.join(SAMPLE_DATA_DIR, pdf_file)
        
        result = upload_document(
            parsed['property_code'],
            parsed['year'],
            parsed['month'],
            parsed['document_type'],
            file_path,
            dry_run
        )
        
        if result:
            upload_results['success'] += 1
            
            # Monitor extraction task if not dry run
            if not dry_run and 'task_id' in result:
                print_info(f"  Monitoring extraction task {result['task_id']}...")
                task_result = check_task_status(result['task_id'], max_wait=120)
                
                if task_result['status'] == 'completed':
                    print_success(f"  Extraction completed successfully")
                elif task_result['status'] == 'failed':
                    print_error(f"  Extraction failed: {task_result.get('error')}")
                else:
                    print_warning(f"  Extraction status: {task_result['status']}")
        else:
            upload_results['failed'] += 1
        
        # Small delay between uploads
        if not dry_run:
            time.sleep(1)
    
    # Step 4: Summary
    print_header("Summary")
    print(f"Total files processed: {upload_results['total']}")
    print_success(f"Successfully uploaded: {upload_results['success']}")
    if upload_results['failed'] > 0:
        print_error(f"Failed uploads: {upload_results['failed']}")
    if upload_results['skipped'] > 0:
        print_info(f"Skipped (filtered): {upload_results['skipped']}")
    
    print(f"\n{Colors.BOLD}Done! ✨{Colors.ENDC}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Load REIMS2 sample data')
    parser.add_argument('--all', action='store_true', help='Load all sample data')
    parser.add_argument('--property', type=str, help='Load data for specific property (e.g., ESP001)')
    parser.add_argument('--year', type=int, help='Load data for specific year (e.g., 2024)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually doing it')
    
    args = parser.parse_args()
    
    if not args.all and not args.property and not args.year:
        parser.print_help()
        print(f"\n{Colors.WARNING}Please specify --all, --property, or --year{Colors.ENDC}\n")
        sys.exit(1)
    
    load_sample_data(
        property_filter=args.property,
        year_filter=args.year,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

