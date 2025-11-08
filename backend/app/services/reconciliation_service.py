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
        user_id: int
    ) -> Optional[ReconciliationSession]:
        """
        Start a new reconciliation session
        
        Args:
            property_code: Property code
            period_year: Financial year
            period_month: Financial month
            document_type: Type of document (balance_sheet, income_statement, etc.)
            user_id: User initiating reconciliation
            
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
        
        # Create session
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
        
        return {
            r.account_code: {
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
        
        return {
            r.account_code: {
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
        
        return {
            f"{r.account_code}_{r.line_number}": {
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
        """Get rent roll data from most recent extraction"""
        records = self.db.query(RentRollData).filter(
            and_(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            )
        ).all()
        
        return {
            r.unit_number: {
                'unit_number': r.unit_number,
                'tenant_name': r.tenant_name,
                'monthly_rent': r.monthly_rent,
                'annual_rent': r.annual_rent,
                'extraction_confidence': r.extraction_confidence
            }
            for r in records
        }
    
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
        pdf_records = self.get_pdf_data(property_obj.id, period.id, document_type)
        db_records = self.get_database_data(property_obj.id, period.id, document_type)
        
        # For simplicity, treat them as the same for now (since we're comparing extraction to itself)
        # In a real scenario, you might re-extract the PDF fresh or compare to reviewed data
        
        # Detect differences
        all_differences = []
        all_account_codes = set(list(pdf_records.keys()) + list(db_records.keys()))
        
        for account_code in all_account_codes:
            pdf_record = pdf_records.get(account_code)
            db_record = db_records.get(account_code)
            
            if document_type == 'rent_roll':
                # Special handling for rent roll
                pdf_value = pdf_record.get('monthly_rent') if pdf_record else None
                db_value = db_record.get('monthly_rent') if db_record else None
            else:
                pdf_value = pdf_record.get('amount') if pdf_record else None
                db_value = db_record.get('amount') if db_record else None
            
            # Compare amounts
            match_status, difference, difference_percent = compare_amounts(pdf_value, db_value)
            
            # Create difference record
            diff_record = {
                'account_code': account_code,
                'account_name': pdf_record.get('account_name') if pdf_record else db_record.get('account_name'),
                'pdf_value': float(pdf_value) if pdf_value is not None else None,
                'db_value': float(db_value) if db_value is not None else None,
                'difference': float(difference) if difference is not None else None,
                'difference_percent': float(difference_percent) if difference_percent is not None else None,
                'match_status': match_status,
                'confidence_score': pdf_record.get('extraction_confidence') if pdf_record else None,
                'needs_review': match_status in ['mismatch', 'missing_pdf', 'missing_db'],
                'flags': []
            }
            
            all_differences.append(diff_record)
            
            # Store in database if not exact match
            if match_status != 'exact':
                diff_db = ReconciliationDifference(
                    session_id=session.id,
                    account_code=account_code,
                    account_name=diff_record['account_name'],
                    field_name='amount',
                    pdf_value=Decimal(str(pdf_value)) if pdf_value is not None else None,
                    db_value=Decimal(str(db_value)) if db_value is not None else None,
                    difference=Decimal(str(difference)) if difference is not None else None,
                    difference_percent=Decimal(str(difference_percent)) if difference_percent is not None else None,
                    difference_type=match_status,
                    status='pending',
                    confidence_score=diff_record['confidence_score'],
                    needs_review=diff_record['needs_review']
                )
                self.db.add(diff_db)
        
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

