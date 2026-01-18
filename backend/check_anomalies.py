
import sys
import os
from sqlalchemy import text, func

# Add app to path
sys.path.append(os.getcwd())

from app.db.database import SessionLocal
from app.models.anomaly_detection import AnomalyDetection
from app.models.committee_alert import CommitteeAlert
from app.models.property import Property
from app.models.organization import Organization
from app.models.document_upload import DocumentUpload

def check_data():
    db = SessionLocal()
    try:
        print("--- Organizations ---")
        orgs = db.query(Organization).all()
        for org in orgs:
            print(f"ID: {org.id}, Name: {org.name}")

        print("\n--- Properties ---")
        props = db.query(Property).all()
        for prop in props:
            print(f"ID: {prop.id}, Code: {prop.property_code}, OrgID: {prop.organization_id}")

        print("\n--- Anomalies Count ---")
        anomaly_count = db.query(func.count(AnomalyDetection.id)).scalar()
        print(f"Total Anomalies: {anomaly_count}")

        print("\n--- Alerts Count ---")
        alert_count = db.query(func.count(CommitteeAlert.id)).scalar()
        print(f"Total Alerts: {alert_count}")
        
        if anomaly_count == 0:
            print("\nWARNING: No anomalies found in the database. Detection might not have run.")
        else:
            # Show a few anomalies
            print("\n--- Sample Anomalies ---")
            anomalies = db.query(
                AnomalyDetection.id, 
                AnomalyDetection.anomaly_category, 
                AnomalyDetection.severity,
                DocumentUpload.property_id
            ).join(
                DocumentUpload, AnomalyDetection.document_id == DocumentUpload.id
            ).limit(5).all()
            
            for a in anomalies:
                print(f"ID: {a.id}, Cat: {a.anomaly_category}, Sev: {a.severity}, PropID: {a.property_id}")

    finally:
        db.close()

if __name__ == "__main__":
    check_data()
