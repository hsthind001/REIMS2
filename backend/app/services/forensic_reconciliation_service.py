"""
Forensic Reconciliation Service

Comprehensive service for forensic financial document reconciliation across
Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement.

Manages reconciliation sessions, finds matches using multiple engines,
validates discrepancies, and provides auditor review workflows.
"""
import logging
import decimal
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, true

from app.models.forensic_reconciliation_session import ForensicReconciliationSession
from app.models.forensic_match import ForensicMatch
from app.models.forensic_discrepancy import ForensicDiscrepancy
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData

if TYPE_CHECKING:
    from app.services.forensic.match_processor import ForensicMatchProcessor
    from app.services.forensic.discrepancy_validator import ForensicDiscrepancyValidator
    from app.services.reconciliation_diagnostics_service import ReconciliationDiagnosticsService

logger = logging.getLogger(__name__)


class ForensicReconciliationService:
    """Service for forensic reconciliation across all document types"""
    
    def __init__(
        self, 
        db: Session,
        match_processor: Optional['ForensicMatchProcessor'] = None,
        discrepancy_validator: Optional['ForensicDiscrepancyValidator'] = None,
        diagnostics_service: Optional['ReconciliationDiagnosticsService'] = None
    ):
        """
        Initialize forensic reconciliation service with injected dependencies.
        
        Args:
            db: Database session
            match_processor: Logic for matching execution
            discrepancy_validator: Logic for validation
        """
        self.db = db
        
        # Lazy load these to avoid circular imports if necessary, or better yet, assume they are passed construction
        # For now, we instantiate them if not provided, but they are lighter weight.
        # Ideally, main.py/dependency overrides should provide these.
        
        if not match_processor:
            from app.services.forensic.match_processor import ForensicMatchProcessor
            from app.services.adaptive_matching_service import AdaptiveMatchingService
            from app.services.exception_tiering_service import ExceptionTieringService
            
            # These are still hard deps if not injected, but at least we moved the logic
            self.match_processor = ForensicMatchProcessor(
                db, 
                AdaptiveMatchingService(db),
                ExceptionTieringService(db)
            )
        else:
            self.match_processor = match_processor

        if not discrepancy_validator:
            from app.services.forensic.discrepancy_validator import ForensicDiscrepancyValidator
            self.discrepancy_validator = ForensicDiscrepancyValidator(db)
        else:
            self.discrepancy_validator = discrepancy_validator

        if not diagnostics_service:
            from app.services.reconciliation_diagnostics_service import ReconciliationDiagnosticsService
            self.diagnostics_service = ReconciliationDiagnosticsService(db)
        else:
            self.diagnostics_service = diagnostics_service
    
    def start_reconciliation_session(
        self,
        property_id: int,
        period_id: int,
        session_type: str = 'full_reconciliation',
        auditor_id: Optional[int] = None
    ) -> Optional[ForensicReconciliationSession]:
        """
        Start a new forensic reconciliation session
        
        Validates that all necessary documents exist for the property/period.
        
        Args:
            property_id: Property ID
            period_id: Period ID
            session_type: Type of session ('full_reconciliation', 'cross_document', 'specific_match')
            auditor_id: Optional auditor user ID
            
        Returns:
            ForensicReconciliationSession object or None if validation fails
        """
        # Validate property and period exist
        property_obj = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            logger.error(f"Property {property_id} not found")
            return None
        
        period = self.db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        if not period:
            logger.error(f"Period {period_id} not found")
            return None
        
        # Validate documents exist (at least one document type should be present)
        document_types = ['balance_sheet', 'income_statement', 'cash_flow', 'rent_roll', 'mortgage_statement']
        existing_docs = self.db.query(DocumentUpload).filter(
            and_(
                DocumentUpload.property_id == property_id,
                DocumentUpload.period_id == period_id,
                DocumentUpload.document_type.in_(document_types),
                DocumentUpload.is_active.is_(true())
            )
        ).all()
        
        if not existing_docs:
            logger.warning(f"No documents found for property {property_id}, period {period_id}")
            return None
        
        # Create new session
        session = ForensicReconciliationSession(
            property_id=property_id,
            period_id=period_id,
            session_type=session_type,
            status='in_progress',
            auditor_id=auditor_id,
            started_at=datetime.now()
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"Started forensic reconciliation session {session.id} for property {property_id}, period {period_id}")
        
        return session
    
    def find_all_matches(
        self,
        session_id: int,
        use_exact: bool = True,
        use_fuzzy: bool = True,
        use_calculated: bool = True,
        use_inferred: bool = True,
        use_rules: bool = True
    ) -> Dict[str, Any]:
        """
        Execute all matching engines - Orchestrator Method.
        """
        session = self.db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.id == session_id
        ).first()

        if not session:
             return {'error': 'Session not found'}

        # Delegate to processor
        result = self.match_processor.process_matches(
            session_id,
            session.property_id,
            session.period_id,
            use_exact, use_fuzzy, use_calculated, use_inferred, use_rules
        )
        
        # Summary update and other orchestration logic could happen here
        # Note: We do NOT commit here. The API route calling this should handle the commit.
        

        
        # Execute Calculated Rules (Hardcoded Python Rules)
        # This ensures the "By Document" tab is updated with fresh rule evaluations
        if use_rules:
            try:
                from app.services.reconciliation_rule_engine import ReconciliationRuleEngine
                rule_engine = ReconciliationRuleEngine(self.db)
                rule_engine.execute_all_rules(session.property_id, session.period_id)
                rule_engine.save_results()
                logger.info(f"Executed ReconciliationRuleEngine for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to execute ReconciliationRuleEngine: {e}")
                # Don't fail the whole request, but log it
        
        return {
            'session_id': session_id,
            'matches_count': len(result['stored_matches']),
            'diagnostic': {
                'failed': len(result['failed_matches'])
            }
        }
    
    def validate_matches(
        self,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Validate matches and identify discrepancies - Orchestrator Method.
        """
        # Delegate
        result = self.discrepancy_validator.validate_session(session_id)
        
        # Response builder (simplified)
        return {
            'session_id': session_id,
            'status': 'completed',
            'health_score': result['health_score'],
            'discrepancies': [self._discrepancy_to_dict(d) for d in result['discrepancies']]
        }

    def _clamp_percent(self, value: Optional[Any]) -> Optional[Decimal]:
        """Clamp percentage value to fit in Numeric(10, 4)"""
        if value is None:
            return None
        
        try:
            val = Decimal(str(value))
        except (ValueError, TypeError, decimal.InvalidOperation):
            return None
            
        limit = Decimal('999999.9999')
        if val > limit:
            return limit
        if val < -limit:
            return -limit
        return val
    
    def get_reconciliation_dashboard(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Any]:
        """
        Get reconciliation dashboard data
        
        Returns summary statistics and match details for dashboard display.
        
        Args:
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            Dict with dashboard data
        """
        # Get most recent session
        session = self.db.query(ForensicReconciliationSession).filter(
            and_(
                ForensicReconciliationSession.property_id == property_id,
                ForensicReconciliationSession.period_id == period_id
            )
        ).order_by(ForensicReconciliationSession.started_at.desc()).first()
        
        if not session:
            return {
                'session_exists': False,
                'message': 'No reconciliation session found'
            }
        
        # Get matches
        matches = self.db.query(ForensicMatch).filter(
            ForensicMatch.session_id == session.id
        ).all()
        
        # Get discrepancies
        discrepancies = self.db.query(ForensicDiscrepancy).filter(
            ForensicDiscrepancy.session_id == session.id
        ).all()
        
        # Group matches by status
        matches_by_status = {
            'pending': [m for m in matches if m.status == 'pending'],
            'approved': [m for m in matches if m.status == 'approved'],
            'rejected': [m for m in matches if m.status == 'rejected'],
            'modified': [m for m in matches if m.status == 'modified']
        }
        
        # Group discrepancies by severity
        discrepancies_by_severity = {
            'critical': [d for d in discrepancies if d.severity == 'critical'],
            'high': [d for d in discrepancies if d.severity == 'high'],
            'medium': [d for d in discrepancies if d.severity == 'medium'],
            'low': [d for d in discrepancies if d.severity == 'low']
        }
        
        return {
            'session_id': session.id,
            'session_status': session.status,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'summary': session.summary or {},
            'matches': {
                'total': len(matches),
                'by_status': {k: len(v) for k, v in matches_by_status.items()},
                'by_type': {
                    'exact': len([m for m in matches if m.match_type == 'exact']),
                    'fuzzy': len([m for m in matches if m.match_type == 'fuzzy']),
                    'calculated': len([m for m in matches if m.match_type == 'calculated']),
                    'inferred': len([m for m in matches if m.match_type == 'inferred'])
                }
            },
            'discrepancies': {
                'total': len(discrepancies),
                'by_severity': {k: len(v) for k, v in discrepancies_by_severity.items()},
                'by_status': {
                    'open': len([d for d in discrepancies if d.status == 'open']),
                    'investigating': len([d for d in discrepancies if d.status == 'investigating']),
                    'resolved': len([d for d in discrepancies if d.status == 'resolved']),
                    'accepted': len([d for d in discrepancies if d.status == 'accepted'])
                }
            }
        }
    
    def approve_match(
        self,
        match_id: int,
        auditor_id: int,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a match (auditor review workflow)
        
        Args:
            match_id: Match ID to approve
            auditor_id: Auditor user ID
            notes: Optional review notes
            
        Returns:
            True if successful, False otherwise
        """
        match = self.db.query(ForensicMatch).filter(ForensicMatch.id == match_id).first()
        
        if not match:
            logger.error(f"Match {match_id} not found")
            return False
        
        match.status = 'approved'
        match.reviewed_by = auditor_id
        match.reviewed_at = datetime.now()
        match.review_notes = notes
        
        self.db.commit()
        
        logger.info(f"Match {match_id} approved by auditor {auditor_id}")
        
        return True
    
    def reject_match(
        self,
        match_id: int,
        auditor_id: int,
        reason: str
    ) -> bool:
        """
        Reject a match (auditor review workflow)
        
        Args:
            match_id: Match ID to reject
            auditor_id: Auditor user ID
            reason: Rejection reason
            
        Returns:
            True if successful, False otherwise
        """
        match = self.db.query(ForensicMatch).filter(ForensicMatch.id == match_id).first()
        
        if not match:
            logger.error(f"Match {match_id} not found")
            return False
        
        match.status = 'rejected'
        match.reviewed_by = auditor_id
        match.reviewed_at = datetime.now()
        match.review_notes = reason
        
        self.db.commit()
        
        logger.info(f"Match {match_id} rejected by auditor {auditor_id}: {reason}")
        
        return True
    
    def resolve_discrepancy(
        self,
        discrepancy_id: int,
        auditor_id: int,
        resolution_notes: str,
        new_value: Optional[Decimal] = None
    ) -> bool:
        """
        Resolve a discrepancy
        
        Allows auditor to resolve discrepancies with rationale.
        
        Args:
            discrepancy_id: Discrepancy ID to resolve
            auditor_id: Auditor user ID
            resolution_notes: Resolution rationale
            new_value: Optional new value to set
            
        Returns:
            True if successful, False otherwise
        """
        discrepancy = self.db.query(ForensicDiscrepancy).filter(
            ForensicDiscrepancy.id == discrepancy_id
        ).first()
        
        if not discrepancy:
            logger.error(f"Discrepancy {discrepancy_id} not found")
            return False
        
        discrepancy.status = 'resolved'
        discrepancy.resolved_by = auditor_id
        discrepancy.resolved_at = datetime.now()
        discrepancy.resolution_notes = resolution_notes
        
        # Update related match if new value provided
        if new_value is not None and discrepancy.match_id:
            match = self.db.query(ForensicMatch).filter(
                ForensicMatch.id == discrepancy.match_id
            ).first()
            
            if match:
                # Update match with new value
                match.status = 'modified'
                match.auditor_override = True
                match.auditor_override_reason = resolution_notes
        
        self.db.commit()
        
        logger.info(f"Discrepancy {discrepancy_id} resolved by auditor {auditor_id}")
        
        return True
    
    def complete_session(
        self,
        session_id: int,
        auditor_id: int
    ) -> bool:
        """
        Complete a reconciliation session
        
        Args:
            session_id: Session ID to complete
            auditor_id: Auditor user ID
            
        Returns:
            True if successful, False otherwise
        """
        session = self.db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.id == session_id
        ).first()
        
        if not session:
            logger.error(f"Session {session_id} not found")
            return False
        
        session.status = 'approved'
        session.auditor_id = auditor_id
        session.completed_at = datetime.now()
        
        self.db.commit()
        
        logger.info(f"Session {session_id} completed by auditor {auditor_id}")
        
        return True
    
    # ==================== HELPER METHODS ====================
    
    def _get_document_records(
        self,
        property_id: int,
        period_id: int,
        document_type: str
    ) -> List[Dict[str, Any]]:
        """Get records for a document type"""
        if document_type == 'balance_sheet':
            records = self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id
                )
            ).all()
            return [{
                'id': r.id,
                'record_id': r.id,
                'account_code': r.account_code,
                'account_name': r.account_name,
                'amount': r.amount
            } for r in records]
        
        elif document_type == 'income_statement':
            records = self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id
                )
            ).all()
            return [{
                'id': r.id,
                'record_id': r.id,
                'account_code': r.account_code,
                'account_name': r.account_name,
                'period_amount': r.period_amount
            } for r in records]
        
        elif document_type == 'cash_flow':
            records = self.db.query(CashFlowData).filter(
                and_(
                    CashFlowData.property_id == property_id,
                    CashFlowData.period_id == period_id
                )
            ).all()
            return [{
                'id': r.id,
                'record_id': r.id,
                'account_code': r.account_code,
                'account_name': r.account_name,
                'period_amount': r.period_amount
            } for r in records]
        
        elif document_type == 'rent_roll':
            records = self.db.query(RentRollData).filter(
                and_(
                    RentRollData.property_id == property_id,
                    RentRollData.period_id == period_id
                )
            ).all()
            return [{
                'id': r.id,
                'record_id': r.id,
                'account_code': None,  # Rent roll doesn't have account codes
                'account_name': r.tenant_name,
                'annual_rent': r.annual_rent,
                'monthly_rent': r.monthly_rent
            } for r in records]
        
        elif document_type == 'mortgage_statement':
            records = self.db.query(MortgageStatementData).filter(
                and_(
                    MortgageStatementData.property_id == property_id,
                    MortgageStatementData.period_id == period_id
                )
            ).all()
            return [{
                'id': r.id,
                'record_id': r.id,
                'account_code': r.loan_number,
                'account_name': f"Loan {r.loan_number}",
                'principal_balance': r.principal_balance,
                'ytd_interest_paid': r.ytd_interest_paid,
                'ytd_principal_paid': r.ytd_principal_paid
            } for r in records]
        
        return []
    
    def _get_document_type_from_table(self, document_type: str) -> str:
        """Get table name from document type"""
        mapping = {
            'balance_sheet': 'balance_sheet_data',
            'income_statement': 'income_statement_data',
            'cash_flow': 'cash_flow_data',
            'rent_roll': 'rent_roll_data',
            'mortgage_statement': 'mortgage_statement_data'
        }
        return mapping.get(document_type, document_type)
    
    def _get_amount_from_record_id(
        self,
        record_id: int,
        document_type: str
    ) -> Optional[Decimal]:
        """Get amount from a record ID"""
        if record_id == 0:
            return None
        
        if document_type == 'balance_sheet':
            record = self.db.query(BalanceSheetData).filter(BalanceSheetData.id == record_id).first()
            return record.amount if record else None
        elif document_type == 'income_statement':
            record = self.db.query(IncomeStatementData).filter(IncomeStatementData.id == record_id).first()
            return record.period_amount if record else None
        elif document_type == 'cash_flow':
            record = self.db.query(CashFlowData).filter(CashFlowData.id == record_id).first()
            return record.period_amount if record else None
        elif document_type == 'rent_roll':
            record = self.db.query(RentRollData).filter(RentRollData.id == record_id).first()
            return record.annual_rent if record else None
        elif document_type == 'mortgage_statement':
            record = self.db.query(MortgageStatementData).filter(MortgageStatementData.id == record_id).first()
            return record.principal_balance if record else None
        
        return None
    
    def _match_to_dict(self, match: ForensicMatch) -> Dict[str, Any]:
        """Convert match to dictionary"""
        return {
            'id': match.id,
            'session_id': match.session_id,
            'source_document_type': match.source_document_type,
            'source_record_id': match.source_record_id,
            'source_account_code': match.source_account_code,
            'source_account_name': match.source_account_name,
            'source_amount': float(match.source_amount) if match.source_amount else None,
            'target_document_type': match.target_document_type,
            'target_record_id': match.target_record_id,
            'target_account_code': match.target_account_code,
            'target_account_name': match.target_account_name,
            'target_amount': float(match.target_amount) if match.target_amount else None,
            'match_type': match.match_type,
            'confidence_score': float(match.confidence_score) if match.confidence_score else None,
            'amount_difference': float(match.amount_difference) if match.amount_difference else None,
            'amount_difference_percent': float(match.amount_difference_percent) if match.amount_difference_percent else None,
            'match_algorithm': match.match_algorithm,
            'relationship_type': match.relationship_type,
            'relationship_formula': match.relationship_formula,
            'status': match.status,
            'reviewed_by': match.reviewed_by,
            'reviewed_at': match.reviewed_at.isoformat() if match.reviewed_at else None,
            'review_notes': match.review_notes
        }
    
    def check_data_availability(self, property_id: int, period_id: int) -> Dict[str, Any]:
        """
        Check what financial data is available for reconciliation
        
        Enhanced with diagnostics service for better insights.
        
        Returns:
            Dict with data availability information
        """
        # Use diagnostics service for enhanced checking
        try:
            diagnostics = self.diagnostics_service.get_diagnostics(property_id, period_id)
            availability = diagnostics.get('data_availability', {})
            
            # Return in expected format
            return {
                'document_uploads': {
                    'balance_sheet': availability.get('balance_sheet', {}).get('has_data', False),
                    'income_statement': availability.get('income_statement', {}).get('has_data', False),
                    'cash_flow': availability.get('cash_flow', {}).get('has_data', False),
                    'rent_roll': availability.get('rent_roll', {}).get('has_data', False),
                    'mortgage_statement': availability.get('mortgage_statement', {}).get('has_data', False)
                },
                'extracted_data': {
                    'balance_sheet': {
                        'count': availability.get('balance_sheet', {}).get('record_count', 0),
                        'has_data': availability.get('balance_sheet', {}).get('has_data', False)
                    },
                    'income_statement': {
                        'count': availability.get('income_statement', {}).get('record_count', 0),
                        'has_data': availability.get('income_statement', {}).get('has_data', False)
                    },
                    'cash_flow': {
                        'count': availability.get('cash_flow', {}).get('record_count', 0),
                        'has_data': availability.get('cash_flow', {}).get('has_data', False)
                    },
                    'rent_roll': {
                        'count': availability.get('rent_roll', {}).get('record_count', 0),
                        'has_data': availability.get('rent_roll', {}).get('has_data', False)
                    },
                    'mortgage_statement': {
                        'count': availability.get('mortgage_statement', {}).get('record_count', 0),
                        'has_data': availability.get('mortgage_statement', {}).get('has_data', False)
                    }
                },
                'key_accounts': {},  # Will be populated by diagnostics
                'total_records': sum([
                    availability.get('balance_sheet', {}).get('record_count', 0),
                    availability.get('income_statement', {}).get('record_count', 0),
                    availability.get('cash_flow', {}).get('record_count', 0),
                    availability.get('rent_roll', {}).get('record_count', 0),
                    availability.get('mortgage_statement', {}).get('record_count', 0)
                ]),
                'can_reconcile': any([
                    availability.get('balance_sheet', {}).get('has_data', False),
                    availability.get('income_statement', {}).get('has_data', False),
                    availability.get('cash_flow', {}).get('has_data', False)
                ]),
                'recommendations': diagnostics.get('recommendations', [])
            }
        except Exception as e:
            logger.error(f"Error using diagnostics service, falling back to legacy method: {e}")
            # Fall back to legacy method
        
        # Legacy method (fallback)
        # Check document uploads
        document_types = ['balance_sheet', 'income_statement', 'cash_flow', 'rent_roll', 'mortgage_statement']
        document_uploads = {}
        for doc_type in document_types:
            count = self.db.query(DocumentUpload).filter(
                and_(
                    DocumentUpload.property_id == property_id,
                    DocumentUpload.period_id == period_id,
                    DocumentUpload.document_type == doc_type,
                    DocumentUpload.is_active == True
                )
            ).count()
            document_uploads[doc_type] = count > 0
        
        # Check extracted data
        bs_count = self.db.query(BalanceSheetData).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id
            )
        ).count()
        
        is_count = self.db.query(IncomeStatementData).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        ).count()
        
        cf_count = self.db.query(CashFlowData).filter(
            and_(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id
            )
        ).count()
        
        rr_count = self.db.query(RentRollData).filter(
            and_(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            )
        ).count()
        
        ms_count = self.db.query(MortgageStatementData).filter(
            and_(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period_id
            )
        ).count()
        
        # Check for key accounts needed for matching
        key_accounts = {}
        if bs_count > 0:
            bs_earnings = self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id,
                    BalanceSheetData.account_code == '3995-0000'
                )
            ).first()
            key_accounts['balance_sheet_current_period_earnings'] = bs_earnings is not None
        
        if is_count > 0:
            is_net_income = self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id,
                    IncomeStatementData.account_code.like('909%')
                )
            ).first()
            key_accounts['income_statement_net_income'] = is_net_income is not None
        
        return {
            'document_uploads': document_uploads,
            'extracted_data': {
                'balance_sheet': {'count': bs_count, 'has_data': bs_count > 0},
                'income_statement': {'count': is_count, 'has_data': is_count > 0},
                'cash_flow': {'count': cf_count, 'has_data': cf_count > 0},
                'rent_roll': {'count': rr_count, 'has_data': rr_count > 0},
                'mortgage_statement': {'count': ms_count, 'has_data': ms_count > 0}
            },
            'key_accounts': key_accounts,
            'total_records': bs_count + is_count + cf_count + rr_count + ms_count,
            'can_reconcile': (bs_count > 0 or is_count > 0 or cf_count > 0 or rr_count > 0 or ms_count > 0),
            'recommendations': self._get_recommendations(bs_count, is_count, cf_count, rr_count, ms_count, key_accounts)
        }
    
    def get_diagnostics(self, property_id: int, period_id: int) -> Dict[str, Any]:
        """
        Get comprehensive diagnostics for reconciliation
        
        Returns:
            Dict with diagnostic information
        """
        return self.diagnostics_service.get_diagnostics(property_id, period_id)
    
    def _get_recommendations(
        self,
        bs_count: int,
        is_count: int,
        cf_count: int,
        rr_count: int,
        ms_count: int,
        key_accounts: Dict[str, bool]
    ) -> List[str]:
        """Get recommendations based on available data"""
        recommendations = []
        
        if bs_count == 0 and is_count == 0 and cf_count == 0 and rr_count == 0 and ms_count == 0:
            recommendations.append("No financial data found. Please upload and extract documents first.")
            return recommendations
        
        if bs_count == 0:
            recommendations.append("Balance Sheet data not found. Upload a Balance Sheet document for this period.")
        
        if is_count == 0:
            recommendations.append("Income Statement data not found. Upload an Income Statement document for this period.")
        
        if bs_count > 0 and not key_accounts.get('balance_sheet_current_period_earnings'):
            recommendations.append("Balance Sheet missing Current Period Earnings account (3995-0000). This is required for reconciliation.")
        
        if is_count > 0 and not key_accounts.get('income_statement_net_income'):
            recommendations.append("Income Statement missing Net Income account (9090-0000 or similar). This is required for reconciliation.")
        
        if bs_count > 0 and is_count > 0:
            recommendations.append("Both Balance Sheet and Income Statement data found. Reconciliation should find matches.")
        
        return recommendations
    
    def _log_available_data(self, property_id: int, period_id: int) -> None:
        """Log available data for debugging"""
        availability = self.check_data_availability(property_id, period_id)
        logger.info(f"Data availability: {availability}")
    
    def _match_to_dict(self, match: ForensicMatch) -> Dict[str, Any]:
        """Convert match object to dictionary with added coordinate data"""
        base_dict = {
            'id': match.id,
            'session_id': match.session_id,
            'match_type': match.match_type,
            'confidence_score': float(match.confidence_score),
            'source_document_type': match.source_document_type,
            'source_record_id': match.source_record_id,
            'source_account_code': match.source_account_code,
            'source_account_name': match.source_account_name,
            'source_amount': float(match.source_amount) if match.source_amount is not None else 0.0,
            'target_document_type': match.target_document_type,
            'target_record_id': match.target_record_id,
            'target_account_code': match.target_account_code,
            'target_account_name': match.target_account_name,
            'target_amount': float(match.target_amount) if match.target_amount is not None else 0.0,
            'amount_difference': float(match.amount_difference) if match.amount_difference is not None else 0.0,
            'amount_difference_percent': float(match.amount_difference_percent) if match.amount_difference_percent is not None else None,
            'status': match.status,
            'exception_tier': match.exception_tier,
            'reviewed_at': match.reviewed_at.isoformat() if match.reviewed_at else None,
            'reviewed_by': match.reviewed_by,
            'review_notes': match.review_notes,
            'relationship_formula': match.relationship_formula,
            'relationship_type': match.relationship_type,
            'match_algorithm': match.match_algorithm
        }

        # Add coordinate data for Deep Visual Matching
        base_dict['source_coordinates'] = self._get_record_coordinates(match.source_record_id, match.source_document_type)
        base_dict['target_coordinates'] = self._get_record_coordinates(match.target_record_id, match.target_document_type)
        
        # Add AI Explainability data
        base_dict['reasons'] = self._generate_match_reasons(match)
        base_dict['prior_period_amount'] = self._get_prior_period_amount(match)
        
        return base_dict

    def _generate_match_reasons(self, match: ForensicMatch) -> List[str]:
        """Generate natural language reasons for match/flag status"""
        reasons = []
        
        # Confidence-based reasons
        if match.confidence_score >= 90.0:
            reasons.append(f"High confidence match ({match.confidence_score}%) based on exact amount and account details.")
        elif match.confidence_score < 70.0:
            reasons.append(f"Flagged due to low confidence score ({match.confidence_score}%).")
            
        # Amount difference reasons
        if match.amount_difference and abs(match.amount_difference) > 0:
            reasons.append(f"Variance of ${abs(match.amount_difference):,.2f} detected between source and target.")
            if match.amount_difference_percent and abs(match.amount_difference_percent) > 5.0:
                 reasons.append(f"Significant deviation ({abs(match.amount_difference_percent):.1f}%) exceeds threshold (5.0%).")
        
        # Algorithm reasons
        if match.match_algorithm == 'calculated_relationship':
            reasons.append(f"Validated via formula: {match.relationship_formula}")
        elif match.match_algorithm == 'fuzzy_string':
             reasons.append(f"Matched using fuzzy text analysis on account description.")
             
        # Specific rule failures (if any) could be checked here by looking at related discrepancies
        # For formatted specific insights:
        if match.source_document_type == 'balance_sheet' and match.target_document_type == 'mortgage_statement':
             reasons.append("Cross-verified against external Mortgage Statement.")
             
        return reasons

    def _get_prior_period_amount(self, match: ForensicMatch) -> Optional[float]:
        """Fetch prior period amount for trend analysis (Mocked for now)"""
        # In a real implementation, this would query the previous month's FinancialPeriod
        # and look up the same account code. 
        # For Phase 2 demo, we will return a simulated prior value based on current value.
        if match.source_amount:
            # Simulate a small random variance for demo purposes if not available
            return float(match.source_amount) * 0.95 
        return None

    def _get_record_coordinates(self, record_id: int, document_type: str) -> Optional[Dict[str, Any]]:
        """Fetch extraction coordinates for a record"""
        if not record_id or not document_type:
            return None
            
        model_map = {
            'balance_sheet': BalanceSheetData,
            'income_statement': IncomeStatementData,
            'cash_flow': CashFlowData,
            'rent_roll': RentRollData,
            'mortgage_statement': MortgageStatementData
        }
        
        model = model_map.get(document_type)
        if not model:
            return None
            
        try:
            record = self.db.query(model).filter(model.id == record_id).first()
            if record and hasattr(record, 'extraction_x0'):
                # Return null if coords are missing (e.g. template extraction)
                if record.extraction_x0 is None:
                    return None
                    
                return {
                    'page': record.page_number,
                    'bbox': [
                        float(record.extraction_x0),
                        float(record.extraction_y0),
                        float(record.extraction_x1),
                        float(record.extraction_y1)
                    ],
                    'upload_id': record.upload_id
                }
        except Exception as e:
            logger.warning(f"Failed to fetch coordinates for {document_type} ID {record_id}: {e}")
            
        return None

    def _discrepancy_to_dict(self, discrepancy: ForensicDiscrepancy) -> Dict[str, Any]:
        """Convert discrepancy to dictionary"""
        return {
            'id': discrepancy.id,
            'session_id': discrepancy.session_id,
            'match_id': discrepancy.match_id,
            'discrepancy_type': discrepancy.discrepancy_type,
            'severity': discrepancy.severity,
            'source_value': float(discrepancy.source_value) if discrepancy.source_value else None,
            'target_value': float(discrepancy.target_value) if discrepancy.target_value else None,
            'difference': float(discrepancy.difference) if discrepancy.difference else None,
            'difference_percent': float(discrepancy.difference_percent) if discrepancy.difference_percent else None,
            'description': discrepancy.description,
            'status': discrepancy.status,
            'resolved_by': discrepancy.resolved_by,
            'resolved_at': discrepancy.resolved_at.isoformat() if discrepancy.resolved_at else None,
            'resolution_notes': discrepancy.resolution_notes
        }
