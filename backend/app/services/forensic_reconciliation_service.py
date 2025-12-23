"""
Forensic Reconciliation Service

Comprehensive service for forensic financial document reconciliation across
Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement.

Manages reconciliation sessions, finds matches using multiple engines,
validates discrepancies, and provides auditor review workflows.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

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

from app.services.matching_engines import (
    ExactMatchEngine,
    FuzzyMatchEngine,
    CalculatedMatchEngine,
    InferredMatchEngine,
    MatchResult
)
from app.services.forensic_matching_rules import ForensicMatchingRules

logger = logging.getLogger(__name__)


class ForensicReconciliationService:
    """Service for forensic reconciliation across all document types"""
    
    def __init__(self, db: Session):
        """
        Initialize forensic reconciliation service
        
        Args:
            db: Database session
        """
        self.db = db
        self.exact_engine = ExactMatchEngine()
        self.fuzzy_engine = FuzzyMatchEngine()
        self.calculated_engine = CalculatedMatchEngine()
        self.inferred_engine = InferredMatchEngine()
        self.matching_rules = ForensicMatchingRules(db)
    
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
                DocumentUpload.is_active == True
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
        Execute all matching engines and find matches across documents
        
        Args:
            session_id: Reconciliation session ID
            use_exact: Use exact matching engine
            use_fuzzy: Use fuzzy matching engine
            use_calculated: Use calculated matching engine
            use_inferred: Use inferred matching engine
            use_rules: Use cross-document matching rules
            
        Returns:
            Dict with matches grouped by type and summary statistics
        """
        session = self.db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.id == session_id
        ).first()
        
        if not session:
            logger.error(f"Session {session_id} not found")
            return {'error': 'Session not found'}
        
        property_id = session.property_id
        period_id = session.period_id
        
        all_matches = []
        
        # Get prior period for reconciliation rules
        period = self.db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        prior_period_id = None
        if period:
            # Find prior period (same property, previous month)
            prior_period = self.db.query(FinancialPeriod).filter(
                and_(
                    FinancialPeriod.property_id == property_id,
                    FinancialPeriod.period_year == period.period_year,
                    FinancialPeriod.period_month == period.period_month - 1
                )
            ).first()
            if not prior_period and period.period_month == 1:
                # Check previous year
                prior_period = self.db.query(FinancialPeriod).filter(
                    and_(
                        FinancialPeriod.property_id == property_id,
                        FinancialPeriod.period_year == period.period_year - 1,
                        FinancialPeriod.period_month == 12
                    )
                ).first()
            if prior_period:
                prior_period_id = prior_period.id
        
        # 1. Execute cross-document matching rules
        if use_rules:
            rule_matches = self.matching_rules.find_all_matches(
                property_id=property_id,
                period_id=period_id,
                prior_period_id=prior_period_id
            )
            all_matches.extend(rule_matches)
        
        # 2. Execute matching engines for document-to-document comparisons
        # Note: Most cross-document matching is handled by rules above
        # Engines are primarily for same-document-type matching or specific use cases
        # For now, we'll focus on rules-based matching which covers most scenarios
        
        # Store matches in database
        stored_matches = []
        for match in all_matches:
            # Determine source and target document types from records
            source_doc_type = self._get_document_type_from_record_id(match.source_record_id, property_id, period_id)
            target_doc_type = self._get_document_type_from_record_id(match.target_record_id, property_id, period_id)
            
            # Get source and target record details for storage
            source_record_details = self._get_record_details(match.source_record_id, source_doc_type)
            target_record_details = self._get_record_details(match.target_record_id, target_doc_type)
            
            # Convert MatchResult to database record
            match_record = ForensicMatch(
                session_id=session_id,
                source_document_type=source_doc_type,
                source_table_name=self._get_table_name(source_doc_type),
                source_record_id=match.source_record_id,
                source_account_code=source_record_details.get('account_code'),
                source_account_name=source_record_details.get('account_name'),
                source_amount=source_record_details.get('amount'),
                source_field_name=source_record_details.get('field_name'),
                target_document_type=target_doc_type,
                target_table_name=self._get_table_name(target_doc_type),
                target_record_id=match.target_record_id,
                target_account_code=target_record_details.get('account_code'),
                target_account_name=target_record_details.get('account_name'),
                target_amount=target_record_details.get('amount'),
                target_field_name=target_record_details.get('field_name'),
                match_type=match.match_type,
                confidence_score=Decimal(str(match.confidence_score)),
                amount_difference=match.amount_difference,
                amount_difference_percent=Decimal(str(match.amount_difference_percent)) if match.amount_difference_percent else None,
                match_algorithm=match.match_algorithm,
                relationship_type=match.relationship_type,
                relationship_formula=match.relationship_formula,
                status='pending'
            )
            
            self.db.add(match_record)
            stored_matches.append(match_record)
        
        self.db.commit()
        
        # Group matches by type
        matches_by_type = {
            'exact': [m for m in stored_matches if m.match_type == 'exact'],
            'fuzzy': [m for m in stored_matches if m.match_type == 'fuzzy'],
            'calculated': [m for m in stored_matches if m.match_type == 'calculated'],
            'inferred': [m for m in stored_matches if m.match_type == 'inferred']
        }
        
        # Calculate summary
        summary = {
            'total_matches': len(stored_matches),
            'exact_matches': len(matches_by_type['exact']),
            'fuzzy_matches': len(matches_by_type['fuzzy']),
            'calculated_matches': len(matches_by_type['calculated']),
            'inferred_matches': len(matches_by_type['inferred']),
            'pending_review': len([m for m in stored_matches if m.status == 'pending']),
            'approved': len([m for m in stored_matches if m.status == 'approved']),
            'rejected': len([m for m in stored_matches if m.status == 'rejected'])
        }
        
        # Update session summary
        session.summary = summary
        self.db.commit()
        
        logger.info(f"Found {len(stored_matches)} matches for session {session_id}")
        
        return {
            'session_id': session_id,
            'matches': [self._match_to_dict(m) for m in stored_matches],
            'matches_by_type': {
                k: [self._match_to_dict(m) for m in v] for k, v in matches_by_type.items()
            },
            'summary': summary
        }
    
    def validate_matches(
        self,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Validate all matches and identify discrepancies
        
        Runs validation rules and calculates reconciliation health score.
        
        Args:
            session_id: Reconciliation session ID
            
        Returns:
            Dict with validation results and health score
        """
        session = self.db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.id == session_id
        ).first()
        
        if not session:
            return {'error': 'Session not found'}
        
        # Get all matches
        matches = self.db.query(ForensicMatch).filter(
            ForensicMatch.session_id == session_id
        ).all()
        
        discrepancies = []
        validation_results = []
        
        for match in matches:
            # Check for discrepancies based on confidence and amount differences
            if match.confidence_score < 70.0:
                # Low confidence - potential discrepancy
                discrepancy = ForensicDiscrepancy(
                    session_id=session_id,
                    match_id=match.id,
                    discrepancy_type='amount_mismatch',
                    severity='medium' if match.confidence_score >= 50.0 else 'high',
                    source_value=match.source_amount,
                    target_value=match.target_amount,
                    expected_value=match.target_amount,  # Assuming target is expected
                    actual_value=match.source_amount,
                    difference=match.amount_difference,
                    difference_percent=match.amount_difference_percent,
                    description=f"Low confidence match ({match.confidence_score:.2f}%) between {match.source_document_type} and {match.target_document_type}",
                    status='open'
                )
                discrepancies.append(discrepancy)
                self.db.add(discrepancy)
            
            # Check for large amount differences
            if match.amount_difference and match.amount_difference > Decimal('1000'):
                discrepancy = ForensicDiscrepancy(
                    session_id=session_id,
                    match_id=match.id,
                    discrepancy_type='amount_mismatch',
                    severity='high' if match.amount_difference > Decimal('10000') else 'medium',
                    source_value=match.source_amount,
                    target_value=match.target_amount,
                    difference=match.amount_difference,
                    difference_percent=match.amount_difference_percent,
                    description=f"Large amount difference (${match.amount_difference:,.2f}) between {match.source_document_type} and {match.target_document_type}",
                    status='open'
                )
                discrepancies.append(discrepancy)
                self.db.add(discrepancy)
        
        self.db.commit()
        
        # Calculate health score
        total_matches = len(matches)
        if total_matches == 0:
            health_score = 0.0
        else:
            approved_matches = len([m for m in matches if m.status == 'approved'])
            high_confidence_matches = len([m for m in matches if m.confidence_score >= 90.0])
            critical_discrepancies = len([d for d in discrepancies if d.severity == 'critical'])
            high_discrepancies = len([d for d in discrepancies if d.severity == 'high'])
            
            # Health score calculation (0-100)
            # Base score from approved matches
            approval_score = (approved_matches / total_matches) * 40 if total_matches > 0 else 0
            
            # Confidence score
            confidence_score = (high_confidence_matches / total_matches) * 40 if total_matches > 0 else 0
            
            # Discrepancy penalty
            discrepancy_penalty = min(20, (critical_discrepancies * 10) + (high_discrepancies * 5))
            
            health_score = approval_score + confidence_score - discrepancy_penalty
            health_score = max(0.0, min(100.0, health_score))
        
        # Update session summary with health score
        if session.summary:
            session.summary['health_score'] = health_score
            session.summary['discrepancies'] = len(discrepancies)
            session.summary['critical_discrepancies'] = len([d for d in discrepancies if d.severity == 'critical'])
        else:
            session.summary = {
                'health_score': health_score,
                'discrepancies': len(discrepancies),
                'critical_discrepancies': len([d for d in discrepancies if d.severity == 'critical'])
            }
        
        self.db.commit()
        
        return {
            'session_id': session_id,
            'health_score': health_score,
            'total_matches': total_matches,
            'discrepancies': len(discrepancies),
            'discrepancy_details': [self._discrepancy_to_dict(d) for d in discrepancies]
        }
    
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
    
    def _get_table_name(self, document_type: str) -> str:
        """Get table name for document type"""
        mapping = {
            'balance_sheet': 'balance_sheet_data',
            'income_statement': 'income_statement_data',
            'cash_flow': 'cash_flow_data',
            'rent_roll': 'rent_roll_data',
            'mortgage_statement': 'mortgage_statement_data'
        }
        return mapping.get(document_type, document_type)
    
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
    
    def _get_document_type_from_record_id(
        self,
        record_id: int,
        property_id: int,
        period_id: int
    ) -> str:
        """Determine document type from record ID by checking all tables"""
        if record_id == 0:
            return 'unknown'
        
        # Check each document type
        if self.db.query(BalanceSheetData).filter(BalanceSheetData.id == record_id).first():
            return 'balance_sheet'
        if self.db.query(IncomeStatementData).filter(IncomeStatementData.id == record_id).first():
            return 'income_statement'
        if self.db.query(CashFlowData).filter(CashFlowData.id == record_id).first():
            return 'cash_flow'
        if self.db.query(RentRollData).filter(RentRollData.id == record_id).first():
            return 'rent_roll'
        if self.db.query(MortgageStatementData).filter(MortgageStatementData.id == record_id).first():
            return 'mortgage_statement'
        
        return 'unknown'
    
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
    
    def _get_record_details(
        self,
        record_id: int,
        document_type: str
    ) -> Dict[str, Any]:
        """Get full record details including account code, name, and amount"""
        if record_id == 0:
            return {}
        
        if document_type == 'balance_sheet':
            record = self.db.query(BalanceSheetData).filter(BalanceSheetData.id == record_id).first()
            if record:
                return {
                    'account_code': record.account_code,
                    'account_name': record.account_name,
                    'amount': record.amount,
                    'field_name': 'amount'
                }
        elif document_type == 'income_statement':
            record = self.db.query(IncomeStatementData).filter(IncomeStatementData.id == record_id).first()
            if record:
                return {
                    'account_code': record.account_code,
                    'account_name': record.account_name,
                    'amount': record.period_amount,
                    'field_name': 'period_amount'
                }
        elif document_type == 'cash_flow':
            record = self.db.query(CashFlowData).filter(CashFlowData.id == record_id).first()
            if record:
                return {
                    'account_code': record.account_code,
                    'account_name': record.account_name,
                    'amount': record.period_amount,
                    'field_name': 'period_amount'
                }
        elif document_type == 'rent_roll':
            record = self.db.query(RentRollData).filter(RentRollData.id == record_id).first()
            if record:
                return {
                    'account_code': None,
                    'account_name': record.tenant_name,
                    'amount': record.annual_rent,
                    'field_name': 'annual_rent'
                }
        elif document_type == 'mortgage_statement':
            record = self.db.query(MortgageStatementData).filter(MortgageStatementData.id == record_id).first()
            if record:
                return {
                    'account_code': record.loan_number,
                    'account_name': f"Loan {record.loan_number}",
                    'amount': record.principal_balance,
                    'field_name': 'principal_balance'
                }
        
        return {}
    
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

