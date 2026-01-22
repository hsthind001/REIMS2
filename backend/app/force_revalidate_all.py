"""
Force Re-run All Validations for Property 11, Period 169

This script will re-trigger all validations to update the cached results
displayed on the Mathematical Integrity dashboard.
"""
import sys
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.services.validation_service import ValidationService

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("RE-RUNNING ALL VALIDATIONS FOR MATHEMATICAL INTEGRITY DASHBOARD")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # Get all active uploads for this property/period
        uploads = db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id == period_id,
            DocumentUpload.is_active == True
        ).all()
        
        print(f"Found {len(uploads)} active document uploads\n")
        
        validation_service = ValidationService(db)
        
        for upload in uploads:
            print(f"\nValidating: {upload.document_type}")
            print(f"  File: {upload.file_name}")
            print(f"  Upload ID: {upload.id}")
            
            results = validation_service.validate_upload(upload.id)
            
            print(f"  ✅ {results['passed_checks']}/{results['total_checks']} checks passed")
            if results['failed_checks'] > 0:
                print(f"  ❌ {results['failed_checks']} failures")
                print(f"  ⚠️  {results['warnings']} warnings")
        
        print("\n" + "=" * 80)
        print("VALIDATION RE-RUN COMPLETE")
        print("=" * 80)
        print("\nRefresh the Mathematical Integrity dashboard to see updated results.")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
