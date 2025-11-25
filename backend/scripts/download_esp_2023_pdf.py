#!/usr/bin/env python3
"""
Quick script to download ESP 2023 Income Statement regenerated PDF
"""
import sys
import os
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod


def main():
    print("=" * 60)
    print("ESP 2023 Income Statement PDF Downloader")
    print("=" * 60)
    
    # Find upload
    db = SessionLocal()
    try:
        upload = db.query(DocumentUpload).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).filter(
            Property.property_code.ilike("%esp%"),
            FinancialPeriod.period_year == 2023,
            FinancialPeriod.period_month == 12,
            DocumentUpload.document_type == "income_statement"
        ).order_by(
            DocumentUpload.id.desc()
        ).first()
        
        if not upload:
            print("❌ No ESP 2023 Income Statement found!")
            print("\nAvailable uploads:")
            all_uploads = db.query(DocumentUpload).join(Property).join(FinancialPeriod).filter(
                DocumentUpload.document_type == "income_statement"
            ).limit(10).all()
            
            for u in all_uploads:
                prop = db.query(Property).filter(Property.id == u.property_id).first()
                period = db.query(FinancialPeriod).filter(FinancialPeriod.id == u.period_id).first()
                print(f"  - Upload ID: {u.id}, Property: {prop.property_code if prop else 'N/A'}, "
                      f"Period: {period.period_year if period else 'N/A'}-{period.period_month if period else 'N/A':02d}")
            return
        
        upload_id = upload.id
        prop = db.query(Property).filter(Property.id == upload.property_id).first()
        period = db.query(FinancialPeriod).filter(FinancialPeriod.id == upload.period_id).first()
        
        print(f"✅ Found upload!")
        print(f"   Upload ID: {upload_id}")
        print(f"   Property: {prop.property_name if prop else 'N/A'}")
        print(f"   Period: {period.period_year if period else 'N/A'}-{period.period_month if period else 'N/A':02d}")
        print(f"   Status: {upload.extraction_status}")
        print()
        
    finally:
        db.close()
    
    # Download PDF
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/v1/documents/uploads/{upload_id}/regenerate-pdf"
    output_file = f"regenerated_ESP_2023_Income_Statement_{upload_id}.pdf"
    
    print(f"📥 Downloading PDF...")
    print(f"   URL: {url}")
    print(f"   Output: {output_file}")
    print()
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r   Progress: {percent:.1f}% ({downloaded:,}/{total_size:,} bytes)", end='', flush=True)
        
        print(f"\n\n✅ Success!")
        print(f"📄 File saved to: {os.path.abspath(output_file)}")
        print(f"📊 File size: {os.path.getsize(output_file):,} bytes")
        print()
        print("You can now compare this with the original PDF to verify extraction accuracy!")
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: Could not connect to API at {base_url}")
        print("   Make sure the backend server is running!")
        print("   Start it with: cd backend && uvicorn app.main:app --reload")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()

