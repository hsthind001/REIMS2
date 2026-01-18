
import sys
import os
from sqlalchemy import text
import pandas as pd

# Add app to path
sys.path.append(os.getcwd())

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

def check_documents():
    db = SessionLocal()
    try:
        print("Checking documents for ESP001...")
        prop = db.query(Property).filter(Property.property_code == 'ESP001').first()
        if not prop:
            print("Property ESP001 not found!")
            return

        print(f"Property ID: {prop.id}")

        docs = db.query(
            DocumentUpload.id,
            DocumentUpload.document_type,
            DocumentUpload.extraction_status,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            DocumentUpload.upload_date
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).filter(
            DocumentUpload.property_id == prop.id
        ).order_by(
            FinancialPeriod.period_year, FinancialPeriod.period_month
        ).all()

        if not docs:
            print("No documents found for ESP001.")
        else:
            print(f"Found {len(docs)} documents:")
            print(f"{'ID':<6} {'Year':<6} {'Month':<6} {'Type':<20} {'Status':<15} {'Upload Date'}")
            print("-" * 80)
            for d in docs:
                print(f"{d.id:<6} {d.period_year:<6} {d.period_month:<6} {d.document_type:<20} {d.extraction_status:<15} {d.upload_date}")

    finally:
        db.close()

if __name__ == "__main__":
    check_documents()
