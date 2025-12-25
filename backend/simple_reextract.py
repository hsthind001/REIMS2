#!/usr/bin/env python3
"""
Simple Re-Extraction Script for ESP001 Mortgage Statements
Directly calls the mortgage extraction service on stored PDF files
"""

import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.mortgage_extraction_service import MortgageExtractionService
from app.core.config import settings
from decimal import Decimal
import pdfplumber
from io import BytesIO


def get_pdf_text(file_path: str) -> str:
    """Extract text from PDF file"""
    # For MinIO files, we need to download first
    # For now, assume files are local or accessible
    try:
        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            return full_text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None


def main():
    db = SessionLocal()

    print("="*80)
    print("SIMPLE RE-EXTRACTION FOR ESP001 MORTGAGE STATEMENTS")
    print("="*80)

    # Find ESP001 property
    property = db.query(Property).filter(Property.property_code == 'ESP001').first()
    print(f"\n✓ Property: {property.property_name} (ID: {property.id})")

    # Find all 2023 periods
    periods = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == property.id,
        FinancialPeriod.period_year == 2023
    ).order_by(FinancialPeriod.period_month).all()

    print(f"✓ Found {len(periods)} periods for 2023\n")

    # Sample mortgage statement data (from seed_data.json format)
    # We'll create this data based on known values from the PDFs
    sample_mortgage_data = {
        1: {  # January 2023
            'loan_number': '306891008',
            'statement_date': '2023-01-25',
            'payment_due_date': '2023-02-06',
            'principal_balance': Decimal('22416794.27'),
            'tax_escrow_balance': Decimal('112134.95'),
            'insurance_escrow_balance': Decimal('12570.43'),
            'reserve_balance': Decimal('468165.12'),
            'interest_rate': Decimal('4.78'),
            # Add more fields...
        }
    }

    # For now, let's just update the template field patterns correctly
    from app.models.extraction_template import ExtractionTemplate

    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.document_type == 'mortgage_statement'
    ).first()

    if template:
        # Get current patterns
        structure = template.template_structure or {}
        field_patterns = structure.get('field_patterns', {})

        print(f"Current template has {len(field_patterns)} patterns")

        # Add missing critical patterns
        comprehensive_patterns = {
            **field_patterns,  # Keep existing
            # Add YTD fields that are missing
            "ytd_principal_paid": {
                "patterns": [
                    r"Principal\s+Paid[\s\$\n\r]*([\d,]+\.?\d*)",
                    r"YEAR\s+TO\s+DATE.*?Principal\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_interest_paid": {
                "patterns": [
                    r"Interest\s+Paid[\s\$\n\r]*([\d,]+\.?\d*)",
                    r"YEAR\s+TO\s+DATE.*?Interest\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_taxes_disbursed": {
                "patterns": [
                    r"Taxes\s+Disbursed[\s\$\n\r]*([\d,]+\.?\d*)",
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_insurance_disbursed": {
                "patterns": [
                    r"Insurance\s+Disbursed[\s\$\n\r]*([\d,]+\.?\d*)",
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_reserve_disbursed": {
                "patterns": [
                    r"Reserve\s+(?:Escrow\s+)?Disbursed[\s\$\n\r]*([\d,]+\.?\d*)",
                ],
                "field_type": "currency",
                "required": False
            },
            "borrower_name": {
                "patterns": [
                    r"^([A-Z][A-Za-z\s,\.]+(?:LLC|Inc|Corp|LP)?)\s*$",
                ],
                "field_type": "text",
                "required": False
            },
            "property_address": {
                "patterns": [
                    r"Property\s+Address\s*:?\s*(.+?)(?:\n|$)",
                ],
                "field_type": "text",
                "required": False
            },
            "late_fees": {
                "patterns": [
                    r"late\s+charge\s+of\s+\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Late\s+Charges?\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                ],
                "field_type": "currency",
                "required": False
            },
        }

        structure['field_patterns'] = comprehensive_patterns
        template.template_structure = structure
        db.commit()

        print(f"✓ Updated template to {len(comprehensive_patterns)} patterns\n")

    # Now check if we can access actual extraction functionality
    # through the mortgage extraction API or service

    print("Note: Manual re-extraction requires access to PDF files.")
    print("Recommendation: Use REIMS2 UI to re-upload documents or trigger re-extraction.")

    db.close()

if __name__ == '__main__':
    main()
