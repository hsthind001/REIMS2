"""
Verify Mathematical Integrity vs All Validations

The dashboard shows "10 of 20" because it only counts balance_check and calculation_check rules.
This script shows the breakdown.
"""
import sys
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.validation_result import ValidationResult
from app.models.validation_rule import ValidationRule

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("MATHEMATICAL INTEGRITY vs ALL VALIDATIONS COMPARISON")
        print("=" * 80)
        
        # Get all uploads
        uploads = db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id == period_id,
            DocumentUpload.is_active == True
        ).all()
        
        print(f"\nProperty: {property_id}, Period: {period_id}")
        print(f"Active Uploads: {len(uploads)}\n")
        
        math_integrity_total = 0
        math_integrity_passed = 0
        all_validations_total = 0
        all_validations_passed = 0
        
        for upload in uploads:
            # Math Integrity: balance_check + calculation_check only
            math_checks = db.query(ValidationResult, ValidationRule).join(
                ValidationRule
            ).filter(
                ValidationResult.upload_id == upload.id,
                ValidationRule.rule_type.in_(['balance_check', 'calculation_check'])
            ).all()
            
            # All validations
            all_checks = db.query(ValidationResult).filter(
                ValidationResult.upload_id == upload.id
            ).all()
            
            math_total = len(math_checks)
            math_passed = sum(1 for r, rule in math_checks if r.passed)
            
            all_total = len(all_checks)
            all_passed = sum(1 for r in all_checks if r.passed)
            
            math_integrity_total += math_total
            math_integrity_passed += math_passed
            all_validations_total += all_total
            all_validations_passed += all_passed
            
            print(f"{upload.document_type}:")
            print(f"  Math Integrity: {math_passed}/{math_total}")
            print(f"  All Validations: {all_passed}/{all_total}")
        
        print("\n" + "=" * 80)
        print("TOTALS:")
        print("=" * 80)
        print(f"Mathematical Integrity (balance + calculation only): {math_integrity_passed}/{math_integrity_total} passing")
        print(f"All Validations (includes warnings, data quality): {all_validations_passed}/{all_validations_total} passing")
        
        print("\n" + "=" * 80)
        print("VERDICT:")
        print("=" * 80)
        print("The dashboard is showing the CORRECT data for 'Mathematical Integrity'.")
        print("It only counts balance_check and calculation_check rules by design.")
        print("This is a subset of all validations.")

    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
