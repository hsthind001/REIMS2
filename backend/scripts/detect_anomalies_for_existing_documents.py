#!/usr/bin/env python3
"""
Backfill anomaly detection for existing uploaded documents.

This script processes all existing document uploads and detects anomalies
in their financial data by comparing against historical periods.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.services.anomaly_detector import StatisticalAnomalyDetector
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from datetime import timedelta
import statistics
from sqlalchemy import text


def _coerce_numeric(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def detect_anomalies_for_document(db: Session, upload: DocumentUpload, detector: StatisticalAnomalyDetector):
    """Detect anomalies for a single document upload"""
    # Get the period for this upload
    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == upload.period_id
    ).first()
    
    if not period:
        return 0
    
    anomalies_created = 0
    
    # Detect anomalies based on document type
    if upload.document_type == 'income_statement':
        anomalies_created += detect_income_statement_anomalies(db, upload, period, detector)
    elif upload.document_type == 'balance_sheet':
        anomalies_created += detect_balance_sheet_anomalies(db, upload, period, detector)
    
    return anomalies_created

def detect_income_statement_anomalies(
    db: Session,
    upload: DocumentUpload,
    period: FinancialPeriod,
    detector: StatisticalAnomalyDetector
) -> int:
    """Detect anomalies in income statement data"""
    # Get current period data
    current_data = db.query(IncomeStatementData).filter(
        IncomeStatementData.property_id == upload.property_id,
        IncomeStatementData.period_id == upload.period_id
    ).all()
    
    if not current_data:
        return 0
    
    # Get historical periods (last 12 months)
    cutoff_date = period.period_end_date - timedelta(days=365)
    historical_periods = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == upload.property_id,
        FinancialPeriod.period_end_date >= cutoff_date,
        FinancialPeriod.period_end_date < period.period_end_date
    ).order_by(FinancialPeriod.period_end_date.desc()).limit(12).all()
    
    if len(historical_periods) < 3:
        return 0
    
    # Get historical data for key accounts
    historical_period_ids = [p.id for p in historical_periods]
    historical_data = db.query(IncomeStatementData).filter(
        IncomeStatementData.property_id == upload.property_id,
        IncomeStatementData.period_id.in_(historical_period_ids)
    ).all()
    
    # Group by account code
    account_groups = {}
    for item in current_data + historical_data:
        account_code = item.account_code
        if account_code not in account_groups:
            account_groups[account_code] = {'current': [], 'historical': []}
        
        if item.period_id == upload.period_id:
            account_groups[account_code]['current'].append(float(item.period_amount or 0))
        else:
            account_groups[account_code]['historical'].append(float(item.period_amount or 0))
    
    anomalies_created = 0
    
    # Detect anomalies for each account
    for account_code, data in account_groups.items():
        if not data['current'] or len(data['historical']) < 3:
            continue
        
        current_value = sum(data['current'])
        historical_values = data['historical']
        
        # Run anomaly detection
        result = detector.detect_anomalies(
            document_id=upload.id,
            field_name=account_code,
            current_value=current_value,
            historical_values=historical_values
        )
        
        # Create anomaly_detections records
        if result.get('anomalies'):
            for anomaly in result['anomalies']:
                create_anomaly_detection(
                    db=db,
                    upload=upload,
                    field_name=account_code,
                    field_value=str(current_value),
                    expected_value=str(statistics.mean(historical_values)),
                    anomaly_type=anomaly.get('type', 'statistical'),
                    severity=anomaly.get('severity', 'medium'),
                    z_score=anomaly.get('z_score'),
                    percentage_change=anomaly.get('percentage_change'),
                    confidence=0.85
                )
                anomalies_created += 1
    
    return anomalies_created

def detect_balance_sheet_anomalies(
    db: Session,
    upload: DocumentUpload,
    period: FinancialPeriod,
    detector: StatisticalAnomalyDetector
) -> int:
    """Detect anomalies in balance sheet data"""
    current_data = db.query(BalanceSheetData).filter(
        BalanceSheetData.property_id == upload.property_id,
        BalanceSheetData.period_id == upload.period_id
    ).all()
    
    if not current_data:
        return 0
    
    cutoff_date = period.period_end_date - timedelta(days=365)
    historical_periods = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == upload.property_id,
        FinancialPeriod.period_end_date >= cutoff_date,
        FinancialPeriod.period_end_date < period.period_end_date
    ).order_by(FinancialPeriod.period_end_date.desc()).limit(12).all()
    
    if len(historical_periods) < 3:
        return 0
    
    historical_period_ids = [p.id for p in historical_periods]
    historical_data = db.query(BalanceSheetData).filter(
        BalanceSheetData.property_id == upload.property_id,
        BalanceSheetData.period_id.in_(historical_period_ids)
    ).all()
    
    account_groups = {}
    for item in current_data + historical_data:
        account_code = item.account_code
        if account_code not in account_groups:
            account_groups[account_code] = {'current': [], 'historical': []}
        
        if item.period_id == upload.period_id:
            account_groups[account_code]['current'].append(float(item.amount or 0))
        else:
            account_groups[account_code]['historical'].append(float(item.amount or 0))
    
    anomalies_created = 0
    
    for account_code, data in account_groups.items():
        if not data['current'] or len(data['historical']) < 3:
            continue
        
        current_value = sum(data['current'])
        historical_values = data['historical']
        
        result = detector.detect_anomalies(
            document_id=upload.id,
            field_name=account_code,
            current_value=current_value,
            historical_values=historical_values
        )
        
        if result.get('anomalies'):
            for anomaly in result['anomalies']:
                create_anomaly_detection(
                    db=db,
                    upload=upload,
                    field_name=account_code,
                    field_value=str(current_value),
                    expected_value=str(statistics.mean(historical_values)),
                    anomaly_type=anomaly.get('type', 'statistical'),
                    severity=anomaly.get('severity', 'medium'),
                    z_score=anomaly.get('z_score'),
                    percentage_change=anomaly.get('percentage_change'),
                    confidence=0.85
                )
                anomalies_created += 1
    
    return anomalies_created

def create_anomaly_detection(
    db: Session,
    upload: DocumentUpload,
    field_name: str,
    field_value: str,
    expected_value: str,
    anomaly_type: str,
    severity: str,
    z_score: float = None,
    percentage_change: float = None,
    confidence: float = 0.85
):
    """Create an anomaly_detection record"""
    # Map severity to database values
    severity_map = {
        'critical': 'critical',
        'high': 'high',
        'medium': 'medium',
        'low': 'low'
    }
    db_severity = severity_map.get(severity.lower(), 'medium')
    
    # Check if anomaly already exists
    check_sql = text("""
        SELECT COUNT(*) FROM anomaly_detections
        WHERE document_id = :document_id
        AND field_name = :field_name
        AND anomaly_type = :anomaly_type
    """)
    try:
        result = db.execute(check_sql, {
            'document_id': upload.id,
            'field_name': field_name,
            'anomaly_type': anomaly_type
        })
        if result.scalar() > 0:
            return  # Already exists
    except Exception:
        db.rollback()
        raise
    
    # Insert anomaly detection record
    sql = text("""
        INSERT INTO anomaly_detections 
        (document_id, field_name, field_value, expected_value, anomaly_type, severity, confidence, z_score, percentage_change, detected_at)
        VALUES (:document_id, :field_name, :field_value, :expected_value, :anomaly_type, :severity, :confidence, :z_score, :percentage_change, NOW())
    """)
    
    try:
        db.execute(sql, {
            'document_id': upload.id,
            'field_name': field_name,
            'field_value': field_value[:500],
            'expected_value': expected_value[:500],
            'anomaly_type': anomaly_type,
            'severity': db_severity,
            'confidence': _coerce_numeric(confidence),
            'z_score': _coerce_numeric(z_score),
            'percentage_change': _coerce_numeric(percentage_change)
        })
        db.commit()
    except Exception:
        db.rollback()
        raise

def main():
    """Main function to process all documents"""
    db: Session = SessionLocal()
    try:
        detector = StatisticalAnomalyDetector(db)
        
        # Get all completed document uploads
        uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'completed',
            DocumentUpload.document_type.in_(['income_statement', 'balance_sheet'])
        ).all()
        
        print(f"Found {len(uploads)} documents to process")
        print("=" * 80)
        
        total_anomalies = 0
        for upload in uploads:
            try:
                anomalies = detect_anomalies_for_document(db, upload, detector)
                if anomalies > 0:
                    print(f"✓ {upload.file_name}: {anomalies} anomaly(ies) detected")
                    total_anomalies += anomalies
                else:
                    print(f"  {upload.file_name}: No anomalies detected")
            except Exception as e:
                print(f"✗ {upload.file_name}: Error - {str(e)}")
                continue
        
        print("\n" + "=" * 80)
        print(f"Total anomalies created: {total_anomalies}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
