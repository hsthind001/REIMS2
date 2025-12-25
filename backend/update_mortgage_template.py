#!/usr/bin/env python3
"""
Update Mortgage Extraction Template with Comprehensive Field Patterns
This script updates the existing mortgage_statement template in the database
with all 42 field patterns from the MortgageExtractionService default patterns.
"""

import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.extraction_template import ExtractionTemplate
from app.services.mortgage_extraction_service import MortgageExtractionService
import json


def main():
    db = SessionLocal()

    try:
        print("="*80)
        print("UPDATING MORTGAGE EXTRACTION TEMPLATE")
        print("="*80)

        # Get existing template
        template = db.query(ExtractionTemplate).filter(
            ExtractionTemplate.document_type == 'mortgage_statement',
            ExtractionTemplate.is_default == True
        ).first()

        if not template:
            print("\n✗ No mortgage_statement template found!")
            print("Creating new template...")
            template = ExtractionTemplate(
                template_name='standard_mortgage_statement',
                document_type='mortgage_statement',
                is_default=True,
                template_structure={}
            )
            db.add(template)

        print(f"\n✓ Found template: {template.template_name}")

        # Get comprehensive default patterns from service
        service = MortgageExtractionService(db)
        default_patterns = service._get_default_field_patterns()

        print(f"\n✓ Loaded {len(default_patterns)} comprehensive field patterns from service")

        # Update template structure
        template_structure = template.template_structure or {}

        # Keep existing field patterns and merge with defaults
        existing_patterns = template_structure.get('field_patterns', {})
        print(f"\n  Existing patterns in template: {len(existing_patterns)}")

        # Merge: defaults + existing (existing takes precedence if conflicts)
        merged_patterns = default_patterns.copy()
        merged_patterns.update(existing_patterns)  # Existing patterns override defaults

        template_structure['field_patterns'] = merged_patterns

        # Update required fields list
        required_fields = [
            'loan_number',
            'statement_date',
            'principal_balance',
            'total_payment_due',
            'payment_due_date',
            'interest_rate'
        ]
        template_structure['required_fields'] = required_fields

        # Update template
        template.template_structure = template_structure

        # Commit changes
        db.commit()

        print(f"\n✓ Updated template with {len(merged_patterns)} field patterns")
        print(f"✓ Set {len(required_fields)} required fields")

        # Verify update
        db.refresh(template)
        updated_patterns = template.template_structure.get('field_patterns', {})
        print(f"\n✓ Verification: Template now has {len(updated_patterns)} field patterns")

        # Show categories
        print(f"\nField Patterns by Category:")
        categories = {
            'Identification': ['loan_number', 'loan_type', 'borrower_name', 'property_address'],
            'Dates': ['statement_date', 'payment_due_date', 'maturity_date', 'origination_date'],
            'Balances': ['principal_balance', 'tax_escrow_balance', 'insurance_escrow_balance',
                        'reserve_balance', 'other_escrow_balance', 'suspense_balance'],
            'Payment Due': ['principal_due', 'interest_due', 'tax_escrow_due', 'insurance_escrow_due',
                           'reserve_due', 'late_fees', 'other_fees', 'total_payment_due'],
            'YTD': ['ytd_principal_paid', 'ytd_interest_paid', 'ytd_taxes_disbursed',
                   'ytd_insurance_disbursed', 'ytd_reserve_disbursed'],
            'Loan Terms': ['interest_rate', 'original_loan_amount', 'loan_term_months',
                          'payment_frequency', 'amortization_type'],
        }

        for category, fields in categories.items():
            count = sum(1 for f in fields if f in updated_patterns)
            print(f"  {category:20s}: {count:2d}/{len(fields):2d} patterns")

        print(f"\n{'='*80}")
        print("✓ TEMPLATE UPDATE COMPLETE")
        print("="*80)
        print("\nNext Steps:")
        print("1. Re-extract mortgage statements using updated template")
        print("2. Verify 100% field extraction")
        print("3. Check data quality scores")

    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
