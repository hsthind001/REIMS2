#!/usr/bin/env python3
"""
Script to update existing anomaly detection confidence scores
based on extraction confidence from the database.

This script recalculates confidence for all existing anomalies
using the new logic: extraction confidence >= 95% = 100%, otherwise use actual extraction confidence.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Change to backend directory to ensure imports work
os.chdir(backend_path)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from decimal import Decimal

def update_anomaly_confidence():
    """Update confidence scores for all existing anomaly detections"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get all anomaly detections
        anomalies_query = text("""
            SELECT 
                ad.id,
                ad.document_id,
                ad.field_name,
                du.document_type
            FROM anomaly_detections ad
            JOIN document_uploads du ON ad.document_id = du.id
        """)
        
        anomalies = db.execute(anomalies_query).fetchall()
        
        print(f"Found {len(anomalies)} anomaly detection records to update")
        
        updated_count = 0
        not_found_count = 0
        error_count = 0
        
        for anomaly in anomalies:
            anomaly_id = anomaly.id
            document_id = anomaly.document_id
            field_name = anomaly.field_name
            document_type = anomaly.document_type
            
            try:
                # Query extraction confidence based on document type
                extraction_confidence = None
                
                if document_type == 'income_statement':
                    query = text("""
                        SELECT AVG(extraction_confidence) as avg_confidence
                        FROM income_statement_data
                        WHERE upload_id = :upload_id
                        AND account_code = :field_name
                        AND extraction_confidence IS NOT NULL
                    """)
                    result = db.execute(query, {
                        'upload_id': document_id,
                        'field_name': field_name
                    }).fetchone()
                    
                    if result and result.avg_confidence:
                        extraction_confidence = float(result.avg_confidence)
                        
                elif document_type == 'balance_sheet':
                    query = text("""
                        SELECT AVG(extraction_confidence) as avg_confidence
                        FROM balance_sheet_data
                        WHERE upload_id = :upload_id
                        AND account_code = :field_name
                        AND extraction_confidence IS NOT NULL
                    """)
                    result = db.execute(query, {
                        'upload_id': document_id,
                        'field_name': field_name
                    }).fetchone()
                    
                    if result and result.avg_confidence:
                        extraction_confidence = float(result.avg_confidence)
                        
                elif document_type == 'cash_flow':
                    query = text("""
                        SELECT AVG(extraction_confidence) as avg_confidence
                        FROM cash_flow_data
                        WHERE upload_id = :upload_id
                        AND account_code = :field_name
                        AND extraction_confidence IS NOT NULL
                    """)
                    result = db.execute(query, {
                        'upload_id': document_id,
                        'field_name': field_name
                    }).fetchone()
                    
                    if result and result.avg_confidence:
                        extraction_confidence = float(result.avg_confidence)
                
                # Calculate new confidence
                if extraction_confidence is not None:
                    # Convert from 0-100 scale to 0-1 scale
                    confidence_decimal = extraction_confidence / 100.0
                    
                    # If extraction confidence >= 95%, set to 100% (1.0)
                    if confidence_decimal >= 0.95:
                        new_confidence = Decimal('1.0')
                    else:
                        new_confidence = Decimal(str(confidence_decimal))
                    
                    # Update the anomaly record
                    update_query = text("""
                        UPDATE anomaly_detections
                        SET confidence = :confidence
                        WHERE id = :anomaly_id
                    """)
                    
                    db.execute(update_query, {
                        'confidence': new_confidence,
                        'anomaly_id': anomaly_id
                    })
                    
                    updated_count += 1
                    if updated_count % 10 == 0:
                        print(f"Updated {updated_count} records...")
                else:
                    not_found_count += 1
                    # Keep existing confidence if extraction confidence not found
                    # (or set to default 0.85 if you want)
                    
            except Exception as e:
                error_count += 1
                print(f"Error updating anomaly {anomaly_id}: {str(e)}")
        
        # Commit all changes
        db.commit()
        
        print(f"\n✅ Update complete!")
        print(f"   Updated: {updated_count} records")
        print(f"   Not found (kept existing): {not_found_count} records")
        print(f"   Errors: {error_count} records")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Updating anomaly detection confidence scores...")
    print("   Using extraction confidence from database")
    print()
    update_anomaly_confidence()

