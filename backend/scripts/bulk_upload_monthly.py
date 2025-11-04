"""
Monthly Bulk Upload Tool

Uploads monthly financial documents following the naming convention:
{PropertyCode}_{Year}_{Month:02d}_{DocumentType}.pdf

Examples:
    ESP001_2024_01_balance_sheet.pdf
    ESP001_2024_01_income_statement.pdf
    ESP001_2024_01_cash_flow.pdf

Usage:
    python scripts/bulk_upload_monthly.py --directory /path/to/monthly/files
    python scripts/bulk_upload_monthly.py --directory /path --property ESP001 --year 2024
    python scripts/bulk_upload_monthly.py --directory /path --dry-run
"""

import os
import sys
import argparse
import time
import requests
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# ANSI Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def parse_monthly_filename(filename: str) -> Optional[Dict]:
    """
    Parse monthly filename format: {PropertyCode}_{Year}_{Month:02d}_{DocumentType}.pdf
    
    Returns dict with property_code, year, month, document_type or None if invalid
    """
    pattern = r'([A-Z]+\d{3})_(\d{4})_(\d{2})_(balance_sheet|income_statement|cash_flow|rent_roll)\.pdf'
    match = re.match(pattern, filename)
    
    if match:
        property_code, year, month, doc_type = match.groups()
        return {
            'property_code': property_code,
            'year': int(year),
            'month': int(month),
            'document_type': doc_type,
            'filename': filename
        }
    return None


def upload_document(property_code: str, year: int, month: int,
                    document_type: str, file_path: str) -> Optional[Dict]:
    """Upload document via API"""
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
                return response.json()
            else:
                print(f"{Colors.RED}✗ Upload failed: {response.status_code}{Colors.END}")
                return None
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.END}")
        return None


def analyze_directory(directory: str, property_filter: Optional[str] = None,
                      year_filter: Optional[int] = None) -> Dict:
    """Analyze directory and report on what files are present"""
    
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    
    parsed_files = []
    invalid_files = []
    
    for filename in files:
        parsed = parse_monthly_filename(filename)
        if parsed:
            # Apply filters
            if property_filter and parsed['property_code'] != property_filter:
                continue
            if year_filter and parsed['year'] != year_filter:
                continue
            parsed_files.append(parsed)
        else:
            invalid_files.append(filename)
    
    # Group by property, year, month
    structure = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for parsed in parsed_files:
        prop = parsed['property_code']
        year = parsed['year']
        month = parsed['month']
        doc_type = parsed['document_type']
        structure[prop][year][month].append(doc_type)
    
    return {
        'parsed_files': parsed_files,
        'invalid_files': invalid_files,
        'structure': structure
    }


def print_analysis(analysis: Dict):
    """Print analysis of directory contents"""
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}Directory Analysis{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")
    
    print(f"Total valid files: {Colors.GREEN}{len(analysis['parsed_files'])}{Colors.END}")
    print(f"Invalid filenames: {Colors.RED}{len(analysis['invalid_files'])}{Colors.END}\n")
    
    if analysis['invalid_files']:
        print(f"{Colors.YELLOW}Invalid files (wrong naming format):{Colors.END}")
        for f in analysis['invalid_files'][:10]:  # Show first 10
            print(f"  - {f}")
        if len(analysis['invalid_files']) > 10:
            print(f"  ... and {len(analysis['invalid_files']) - 10} more")
        print()
    
    # Show structure
    structure = analysis['structure']
    for prop in sorted(structure.keys()):
        print(f"{Colors.BOLD}Property: {prop}{Colors.END}")
        for year in sorted(structure[prop].keys()):
            months_with_data = sorted(structure[prop][year].keys())
            print(f"  Year {year}: {len(months_with_data)} months")
            
            # Check for gaps
            if months_with_data:
                missing_months = set(range(1, 13)) - set(months_with_data)
                if missing_months:
                    print(f"    {Colors.YELLOW}Missing months: {sorted(missing_months)}{Colors.END}")
                
                # Check for incomplete months (missing document types)
                for month in months_with_data:
                    doc_types = structure[prop][year][month]
                    expected = {'balance_sheet', 'income_statement', 'cash_flow'}
                    missing = expected - set(doc_types)
                    if missing:
                        print(f"    {Colors.YELLOW}Month {month:02d}: Missing {missing}{Colors.END}")
        print()


def bulk_upload(directory: str, property_filter: Optional[str] = None,
                year_filter: Optional[int] = None, dry_run: bool = False):
    """Main bulk upload function"""
    
    print(f"\n{Colors.BOLD}Monthly Bulk Upload Tool{Colors.END}\n")
    print(f"Directory: {directory}")
    if property_filter:
        print(f"Property filter: {property_filter}")
    if year_filter:
        print(f"Year filter: {year_filter}")
    print(f"Dry run: {dry_run}\n")
    
    # Analyze directory
    analysis = analyze_directory(directory, property_filter, year_filter)
    print_analysis(analysis)
    
    if dry_run:
        print(f"\n{Colors.CYAN}Dry run complete. No files uploaded.{Colors.END}\n")
        return
    
    # Proceed with upload
    print(f"\n{Colors.BOLD}Starting upload...{Colors.END}\n")
    
    results = {
        'success': 0,
        'failed': 0,
        'total': len(analysis['parsed_files'])
    }
    
    for i, parsed in enumerate(analysis['parsed_files'], 1):
        file_path = os.path.join(directory, parsed['filename'])
        
        print(f"[{i}/{results['total']}] Uploading {parsed['property_code']} " +
              f"{parsed['year']}-{parsed['month']:02d} {parsed['document_type']}... ", end='')
        
        result = upload_document(
            parsed['property_code'],
            parsed['year'],
            parsed['month'],
            parsed['document_type'],
            file_path
        )
        
        if result:
            print(f"{Colors.GREEN}✓{Colors.END}")
            results['success'] += 1
        else:
            results['failed'] += 1
        
        time.sleep(0.5)  # Rate limiting
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}Upload Summary{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
    print(f"Total files: {results['total']}")
    print(f"{Colors.GREEN}Successful: {results['success']}{Colors.END}")
    if results['failed'] > 0:
        print(f"{Colors.RED}Failed: {results['failed']}{Colors.END}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Bulk upload monthly financial documents')
    parser.add_argument('--directory', '-d', required=True, help='Directory containing monthly PDF files')
    parser.add_argument('--property', help='Filter by property code (e.g., ESP001)')
    parser.add_argument('--year', type=int, help='Filter by year (e.g., 2024)')
    parser.add_argument('--dry-run', action='store_true', help='Analyze only, do not upload')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"{Colors.RED}Error: Directory not found: {args.directory}{Colors.END}")
        sys.exit(1)
    
    bulk_upload(args.directory, args.property, args.year, args.dry_run)


if __name__ == "__main__":
    main()

