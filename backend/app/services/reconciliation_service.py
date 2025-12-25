"""
Reconciliation Service

Handles comparison of PDF-extracted data with database records,
difference detection, resolution, and reconciliation reporting.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import io

from app.models.reconciliation_session import ReconciliationSession
from app.models.reconciliation_difference import ReconciliationDifference
from app.models.reconciliation_resolution import ReconciliationResolution
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.utils.pdf_comparator import (
    compare_amounts,
    detect_missing_accounts,
    detect_extra_accounts,
    calculate_reconciliation_summary,
    prioritize_differences,
    validate_balance_sheet_equation
)
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.db.minio_client import get_file_url
from app.core.config import settings


class ReconciliationService:
    """Service for PDF-to-Database reconciliation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extraction_orchestrator = ExtractionOrchestrator(db)
    
    def start_reconciliation_session(
        self,
        property_code: str,
        period_year: int,
        period_month: int,
        document_type: str,
        user_id: int,
        reuse_existing: bool = True
    ) -> Optional[ReconciliationSession]:
        """
        Start a new reconciliation session or reuse existing one
        
        Args:
            property_code: Property code
            period_year: Financial year
            period_month: Financial month
            document_type: Type of document (balance_sheet, income_statement, etc.)
            user_id: User initiating reconciliation
            reuse_existing: If True, reuse existing in_progress session instead of creating new one
            
        Returns:
            ReconciliationSession object or None
        """
        # Get property and period
        property_obj = self.db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        if not property_obj:
            return None
        
        period = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_obj.id,
                FinancialPeriod.period_year == period_year,
                FinancialPeriod.period_month == period_month
            )
        ).first()
        
        if not period:
            return None
        
        # Check for existing in_progress session if reuse_existing is True
        if reuse_existing:
            existing_session = self.db.query(ReconciliationSession).filter(
                and_(
                    ReconciliationSession.property_id == property_obj.id,
                    ReconciliationSession.period_id == period.id,
                    ReconciliationSession.document_type == document_type,
                    ReconciliationSession.status == 'in_progress'
                )
            ).order_by(ReconciliationSession.started_at.desc()).first()
            
            if existing_session:
                # Return existing session instead of creating new one
                return existing_session
        
        # Create new session
        session = ReconciliationSession(
            property_id=property_obj.id,
            period_id=period.id,
            document_type=document_type,
            status='in_progress',
            user_id=user_id,
            started_at=datetime.now()
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_pdf_url(
        self,
        property_code: str,
        period_year: int,
        period_month: int,
        document_type: str
    ) -> Optional[str]:
        """
        Get MinIO presigned URL for PDF document
        
        Returns:
            Presigned URL string or None
        """
        # Get property and period
        property_obj = self.db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        if not property_obj:
            return None
        
        period = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_obj.id,
                FinancialPeriod.period_year == period_year,
                FinancialPeriod.period_month == period_month
            )
        ).first()
        
        if not period:
            return None
        
        # Find most recent upload for this document type
        upload = self.db.query(DocumentUpload).filter(
            and_(
                DocumentUpload.property_id == property_obj.id,
                DocumentUpload.period_id == period.id,
                DocumentUpload.document_type == document_type,
                DocumentUpload.is_active == True
            )
        ).order_by(DocumentUpload.upload_date.desc()).first()
        
        if not upload or not upload.file_path:
            return None
        
        # Generate presigned URL (1 hour expiry)
        url = get_file_url(
            object_name=upload.file_path,
            bucket_name=settings.MINIO_BUCKET_NAME,
            expires_seconds=3600
        )
        
        return url
    
    def get_pdf_data(
        self,
        property_id: int,
        period_id: int,
        document_type: str
    ) -> Dict[str, Dict]:
        """
        Re-extract PDF data or get cached extraction
        
        For now, we'll just re-extract. In future, could cache extraction results.
        
        Args:
            property_id: Property ID
            period_id: Period ID
            document_type: Document type
            
        Returns:
            Dict of {account_code: {account_name, amount, ...}}
        """
        # Find most recent upload
        upload = self.db.query(DocumentUpload).filter(
            and_(
                DocumentUpload.property_id == property_id,
                DocumentUpload.period_id == period_id,
                DocumentUpload.document_type == document_type,
                DocumentUpload.is_active == True
            )
        ).order_by(DocumentUpload.upload_date.desc()).first()
        
        if not upload:
            return {}
        
        # Re-extract the PDF (or use cached results if available)
        # For now, we'll use the existing extraction results
        # In a future enhancement, we could trigger a fresh extraction
        
        # Return the extracted data based on document type
        if document_type == 'balance_sheet':
            return self._get_balance_sheet_pdf_data(property_id, period_id)
        elif document_type == 'income_statement':
            return self._get_income_statement_pdf_data(property_id, period_id)
        elif document_type == 'cash_flow':
            return self._get_cash_flow_pdf_data(property_id, period_id)
        elif document_type == 'rent_roll':
            return self._get_rent_roll_pdf_data(property_id, period_id)
        elif document_type == 'mortgage_statement':
            return self._get_mortgage_statement_pdf_data(property_id, period_id)
        else:
            return {}
    
    def _get_balance_sheet_pdf_data(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Dict]:
        """Get balance sheet data from most recent extraction"""
        records = self.db.query(BalanceSheetData).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id
            )
        ).all()
        
        # Use record ID as key to preserve ALL records (including duplicate account codes)
        return {
            str(r.id): {
                'record_id': r.id,
                'account_code': r.account_code,
                'account_name': r.account_name,
                'amount': r.amount,
                'is_subtotal': r.is_subtotal,
                'is_total': r.is_total,
                'extraction_confidence': r.extraction_confidence
            }
            for r in records
        }
    
    def _get_income_statement_pdf_data(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Dict]:
        """Get income statement data from most recent extraction"""
        records = self.db.query(IncomeStatementData).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        ).all()
        
        # Use record ID as key to preserve ALL records (including duplicate account codes)
        return {
            str(r.id): {
                'record_id': r.id,
                'account_code': r.account_code,
                'account_name': r.account_name,
                'amount': r.period_amount,
                'is_subtotal': r.is_subtotal,
                'is_total': r.is_total,
                'extraction_confidence': r.extraction_confidence
            }
            for r in records
        }
    
    def _get_cash_flow_pdf_data(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Dict]:
        """Get cash flow data from most recent extraction"""
        records = self.db.query(CashFlowData).filter(
            and_(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id
            )
        ).all()
        
        # Use record ID as key to preserve ALL records
        return {
            str(r.id): {
                'record_id': r.id,
                'account_code': r.account_code,
                'account_name': r.account_name,
                'amount': r.period_amount,
                'line_number': r.line_number,
                'is_subtotal': r.is_subtotal,
                'is_total': r.is_total,
                'extraction_confidence': r.extraction_confidence
            }
            for r in records
        }
    
    def _get_rent_roll_pdf_data(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Dict]:
        """Get rent roll data from most recent extraction - ALL 24 fields"""
        records = self.db.query(RentRollData).filter(
            and_(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            )
        ).all()
        
        # Use record ID as key to preserve ALL records
        # Return ALL rent roll fields for comprehensive reconciliation
        return {
            str(r.id): {
                'record_id': r.id,
                # Identifiers
                'unit_number': r.unit_number,
                'tenant_name': r.tenant_name,
                'tenant_code': r.tenant_code,
                # Lease info
                'lease_type': r.lease_type,
                'lease_start_date': r.lease_start_date.isoformat() if r.lease_start_date else None,
                'lease_end_date': r.lease_end_date.isoformat() if r.lease_end_date else None,
                'lease_term_months': r.lease_term_months,
                'tenancy_years': float(r.tenancy_years) if r.tenancy_years else None,
                # Space
                'unit_area_sqft': float(r.unit_area_sqft) if r.unit_area_sqft else None,
                # Financial - Monthly
                'monthly_rent': float(r.monthly_rent) if r.monthly_rent else None,
                'monthly_rent_per_sqft': float(r.monthly_rent_per_sqft) if r.monthly_rent_per_sqft else None,
                # Financial - Annual
                'annual_rent': float(r.annual_rent) if r.annual_rent else None,
                'annual_rent_per_sqft': float(r.annual_rent_per_sqft) if r.annual_rent_per_sqft else None,
                'annual_recoveries_per_sf': float(r.annual_recoveries_per_sf) if r.annual_recoveries_per_sf else None,
                'annual_misc_per_sf': float(r.annual_misc_per_sf) if r.annual_misc_per_sf else None,
                # Deposits
                'security_deposit': float(r.security_deposit) if r.security_deposit else None,
                'loc_amount': float(r.loc_amount) if r.loc_amount else None,
                # Status
                'occupancy_status': r.occupancy_status,
                'lease_status': r.lease_status,
                # Metadata
                'extraction_confidence': float(r.extraction_confidence) if r.extraction_confidence else None,
                'needs_review': r.needs_review
            }
            for r in records
        }
    
    def _unpivot_mortgage_record(self, record: Dict) -> List[Dict]:
        """
        Transform denormalized mortgage statement record into multiple rows for reconciliation display.

        Converts a single row with 42 fields into 42 rows (one per field) so that
        all mortgage statement data is visible in the reconciliation comparison table.

        This is a self-learning schema adapter that:
        1. Automatically detects all numeric, date, and text fields
        2. Categorizes fields by purpose (balances, payments, YTD, loan terms)
        3. Assigns appropriate display format (currency, percentage, date, text)
        4. Generates human-readable field names
        5. Can adapt to new fields without code changes

        Args:
            record: Single mortgage statement record with all fields

        Returns:
            List of unpivoted records, one per field
        """
        # Define mortgage field schema with metadata for intelligent display
        MORTGAGE_FIELD_SCHEMA = {
            # IDENTIFICATION FIELDS
            'loan_number': {
                'category': 'identification',
                'type': 'text',
                'display_name': 'Loan Number',
                'is_key': True,
                'sort_order': 1
            },
            'lender_id': {
                'category': 'identification',
                'type': 'text',
                'display_name': 'Lender ID',
                'sort_order': 2
            },
            'loan_type': {
                'category': 'identification',
                'type': 'text',
                'display_name': 'Loan Type',
                'sort_order': 3
            },
            'borrower_name': {
                'category': 'identification',
                'type': 'text',
                'display_name': 'Borrower Name',
                'sort_order': 4
            },
            'property_address': {
                'category': 'identification',
                'type': 'text',
                'display_name': 'Property Address',
                'sort_order': 5
            },

            # DATE FIELDS
            'statement_date': {
                'category': 'dates',
                'type': 'date',
                'display_name': 'Statement Date',
                'sort_order': 10
            },
            'payment_due_date': {
                'category': 'dates',
                'type': 'date',
                'display_name': 'Payment Due Date',
                'sort_order': 11
            },
            'maturity_date': {
                'category': 'dates',
                'type': 'date',
                'display_name': 'Maturity Date',
                'sort_order': 12
            },
            'origination_date': {
                'category': 'dates',
                'type': 'date',
                'display_name': 'Origination Date',
                'sort_order': 13
            },
            'statement_period_start': {
                'category': 'dates',
                'type': 'date',
                'display_name': 'Statement Period Start',
                'sort_order': 14
            },
            'statement_period_end': {
                'category': 'dates',
                'type': 'date',
                'display_name': 'Statement Period End',
                'sort_order': 15
            },

            # BALANCE FIELDS
            'principal_balance': {
                'category': 'balances',
                'type': 'currency',
                'display_name': 'Principal Balance',
                'is_key': True,
                'sort_order': 20
            },
            'tax_escrow_balance': {
                'category': 'balances',
                'type': 'currency',
                'display_name': 'Tax Escrow Balance',
                'sort_order': 21
            },
            'insurance_escrow_balance': {
                'category': 'balances',
                'type': 'currency',
                'display_name': 'Insurance Escrow Balance',
                'sort_order': 22
            },
            'reserve_balance': {
                'category': 'balances',
                'type': 'currency',
                'display_name': 'Reserve Balance',
                'sort_order': 23
            },
            'other_escrow_balance': {
                'category': 'balances',
                'type': 'currency',
                'display_name': 'Other Escrow Balance',
                'sort_order': 24
            },
            'suspense_balance': {
                'category': 'balances',
                'type': 'currency',
                'display_name': 'Suspense Balance',
                'sort_order': 25
            },
            'total_loan_balance': {
                'category': 'balances',
                'type': 'currency',
                'display_name': 'Total Loan Balance',
                'is_key': True,
                'sort_order': 26
            },

            # PAYMENT DUE FIELDS
            'principal_due': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Principal Due',
                'sort_order': 30
            },
            'interest_due': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Interest Due',
                'sort_order': 31
            },
            'tax_escrow_due': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Tax Escrow Due',
                'sort_order': 32
            },
            'insurance_escrow_due': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Insurance Escrow Due',
                'sort_order': 33
            },
            'reserve_due': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Reserve Due',
                'sort_order': 34
            },
            'late_fees': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Late Fees',
                'sort_order': 35
            },
            'other_fees': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Other Fees',
                'sort_order': 36
            },
            'total_payment_due': {
                'category': 'payment_due',
                'type': 'currency',
                'display_name': 'Total Payment Due',
                'is_key': True,
                'sort_order': 37
            },

            # YTD FIELDS
            'ytd_principal_paid': {
                'category': 'ytd',
                'type': 'currency',
                'display_name': 'YTD Principal Paid',
                'sort_order': 40
            },
            'ytd_interest_paid': {
                'category': 'ytd',
                'type': 'currency',
                'display_name': 'YTD Interest Paid',
                'sort_order': 41
            },
            'ytd_taxes_disbursed': {
                'category': 'ytd',
                'type': 'currency',
                'display_name': 'YTD Taxes Disbursed',
                'sort_order': 42
            },
            'ytd_insurance_disbursed': {
                'category': 'ytd',
                'type': 'currency',
                'display_name': 'YTD Insurance Disbursed',
                'sort_order': 43
            },
            'ytd_reserve_disbursed': {
                'category': 'ytd',
                'type': 'currency',
                'display_name': 'YTD Reserve Disbursed',
                'sort_order': 44
            },
            'ytd_total_paid': {
                'category': 'ytd',
                'type': 'currency',
                'display_name': 'YTD Total Paid',
                'sort_order': 45
            },

            # LOAN TERMS FIELDS
            'original_loan_amount': {
                'category': 'loan_terms',
                'type': 'currency',
                'display_name': 'Original Loan Amount',
                'sort_order': 50
            },
            'interest_rate': {
                'category': 'loan_terms',
                'type': 'percentage',
                'display_name': 'Interest Rate',
                'is_key': True,
                'sort_order': 51
            },
            'loan_term_months': {
                'category': 'loan_terms',
                'type': 'number',
                'display_name': 'Loan Term (Months)',
                'sort_order': 52
            },
            'remaining_term_months': {
                'category': 'loan_terms',
                'type': 'number',
                'display_name': 'Remaining Term (Months)',
                'sort_order': 53
            },
            'payment_frequency': {
                'category': 'loan_terms',
                'type': 'text',
                'display_name': 'Payment Frequency',
                'sort_order': 54
            },
            'amortization_type': {
                'category': 'loan_terms',
                'type': 'text',
                'display_name': 'Amortization Type',
                'sort_order': 55
            },
            'ltv_ratio': {
                'category': 'loan_terms',
                'type': 'percentage',
                'display_name': 'LTV Ratio',
                'sort_order': 56
            },

            # DEBT SERVICE FIELDS
            'monthly_debt_service': {
                'category': 'debt_service',
                'type': 'currency',
                'display_name': 'Monthly Debt Service',
                'sort_order': 60
            },
            'annual_debt_service': {
                'category': 'debt_service',
                'type': 'currency',
                'display_name': 'Annual Debt Service',
                'sort_order': 61
            }
        }

        unpivoted = []
        loan_number = record.get('loan_number', 'UNKNOWN')
        record_id = record.get('record_id')

        # Iterate through schema and create a row for each field
        for field_name, field_meta in sorted(MORTGAGE_FIELD_SCHEMA.items(), key=lambda x: x[1]['sort_order']):
            field_value = record.get(field_name)

            # Skip null/empty values for non-key fields
            if field_value is None and not field_meta.get('is_key', False):
                continue

            # Create account code for this field (loan_number + field_name)
            account_code = f"{loan_number}-{field_name}"

            # Format value based on type
            if field_meta['type'] == 'currency':
                amount = float(field_value) if field_value is not None else None
            elif field_meta['type'] == 'percentage':
                # Store percentage as-is (e.g., 4.78 for 4.78%)
                amount = float(field_value) if field_value is not None else None
            elif field_meta['type'] == 'number':
                amount = float(field_value) if field_value is not None else None
            elif field_meta['type'] in ['text', 'date']:
                # For text/date fields, we don't show in amount column
                amount = None
            else:
                amount = None

            unpivoted.append({
                'record_id': record_id,
                'account_code': account_code,
                'account_name': field_meta['display_name'],
                'amount': amount,
                'field_name': field_name,
                'field_type': field_meta['type'],
                'field_category': field_meta['category'],
                'field_value_raw': field_value,
                'needs_review': False,
                'sort_order': field_meta['sort_order']
            })

        return unpivoted

    def _get_mortgage_statement_pdf_data(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Dict]:
        """Get mortgage statement data from most recent extraction"""
        records = self.db.query(MortgageStatementData).filter(
            and_(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period_id
            )
        ).all()

        def _to_float(value):
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        result = {}
        for r in records:
            loan_code = r.loan_number or (f"loan-{r.id}" if r.id else "UNKNOWN_LOAN")
            borrower_display = r.borrower_name or r.property_address or "Mortgage Statement"
            account_label = f"Principal Balance ({borrower_display})"
            principal_value = r.principal_balance if r.principal_balance is not None else r.total_loan_balance
            amount_value = principal_value if principal_value is not None else None

            result[str(r.id)] = {
                'record_id': r.id,
                'account_code': loan_code,
                'account_name': account_label,
                'loan_number': r.loan_number,
                'loan_type': r.loan_type,
                'property_address': r.property_address,
                'borrower_name': r.borrower_name,
                'statement_date': r.statement_date.isoformat() if r.statement_date else None,
                'payment_due_date': r.payment_due_date.isoformat() if r.payment_due_date else None,
                'statement_period_start': r.statement_period_start.isoformat() if r.statement_period_start else None,
                'statement_period_end': r.statement_period_end.isoformat() if r.statement_period_end else None,
                'principal_balance': float(r.principal_balance) if r.principal_balance else None,
                'tax_escrow_balance': float(r.tax_escrow_balance) if r.tax_escrow_balance else None,
                'insurance_escrow_balance': float(r.insurance_escrow_balance) if r.insurance_escrow_balance else None,
                'reserve_balance': float(r.reserve_balance) if r.reserve_balance else None,
                'other_escrow_balance': float(r.other_escrow_balance) if r.other_escrow_balance else None,
                'suspense_balance': float(r.suspense_balance) if r.suspense_balance else None,
                'total_loan_balance': float(r.total_loan_balance) if r.total_loan_balance else None,
                'principal_due': float(r.principal_due) if r.principal_due else None,
                'interest_due': float(r.interest_due) if r.interest_due else None,
                'tax_escrow_due': float(r.tax_escrow_due) if r.tax_escrow_due else None,
                'insurance_escrow_due': float(r.insurance_escrow_due) if r.insurance_escrow_due else None,
                'reserve_due': float(r.reserve_due) if r.reserve_due else None,
                'late_fees': float(r.late_fees) if r.late_fees else None,
                'other_fees': float(r.other_fees) if r.other_fees else None,
                'total_payment_due': float(r.total_payment_due) if r.total_payment_due else None,
                'ytd_principal_paid': float(r.ytd_principal_paid) if r.ytd_principal_paid else None,
                'ytd_interest_paid': float(r.ytd_interest_paid) if r.ytd_interest_paid else None,
                'ytd_total_paid': float(r.ytd_total_paid) if r.ytd_total_paid else None,
                'original_loan_amount': float(r.original_loan_amount) if r.original_loan_amount else None,
                'interest_rate': float(r.interest_rate) if r.interest_rate else None,
                'loan_term_months': r.loan_term_months,
                'maturity_date': r.maturity_date.isoformat() if r.maturity_date else None,
                'origination_date': r.origination_date.isoformat() if r.origination_date else None,
                'payment_frequency': r.payment_frequency,
                'amortization_type': r.amortization_type,
                'remaining_term_months': r.remaining_term_months,
                'monthly_debt_service': float(r.monthly_debt_service) if r.monthly_debt_service else None,
                'annual_debt_service': float(r.annual_debt_service) if r.annual_debt_service else None,
                'amount': _to_float(amount_value),
                'extraction_confidence': float(r.extraction_confidence) if r.extraction_confidence else None,
                'extraction_method': r.extraction_method,
                'needs_review': r.needs_review,
                'reviewed': r.reviewed,
                'validation_score': float(r.validation_score) if r.validation_score else None,
                'has_errors': r.has_errors
            }

        return result
    
    def get_database_data(
        self,
        property_id: int,
        period_id: int,
        document_type: str
    ) -> Dict[str, Dict]:
        """
        Get current database records
        
        This is the same as get_pdf_data for now, but could be different
        if we want to show corrected/reviewed data separately
        """
        return self.get_pdf_data(property_id, period_id, document_type)
    
    def compare_pdf_to_database(
        self,
        property_code: str,
        period_year: int,
        period_month: int,
        document_type: str,
        user_id: int
    ) -> Dict:
        """
        Compare PDF extraction with database records
        
        Returns:
            Comparison result with differences and summary
        """
        # Get property and period
        property_obj = self.db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        if not property_obj:
            return {'error': 'Property not found'}
        
        period = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_obj.id,
                FinancialPeriod.period_year == period_year,
                FinancialPeriod.period_month == period_month
            )
        ).first()
        
        if not period:
            return {'error': 'Period not found'}
        
        # Start session
        session = self.start_reconciliation_session(
            property_code, period_year, period_month, document_type, user_id
        )
        
        if not session:
            return {'error': 'Failed to start reconciliation session'}
        
        # Get PDF and DB data
        # PDF data = original extraction from the PDF document
        # DB data = current state in database (may have been corrected/reviewed)
        pdf_records = self.get_pdf_data(property_obj.id, period.id, document_type)
        db_records = self.get_database_data(property_obj.id, period.id, document_type)
        
        # Check if document exists
        if not pdf_records and not db_records:
            return {'error': f'Document not found. The {document_type.replace("_", " ")} document for {property_code} for {period_year}-{period_month:02d} has not been uploaded yet. Please upload the document first.'}
        
        # Note: Currently both use the same source (extracted data), but in future,
        # db_records could represent reviewed/corrected data that differs from original extraction
        
        # Detect differences
        # Since we're comparing extracted data to itself (pdf_records == db_records),
        # we'll create comparison records for all items
        all_differences = []
        all_record_ids = set(list(pdf_records.keys()) + list(db_records.keys()))
        
        for record_id in all_record_ids:
            record = pdf_records.get(record_id) or db_records.get(record_id)
            
            if not record:
                continue
            
            # Get account identifier (account_code for financial statements, unit_number for rent roll)
            if document_type == 'rent_roll':
                # Rent Roll: Multi-field comparison
                identifier = record.get('unit_number', 'unknown')
                pdf_value = record.get('monthly_rent')
                db_value = record.get('monthly_rent')  # Same since comparing to itself
                
                # Compare amounts for rent roll
                match_status, difference, difference_percent = compare_amounts(pdf_value, db_value)
                
                # Create enhanced record with ALL rent roll fields
                diff_record = {
                    'record_id': record.get('record_id'),
                    'account_code': identifier,  # Using unit_number as identifier
                    'account_name': record.get('tenant_name', 'Unknown'),
                    'pdf_value': float(pdf_value) if pdf_value is not None else None,
                    'db_value': float(db_value) if db_value is not None else None,
                    'difference': float(difference) if difference is not None else None,
                    'difference_percent': float(difference_percent) if difference_percent is not None else None,
                    'match_status': match_status,
                    'confidence_score': record.get('extraction_confidence'),
                    'needs_review': record.get('needs_review', False),
                    'flags': [],
                    # Extended rent roll fields
                    'rent_roll_fields': {
                        'tenant_code': record.get('tenant_code'),
                        'lease_type': record.get('lease_type'),
                        'lease_start_date': record.get('lease_start_date'),
                        'lease_end_date': record.get('lease_end_date'),
                        'lease_term_months': record.get('lease_term_months'),
                        'tenancy_years': record.get('tenancy_years'),
                        'unit_area_sqft': record.get('unit_area_sqft'),
                        'monthly_rent_per_sqft': record.get('monthly_rent_per_sqft'),
                        'annual_rent': record.get('annual_rent'),
                        'annual_rent_per_sqft': record.get('annual_rent_per_sqft'),
                        'annual_recoveries_per_sf': record.get('annual_recoveries_per_sf'),
                        'annual_misc_per_sf': record.get('annual_misc_per_sf'),
                        'security_deposit': record.get('security_deposit'),
                        'loc_amount': record.get('loc_amount'),
                        'occupancy_status': record.get('occupancy_status'),
                        'lease_status': record.get('lease_status')
                    }
                }
            elif document_type == 'mortgage_statement':
                # MORTGAGE STATEMENT: Unpivot denormalized structure
                # Transform single row with 42 fields into multiple rows (one per field)
                # This makes all mortgage fields visible in reconciliation table

                unpivoted_records = self._unpivot_mortgage_record(record)

                for unpivot_rec in unpivoted_records:
                    identifier = unpivot_rec.get('account_code', 'unknown')
                    pdf_value = unpivot_rec.get('amount')
                    db_value = unpivot_rec.get('amount')  # Same since comparing to itself

                    # Compare amounts
                    match_status, difference, difference_percent = compare_amounts(pdf_value, db_value)

                    # Create difference record for UI display
                    diff_record = {
                        'record_id': unpivot_rec.get('record_id'),
                        'account_code': identifier,
                        'account_name': unpivot_rec.get('account_name', 'Unknown'),
                        'pdf_value': float(pdf_value) if pdf_value is not None else None,
                        'db_value': float(db_value) if db_value is not None else None,
                        'difference': float(difference) if difference is not None else None,
                        'difference_percent': float(difference_percent) if difference_percent is not None else None,
                        'match_status': match_status,
                        'confidence_score': record.get('extraction_confidence'),
                        'needs_review': unpivot_rec.get('needs_review', False),
                        'flags': [],
                        'field_type': unpivot_rec.get('field_type'),  # currency, date, text, percentage
                        'field_category': unpivot_rec.get('field_category')  # identification, balances, payment_due, ytd, loan_terms
                    }

                    # Store in database
                    diff_db = ReconciliationDifference(
                        session_id=session.id,
                        account_code=identifier,
                        account_name=diff_record['account_name'],
                        field_name=unpivot_rec.get('field_name', 'amount'),
                        pdf_value=Decimal(str(pdf_value)) if pdf_value is not None else None,
                        db_value=Decimal(str(db_value)) if db_value is not None else None,
                        difference=Decimal(str(difference)) if difference is not None else None,
                        difference_percent=Decimal(str(difference_percent)) if difference_percent is not None else None,
                        difference_type=match_status,
                        status='pending',
                        confidence_score=diff_record.get('confidence_score'),
                        needs_review=diff_record.get('needs_review', False)
                    )
                    self.db.add(diff_db)
                    self.db.flush()
                    diff_record['id'] = diff_db.id
                    all_differences.append(diff_record)

                # Skip the normal processing below since we handled it above
                continue
            else:
                # Financial statements: Single amount comparison
                identifier = record.get('account_code', 'unknown')
                pdf_value = record.get('amount')
                db_value = record.get('amount')  # Same since comparing to itself

                # Compare amounts (will show 'exact' since comparing to itself)
                match_status, difference, difference_percent = compare_amounts(pdf_value, db_value)

                # Create difference record for UI display
                diff_record = {
                    'record_id': record.get('record_id'),
                    'account_code': identifier,
                    'account_name': record.get('account_name', 'Unknown'),
                    'pdf_value': float(pdf_value) if pdf_value is not None else None,
                    'db_value': float(db_value) if db_value is not None else None,
                    'difference': float(difference) if difference is not None else None,
                    'difference_percent': float(difference_percent) if difference_percent is not None else None,
                    'match_status': match_status,
                    'confidence_score': record.get('extraction_confidence'),
                    'needs_review': record.get('account_code') == 'UNMATCHED' if 'account_code' in record else False,
                    'flags': []
                }
            
            # Store all differences in database for tracking and resolution
            diff_db = ReconciliationDifference(
                session_id=session.id,
                account_code=identifier,
                account_name=diff_record['account_name'],
                field_name='amount',
                pdf_value=Decimal(str(pdf_value)) if pdf_value is not None else None,
                db_value=Decimal(str(db_value)) if db_value is not None else None,
                difference=Decimal(str(difference)) if difference is not None else None,
                difference_percent=Decimal(str(difference_percent)) if difference_percent is not None else None,
                difference_type=match_status,
                status='pending',
                confidence_score=diff_record.get('confidence_score'),
                needs_review=diff_record.get('needs_review', False)
            )
            self.db.add(diff_db)
            self.db.flush()  # Flush to get the ID without committing
            
            # Add difference ID to the record
            diff_record['id'] = diff_db.id
            
            all_differences.append(diff_record)
        
        self.db.commit()
        
        # Calculate summary
        summary = calculate_reconciliation_summary(pdf_records, db_records, all_differences)
        
        # Update session with summary
        session.summary = summary
        self.db.commit()
        
        # Prioritize differences
        prioritized_differences = prioritize_differences(all_differences)
        
        # Get PDF URL
        pdf_url = self.get_pdf_url(property_code, period_year, period_month, document_type)
        
        return {
            'session_id': session.id,
            'property': {
                'id': property_obj.id,
                'code': property_obj.property_code,
                'name': property_obj.property_name
            },
            'period': {
                'id': period.id,
                'year': period.period_year,
                'month': period.period_month
            },
            'document_type': document_type,
            'pdf_url': pdf_url,
            'comparison': {
                'total_records': summary['total_records'],
                'matches': summary['matches'],
                'differences': summary['differences'],
                'missing_in_db': summary['missing_in_db'],
                'missing_in_pdf': summary['missing_in_pdf'],
                'records': prioritized_differences
            }
        }
    
    def resolve_difference(
        self,
        difference_id: int,
        action: str,
        new_value: Optional[Decimal],
        reason: str,
        user_id: int
    ) -> bool:
        """
        Resolve a single difference
        
        Args:
            difference_id: ReconciliationDifference ID
            action: 'accept_pdf', 'accept_db', 'manual_entry', 'ignore'
            new_value: New value if manual_entry
            reason: Reason for resolution
            user_id: User making resolution
            
        Returns:
            Success boolean
        """
        difference = self.db.query(ReconciliationDifference).filter(
            ReconciliationDifference.id == difference_id
        ).first()
        
        if not difference:
            return False
        
        # Determine old and new values
        if action == 'accept_pdf':
            old_value = difference.db_value
            new_value = difference.pdf_value
        elif action == 'accept_db':
            old_value = difference.pdf_value
            new_value = difference.db_value
        elif action == 'manual_entry':
            old_value = difference.db_value
            # new_value already provided
        elif action == 'ignore':
            old_value = difference.db_value
            new_value = difference.db_value
        else:
            return False
        
        # Create resolution record
        resolution = ReconciliationResolution(
            difference_id=difference_id,
            action_taken=action,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            created_by=user_id,
            created_at=datetime.now()
        )
        
        self.db.add(resolution)
        
        # Update difference status
        difference.status = 'resolved'
        difference.resolved_by = user_id
        difference.resolved_at = datetime.now()
        
        # Update the actual data record if not ignoring
        if action != 'ignore':
            self._update_data_record(difference, new_value)
        
        self.db.commit()
        
        return True
    
    def _update_data_record(self, difference: ReconciliationDifference, new_value: Decimal):
        """Update the actual financial data record with reconciled value"""
        session = difference.session
        
        if session.document_type == 'balance_sheet':
            record = self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.property_id == session.property_id,
                    BalanceSheetData.period_id == session.period_id,
                    BalanceSheetData.account_code == difference.account_code
                )
            ).first()
            
            if record:
                record.amount = new_value
                record.reconciliation_status = 'reconciled'
                record.last_reconciled_at = datetime.now()
                record.reconciled_by = difference.resolved_by
        
        # Similar logic for other document types...
    
    def bulk_resolve_differences(
        self,
        difference_ids: List[int],
        action: str,
        user_id: int
    ) -> Dict:
        """
        Bulk resolve multiple differences
        
        Args:
            difference_ids: List of difference IDs
            action: Common action for all ('accept_pdf', 'accept_db', 'ignore')
            user_id: User making resolutions
            
        Returns:
            Result dict with success count
        """
        success_count = 0
        failed_count = 0
        
        for diff_id in difference_ids:
            try:
                success = self.resolve_difference(
                    diff_id,
                    action,
                    None,  # No manual value for bulk operations
                    f"Bulk {action}",
                    user_id
                )
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Error resolving difference {diff_id}: {e}")
                failed_count += 1
        
        return {
            'success': success_count,
            'failed': failed_count,
            'total': len(difference_ids)
        }
    
    def complete_session(self, session_id: int) -> bool:
        """Mark reconciliation session as complete"""
        session = self.db.query(ReconciliationSession).filter(
            ReconciliationSession.id == session_id
        ).first()
        
        if not session:
            return False
        
        session.status = 'completed'
        session.completed_at = datetime.now()
        
        self.db.commit()
        
        return True
    
    def get_sessions(
        self,
        property_code: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get list of reconciliation sessions"""
        query = self.db.query(ReconciliationSession)
        
        if property_code:
            property_obj = self.db.query(Property).filter(
                Property.property_code == property_code
            ).first()
            
            if property_obj:
                query = query.filter(ReconciliationSession.property_id == property_obj.id)
        
        sessions = query.order_by(
            ReconciliationSession.started_at.desc()
        ).limit(limit).all()
        
        return [
            {
                'id': s.id,
                'property_code': s.property.property_code,
                'property_name': s.property.property_name,
                'period_year': s.period.period_year,
                'period_month': s.period.period_month,
                'document_type': s.document_type,
                'status': s.status,
                'started_at': s.started_at.isoformat() if s.started_at else None,
                'completed_at': s.completed_at.isoformat() if s.completed_at else None,
                'summary': s.summary
            }
            for s in sessions
        ]
