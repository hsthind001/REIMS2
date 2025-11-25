#!/usr/bin/env python3
"""
Script to download regenerated income statement PDF from database

Usage:
    python scripts/download_regenerated_pdf.py <upload_id>
    python scripts/download_regenerated_pdf.py --property esp --year 2023 --month 12
"""
import sys
import os
import argparse
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod


def find_upload_id(property_code: str, year: int, month: int, db: Session) -> int:
    """Find upload_id for a specific property and period"""
    upload = db.query(DocumentUpload).join(
        Property, DocumentUpload.property_id == Property.id
    ).join(
        FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
    ).filter(
        Property.property_code == property_code.upper(),
        FinancialPeriod.period_year == year,
        FinancialPeriod.period_month == month,
        DocumentUpload.document_type == "income_statement"
    ).order_by(
        DocumentUpload.id.desc()
    ).first()
    
    if not upload:
        raise ValueError(f"No income statement found for {property_code} {year}-{month:02d}")
    
    return upload.id


def download_regenerated_pdf(upload_id: int, output_path: str = None, base_url: str = "http://localhost:8000"):
    """
    Download regenerated PDF from API
    
    Args:
        upload_id: Document upload ID
        output_path: Output file path (optional)
        base_url: API base URL
    """
    url = f"{base_url}/api/v1/documents/uploads/{upload_id}/regenerate-pdf"
    
    print(f"Downloading regenerated PDF for upload_id {upload_id}...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get filename from Content-Disposition header or use default
        if output_path is None:
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            else:
                filename = f"regenerated_income_statement_{upload_id}.pdf"
            output_path = filename
        
        # Download file
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
        
        print(f"\n✅ PDF downloaded successfully!")
        print(f"📄 File saved to: {os.path.abspath(output_path)}")
        print(f"📊 File size: {os.path.getsize(output_path):,} bytes")
        
        return output_path
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading PDF: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Download regenerated income statement PDF from database"
    )
    parser.add_argument(
        'upload_id',
        type=int,
        nargs='?',
        help='Document upload ID'
    )
    parser.add_argument(
        '--property',
        type=str,
        help='Property code (e.g., esp, wend001)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Period year (e.g., 2023)'
    )
    parser.add_argument(
        '--month',
        type=int,
        help='Period month (1-12)'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output file path (optional)'
    )
    parser.add_argument(
        '--url',
        type=str,
        default='http://localhost:8000',
        help='API base URL (default: http://localhost:8000)'
    )
    
    args = parser.parse_args()
    
    # Determine upload_id
    upload_id = args.upload_id
    
    if not upload_id:
        if args.property and args.year and args.month:
            print(f"Looking up upload_id for {args.property} {args.year}-{args.month:02d}...")
            db = SessionLocal()
            try:
                upload_id = find_upload_id(args.property, args.year, args.month, db)
                print(f"✅ Found upload_id: {upload_id}")
            finally:
                db.close()
        else:
            parser.error("Either upload_id or --property/--year/--month must be provided")
    
    # Download PDF
    try:
        download_regenerated_pdf(upload_id, args.output, args.url)
    except Exception as e:
        print(f"\n❌ Failed to download PDF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

