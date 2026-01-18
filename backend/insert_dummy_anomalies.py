
import sys
import os
from datetime import datetime
from sqlalchemy import text
from decimal import Decimal

# Add app to path
sys.path.append(os.getcwd())

from app.db.database import SessionLocal
from app.models.anomaly_detection import AnomalyDetection, AnomalyCategory, AnomalyDirection, BaselineType, PatternType
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

def insert_dummies():
    db = SessionLocal()
    try:
        # Get Property 11 (ESP001)
        prop = db.query(Property).filter(Property.id == 11).first()
        if not prop:
            print("Property 11 not found, trying ESP001")
            prop = db.query(Property).filter(Property.property_code == 'ESP001').first()
        
        if not prop:
            print("Property not found. Aborting.")
            return

        print(f"Using Property: {prop.property_name} (ID: {prop.id})")

        # Get or Create Period (Dec 2024)
        period = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == prop.id,
            FinancialPeriod.period_year == 2024,
            FinancialPeriod.period_month == 12
        ).first()

        if not period:
            print("Creating dummy period 2024-12...")
            period = FinancialPeriod(
                property_id=prop.id,
                period_year=2024,
                period_month=12,
                is_closed=False
            )
            db.add(period)
            db.commit()
            db.refresh(period)

        # Get or Create Dummy Document
        doc = db.query(DocumentUpload).filter(
            DocumentUpload.property_id == prop.id,
            DocumentUpload.period_id == period.id,
            DocumentUpload.document_type == 'balance_sheet'
        ).first()

        if not doc:
            print("Creating dummy document record...")
            doc = DocumentUpload(
                property_id=prop.id,
                period_id=period.id,
                document_type='balance_sheet',
                filename='dummy_balance_sheet.pdf',
                file_path='minio://dummy/path',
                extraction_status='completed',
                uploaded_by=1 
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
        
        print(f"Using Document ID: {doc.id}")

        # Insert Anomaly 1: Critical Accounting Issue
        a1 = AnomalyDetection(
            document_id=doc.id,
            field_name="Gross Potential Rent",
            field_value="150000.00",
            expected_value="165000.00",
            z_score=3.5,
            percentage_change=-9.1,
            anomaly_type="statistical",
            severity="critical",
            confidence=0.98,
            anomaly_score=95.0,
            impact_amount=15000.00,
            direction=AnomalyDirection.DOWN,
            baseline_type=BaselineType.PEER_GROUP,
            anomaly_category=AnomalyCategory.PERFORMANCE,
            pattern_type=PatternType.TREND,
            metadata_json={
                "account_code": "5000-0000",
                "account_name": "Gross Potential Rent",
                "reason": "Significant deviation from peer group average"
            }
        )
        db.add(a1)

        # Insert Anomaly 2: Data Quality
        a2 = AnomalyDetection(
            document_id=doc.id,
            field_name="Utilities Expense",
            field_value="12000.00",
            expected_value="4000.00",
            z_score=4.2,
            percentage_change=200.0,
            anomaly_type="ml",
            severity="high",
            confidence=0.85,
            anomaly_score=85.0,
            impact_amount=8000.00,
            direction=AnomalyDirection.UP,
            baseline_type=BaselineType.SEASONAL,
            anomaly_category=AnomalyCategory.ACCOUNTING,
            pattern_type=PatternType.POINT,
            metadata_json={
                "account_code": "6000-1000",
                "account_name": "Utilities - Water",
                "reason": "Spike exceeding historical seasonal maximum"
            }
        )
        db.add(a2)

        # Insert Anomaly 3: Minor Formatting
        a3 = AnomalyDetection(
            document_id=doc.id,
            field_name="Common Area Maint",
            field_value="0.00",
            expected_value="1500.00",
            z_score=1.5,
            percentage_change=-100.0,
            anomaly_type="missing_data",
            severity="medium",
            confidence=0.75,
            anomaly_score=60.0,
            impact_amount=1500.00,
            direction=AnomalyDirection.DOWN,
            baseline_type=BaselineType.MEAN,
            anomaly_category=AnomalyCategory.DATA_QUALITY,
            pattern_type=PatternType.POINT,
            metadata_json={
                "account_code": "6100-0000",
                "account_name": "CAM Expenses",
                "reason": "Unexpected zero value"
            }
        )
        db.add(a3)

        db.commit()
        print("Successfully inserted 3 dummy anomalies.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    insert_dummies()
