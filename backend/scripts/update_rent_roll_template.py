#!/usr/bin/env python3
"""
Update Rent Roll Extraction Template to v2.0

Updates the extraction template record in the database with:
- All 24 field mappings
- Comprehensive validation rules
- Quality scoring thresholds  
- Auto-approve criteria
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.extraction_template import ExtractionTemplate


def update_rent_roll_template():
    """Update rent roll template to v2.0"""
    db = SessionLocal()
    
    try:
        # Find existing rent roll template
        template = db.query(ExtractionTemplate).filter(
            ExtractionTemplate.document_type == 'rent_roll'
        ).first()
        
        if not template:
            print("No existing rent roll template found. Creating new one...")
            template = ExtractionTemplate(
                document_type='rent_roll',
                template_name='Rent Roll v2.0',
                description='Comprehensive rent roll extraction template with 24 fields, validation, and quality scoring',
                is_default=True
            )
            db.add(template)
        else:
            print(f"Found existing template: {template.template_name}")
            template.template_name = 'Rent Roll v2.0'
            template.description = 'Comprehensive rent roll extraction template with 24 fields, validation, and quality scoring'
        
        # Update field mappings
        template.field_mappings = {
            "report_date": {
                "source": "header",
                "pattern": r"As of Date:\s*(\d{1,2}/\d{1,2}/\d{4})",
                "description": "Report date from document header",
                "required": True
            },
            "property_name": {
                "source": "header",
                "pattern": r"([A-Z][^(]+?)\s*\(([A-Z]{2,5})\)",
                "description": "Property name extracted from format 'Name (CODE)'",
                "required": True
            },
            "unit_number": {
                "column": "Unit(s)",
                "required": True,
                "description": "Physical unit identifier (may be multi-unit)"
            },
            "tenant_name": {
                "column": "Lease",
                "required": True,
                "description": "Tenant legal name (includes tenant ID)"
            },
            "tenant_id": {
                "pattern": r"\(t(\d+)\)",
                "description": "Tenant ID extracted from name (t0000xxx)"
            },
            "lease_type": {
                "column": "Lease Type",
                "description": "Retail NNN, Retail Gross, etc."
            },
            "area_sqft": {
                "column": "Area",
                "required": True,
                "description": "Rentable square footage"
            },
            "lease_from_date": {
                "column": "Lease From",
                "format": "MM/DD/YYYY",
                "description": "Lease commencement date"
            },
            "lease_to_date": {
                "column": "Lease To",
                "format": "MM/DD/YYYY",
                "description": "Lease expiration date (may be NULL for MTM)"
            },
            "term_months": {
                "column": "Term",
                "description": "Original lease term in months"
            },
            "tenancy_years": {
                "column": "Tenancy Years",
                "calculated": True,
                "formula": "years from lease_from to report_date",
                "description": "Years of occupancy"
            },
            "monthly_rent": {
                "column": "Monthly Rent",
                "required": True,
                "description": "Monthly base rent"
            },
            "monthly_rent_per_sf": {
                "column": "Monthly Rent/Area",
                "calculated": True,
                "formula": "monthly_rent / area_sqft",
                "description": "Monthly rent per SF"
            },
            "annual_rent": {
                "column": "Annual Rent",
                "calculated": True,
                "formula": "monthly_rent * 12",
                "description": "Annual base rent"
            },
            "annual_rent_per_sf": {
                "column": "Annual Rent/Area",
                "calculated": True,
                "formula": "annual_rent / area_sqft",
                "description": "Annual rent per SF"
            },
            "annual_recoveries_per_sf": {
                "column": "Annual Rec./Area",
                "description": "CAM + tax + insurance per SF"
            },
            "annual_misc_per_sf": {
                "column": "Annual Misc/Area",
                "description": "Miscellaneous charges per SF"
            },
            "security_deposit": {
                "column": "Security Deposit Received",
                "description": "Security deposit amount"
            },
            "loc_amount": {
                "column": "LOC Amount/ Bank Guarantee",
                "description": "Letter of credit amount"
            },
            "is_vacant": {
                "detection": "tenant_name == 'VACANT'",
                "description": "Flag for vacant units"
            },
            "is_gross_rent_row": {
                "detection": "'Gross Rent' in first column",
                "description": "Flag for gross rent calculation rows"
            },
            "parent_row_id": {
                "linkage": "previous non-gross row with same unit",
                "description": "Links gross rent rows to parent tenant"
            }
        }
        
        # Update validation rules
        template.validation_rules = {
            "annual_rent_check": {
                "rule": "annual_rent = monthly_rent * 12",
                "tolerance": "±2%",
                "severity": "CRITICAL",
                "description": "Annual rent must equal monthly times 12"
            },
            "rent_per_sf_check": {
                "rule": "monthly_rent_per_sf = monthly_rent / area_sqft",
                "tolerance": "±$0.05",
                "severity": "WARNING",
                "description": "Rent per SF calculation accuracy"
            },
            "date_sequence": {
                "rule": "lease_from <= report_date <= lease_to",
                "severity": "CRITICAL",
                "description": "Date sequence must be logical"
            },
            "term_calculation": {
                "rule": "term_months ≈ months between lease_from and lease_to",
                "tolerance": "±2 months",
                "severity": "WARNING",
                "description": "Term must match date range"
            },
            "tenancy_calculation": {
                "rule": "tenancy_years ≈ years from lease_from to report_date",
                "tolerance": "±0.5 years",
                "severity": "INFO",
                "description": "Tenancy years accuracy check"
            },
            "non_negative_values": {
                "rule": "All financial fields >= 0",
                "severity": "CRITICAL",
                "description": "Financial values must be non-negative"
            },
            "area_reasonable": {
                "rule": "0 <= area_sqft <= 100,000",
                "severity": "WARNING",
                "description": "Area must be within reasonable range"
            },
            "security_deposit_range": {
                "rule": "Typically 1-3 months of rent",
                "severity": "INFO",
                "description": "Security deposit reasonableness"
            },
            "expired_lease": {
                "rule": "Flag if lease_to < report_date",
                "severity": "WARNING",
                "description": "Detect holdover tenants"
            },
            "future_lease": {
                "rule": "Flag if lease_from > report_date",
                "severity": "INFO",
                "description": "Detect future leases"
            },
            "mtm_lease": {
                "rule": "Flag if lease_to is NULL",
                "severity": "INFO",
                "description": "Detect month-to-month leases"
            },
            "zero_rent": {
                "rule": "Flag if monthly_rent = 0",
                "severity": "INFO",
                "description": "Detect expense-only or abatement"
            },
            "zero_area": {
                "rule": "Flag if area_sqft = 0",
                "severity": "INFO",
                "description": "Detect ATM, signage, parking"
            },
            "short_term": {
                "rule": "Flag if term_months < 12",
                "severity": "WARNING",
                "description": "Detect short-term leases"
            },
            "long_term": {
                "rule": "Flag if term_months > 240",
                "severity": "INFO",
                "description": "Detect ground leases"
            },
            "unusual_rent_per_sf": {
                "rule": "Flag if < $0.50 or > $15.00",
                "severity": "WARNING",
                "description": "Detect unusual rent rates"
            },
            "multi_unit": {
                "rule": "Flag if ',' or multiple '-' in unit_number",
                "severity": "INFO",
                "description": "Detect multi-unit leases"
            },
            "special_unit": {
                "rule": "Flag if ATM, LAND, COMMON, SIGN in unit",
                "severity": "INFO",
                "description": "Detect special unit types"
            },
            "gross_rent_linkage": {
                "rule": "Gross rent rows must have parent_row_id",
                "severity": "WARNING",
                "description": "Ensure gross rent rows are linked"
            },
            "vacant_unit_check": {
                "rule": "Vacant units should have area but no rent",
                "severity": "WARNING",
                "description": "Validate vacant unit data"
            }
        }
        
        # Update quality thresholds
        template.quality_thresholds = {
            "auto_approve": {
                "score": 99.0,
                "criteria": [
                    "quality_score >= 99%",
                    "zero CRITICAL issues",
                    "all financial validations pass",
                    "all date validations pass"
                ],
                "description": "Automatically approve without human review"
            },
            "review_warnings": {
                "score": 98.0,
                "criteria": [
                    "98% <= quality_score < 99%",
                    "zero CRITICAL issues",
                    "minor warnings present"
                ],
                "description": "Review warnings but likely acceptable"
            },
            "review_required": {
                "score": 95.0,
                "criteria": [
                    "quality_score < 98%",
                    "OR any CRITICAL issues present"
                ],
                "description": "Human review required before approval"
            },
            "scoring_method": {
                "base_score": 100.0,
                "critical_penalty": -5.0,
                "warning_penalty": -1.0,
                "info_penalty": 0.0,
                "description": "Score calculation methodology"
            }
        }
        
        db.commit()
        
        print("\n✅ Rent roll template updated to v2.0!")
        print(f"   Template ID: {template.id}")
        print(f"   Name: {template.template_name}")
        print(f"   Field Mappings: {len(template.field_mappings)} fields")
        print(f"   Validation Rules: {len(template.validation_rules)} rules")
        print(f"   Quality Thresholds: {len(template.quality_thresholds)} thresholds")
        
        return template
    
    except Exception as e:
        db.rollback()
        print(f"✗ Error updating template: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == '__main__':
    print("="*60)
    print("RENT ROLL TEMPLATE UPDATE TO v2.0")
    print("="*60)
    update_rent_roll_template()

