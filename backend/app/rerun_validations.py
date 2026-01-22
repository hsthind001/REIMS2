"""
Re-run Validation for Income Statement

This script re-runs validation for the Income Statement upload to update
the cached validation results after the repair.
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
        print("RE-RUNNING INCOME STATEMENT VALIDATIONS")
        print("=" * 80)
        
        # Find the Income Statement upload for this property/period
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id == period_id,
            DocumentUpload.document_type == "income_statement",
            DocumentUpload.is_active == True
        ).first()
        
        if not upload:
            print("ERROR: No active Income Statement upload found!")
            return
        
        print(f"Found upload ID: {upload.id}")
        print(f"File: {upload.file_name}")
        print(f"Uploaded: {upload.upload_date}")
        print()
        
        # Re-run validations
        print("Running validations...")
        validation_service = ValidationService(db)
        results = validation_service.validate_upload(upload.id)
        
        print("\n" + "=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)
        print(f"Total Checks: {results['total_checks']}")
        print(f"Passed: {results['passed_checks']} ✅")
        print(f"Failed: {results['failed_checks']} ❌")
        print(f"Warnings: {results['warnings']} ⚠️")
        print(f"Errors: {results['errors']} 🔴")
        
        if results['failed_checks'] > 0:
            print("\n\nFailed Checks:")
            for result in results['validation_results']:
                if not result['passed']:
                    print(f"  - {result.get('severity', 'ERROR')}: {result.get('error_message', 'Unknown error')}")
        else:
            print("\n🎉 ALL VALIDATIONS PASSED!")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
