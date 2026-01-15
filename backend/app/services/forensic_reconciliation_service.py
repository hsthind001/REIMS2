"""
Forensic Reconciliation Service

Comprehensive service for forensic financial document reconciliation across
Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement.

Manages reconciliation sessions, finds matches using multiple engines,
validates discrepancies, and provides auditor review workflows.
"""
import logging
import decimal
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, true

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
from app.services.calculated_rules_engine import CalculatedRulesEngine
# from app.services.forensic_matching_rules import ForensicMatchingRules
from app.services.adaptive_matching_service import AdaptiveMatchingService
from app.services.match_learning_service import MatchLearningService
from app.services.reconciliation_diagnostics_service import ReconciliationDiagnosticsService
from app.services.relationship_discovery_service import RelationshipDiscoveryService
from app.services.exception_tiering_service import ExceptionTieringService

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
        self.matching_rules = AdaptiveMatchingService(db)  # Use adaptive matching
        self.learning_service = MatchLearningService(db)
        self.diagnostics_service = ReconciliationDiagnosticsService(db)
        self.relationship_service = RelationshipDiscoveryService(db)
        self.tiering_service = ExceptionTieringService(db)
    
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
        
        # 1. Execute cross-document matching rules (now uses adaptive matching)
        if use_rules:
            # Log available data for debugging
            logger.info(f"Checking available data for property {property_id}, period {period_id}")
            self._log_available_data(property_id, period_id)
            
            # Use adaptive matching which discovers codes and uses learned patterns
            rule_matches = self.matching_rules.find_all_matches(
                property_id=property_id,
                period_id=period_id,
                prior_period_id=prior_period_id
            )
            logger.info(f"Found {len(rule_matches)} rule-based matches (adaptive + hard-coded)")
            all_matches.extend(rule_matches)
            
            # Learn from matches after reconciliation completes
            # This will be done in a background task
        
        # 2. Execute matching engines for document-to-document comparisons
        # Note: Most cross-document matching is handled by rules above
        # Engines are primarily for same-document-type matching or specific use cases
        # For now, we'll focus on rules-based matching which covers most scenarios
        
        # Store matches in database with robust error handling
        stored_matches = []
        failed_matches = []
        
        for match in all_matches:
            try:
                # Determine source and target document types from records
                source_doc_type = self._get_document_type_from_record_id(match.source_record_id, property_id, period_id)
                target_doc_type = self._get_document_type_from_record_id(match.target_record_id, property_id, period_id)
                
                # Skip if document types are unknown (can't store without knowing document types)
                if source_doc_type == 'unknown' or target_doc_type == 'unknown':
                    logger.warning(
                        f"Skipping match: unknown document type (source_id={match.source_record_id}, "
                        f"target_id={match.target_record_id}, source_type={source_doc_type}, target_type={target_doc_type})"
                    )
                    failed_matches.append({
                        'match': match,
                        'reason': f'Unknown document type (source: {source_doc_type}, target: {target_doc_type})'
                    })
                    continue
                
                # Get source and target record details for storage (with fallback)
                source_record_details = self._get_record_details(match.source_record_id, source_doc_type) or {}
                target_record_details = self._get_record_details(match.target_record_id, target_doc_type) or {}
                
                # Convert MatchResult to database record (use minimal data if details unavailable)
                match_record = ForensicMatch(
                    session_id=session_id,
                    source_document_type=source_doc_type,
                    source_table_name=self._get_table_name(source_doc_type),
                    source_record_id=match.source_record_id,
                    source_account_code=source_record_details.get('account_code'),
                    source_account_name=source_record_details.get('account_name') or 'Unknown',
                    source_amount=source_record_details.get('amount'),
                    source_field_name=source_record_details.get('field_name'),
                    target_document_type=target_doc_type,
                    target_table_name=self._get_table_name(target_doc_type),
                    target_record_id=match.target_record_id,
                    target_account_code=target_record_details.get('account_code'),
                    target_account_name=target_record_details.get('account_name') or 'Unknown',
                    target_amount=target_record_details.get('amount'),
                    target_field_name=target_record_details.get('field_name'),
                    match_type=match.match_type,
                    confidence_score=Decimal(str(match.confidence_score)),
                    amount_difference=match.amount_difference,
                    amount_difference_percent=Decimal(str(match.amount_difference_percent)) if match.amount_difference_percent else None,
                    match_algorithm=match.match_algorithm or 'adaptive',
                    relationship_type=match.relationship_type,
                    relationship_formula=match.relationship_formula,
                    status='pending'
                )
                
                self.db.add(match_record)
                stored_matches.append(match_record)
                
            except Exception as e:
                logger.warning(
                    f"Failed to store match (source_id={match.source_record_id}, target_id={match.target_record_id}): {e}",
                    exc_info=True
                )
                failed_matches.append({
                    'match': match,
                    'reason': str(e)
                })
                # Continue processing other matches even if one fails
                continue
        
        # Commit all successfully stored matches
        if stored_matches:
            try:
                self.db.commit()
                logger.info(f"Successfully stored {len(stored_matches)} matches for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to commit matches: {e}", exc_info=True)
                self.db.rollback()
                # Try to store matches individually if batch commit fails
                individual_stored = []
                for match_record in stored_matches:
                    try:
                        self.db.add(match_record)
                        self.db.commit()
                        individual_stored.append(match_record)
                    except Exception as commit_error:
                        logger.error(f"Failed to commit individual match: {commit_error}")
                        self.db.rollback()
                stored_matches = individual_stored
        
        if failed_matches:
            logger.warning(f"Failed to store {len(failed_matches)} matches out of {len(all_matches)} total matches")
        
        # Apply exception tiering to all matches (with proper transaction isolation)
        # Tiering is optional - if it fails, we continue without it
        tiering_results = []
        tiering_failures = []
        
        try:
            # Clear any stale object state before tiering
            self.db.expire_all()
            
            for match in stored_matches:
                try:
                    # Ensure we're in a clean transaction state - rollback any failed transaction first
                    try:
                        self.db.rollback()
                    except Exception:
                        pass  # Ignore rollback errors if already clean
                    
                    # Get fresh match object from database to avoid stale state
                    fresh_match = self.db.query(ForensicMatch).filter(
                        ForensicMatch.id == match.id
                    ).first()
                    
                    if not fresh_match:
                        logger.warning(f"Match {match.id} not found in database, skipping tiering")
                        continue
                    
                    # Now apply tiering in a fresh transaction
                    try:
                        tiering_result = self.tiering_service.classify_and_apply_tiering(
                            fresh_match,
                            auto_resolve=True  # Auto-resolve tier 0 matches
                        )
                        tiering_results.append(tiering_result)
                        # Commit tiering changes for this match
                        self.db.commit()
                    except Exception as tiering_error:
                        logger.error(f"Error applying tiering to match {match.id}: {tiering_error}", exc_info=True)
                        # Rollback this match's tiering attempt
                        try:
                            self.db.rollback()
                        except Exception:
                            pass
                        tiering_failures.append({'match_id': match.id, 'error': str(tiering_error)})
                        # Continue with other matches even if one fails
                        continue
                except Exception as e:
                    logger.error(f"Error in tiering loop for match {match.id}: {e}", exc_info=True)
                    # Rollback and continue
                    try:
                        self.db.rollback()
                    except Exception:
                        pass
                    tiering_failures.append({'match_id': match.id, 'error': str(e)})
                    # Continue with other matches even if one fails
                    continue
        except Exception as e:
            logger.error(f"Critical error in tiering process: {e}", exc_info=True)
            # Rollback everything and continue - tiering is optional
            try:
                self.db.rollback()
            except Exception:
                pass
            # Don't fail the entire reconciliation if tiering fails
        
        # Re-query all matches from database to get fresh state (after tiering)
        # This ensures we have the latest data and avoids stale transaction state
        try:
            # Clear any stale object state
            self.db.expire_all()
            
            # Ensure clean transaction
            try:
                self.db.rollback()
            except Exception:
                pass
            
            # Re-query all matches for this session
            fresh_matches = self.db.query(ForensicMatch).filter(
                ForensicMatch.session_id == session_id
            ).all()
            
            # Update stored_matches with fresh data
            stored_matches = fresh_matches
            logger.info(f"Re-queried {len(stored_matches)} matches after tiering")
        except Exception as e:
            logger.warning(f"Failed to re-query matches after tiering: {e}", exc_info=True)
            # Use stored_matches as-is if re-query fails
            try:
                self.db.rollback()
            except Exception:
                pass
        
        # Group matches by type (using fresh data)
        matches_by_type = {
            'exact': [m for m in stored_matches if m.match_type == 'exact'],
            'fuzzy': [m for m in stored_matches if m.match_type == 'fuzzy'],
            'calculated': [m for m in stored_matches if m.match_type == 'calculated'],
            'inferred': [m for m in stored_matches if m.match_type == 'inferred']
        }
        
        # Calculate summary with tiering breakdown (using fresh data)
        tier_breakdown = {
            'tier_0_auto_close': len([m for m in stored_matches if m.exception_tier == 'tier_0_auto_close']),
            'tier_1_auto_suggest': len([m for m in stored_matches if m.exception_tier == 'tier_1_auto_suggest']),
            'tier_2_route': len([m for m in stored_matches if m.exception_tier == 'tier_2_route']),
            'tier_3_escalate': len([m for m in stored_matches if m.exception_tier == 'tier_3_escalate'])
        }
        
        summary = {
            'total_matches': len(stored_matches),
            'exact_matches': len(matches_by_type['exact']),
            'fuzzy_matches': len(matches_by_type['fuzzy']),
            'calculated_matches': len(matches_by_type['calculated']),
            'inferred_matches': len(matches_by_type['inferred']),
            'pending_review': len([m for m in stored_matches if m.status == 'pending']),
            'approved': len([m for m in stored_matches if m.status == 'approved']),
            'rejected': len([m for m in stored_matches if m.status == 'rejected']),
            'tier_breakdown': tier_breakdown
        }
        
        # Update session summary (with transaction safety)
        try:
            # Ensure clean transaction state before updating session
            try:
                self.db.rollback()  # Rollback any failed transaction
            except Exception:
                pass
            
            # Re-query session to get fresh state (don't use refresh on potentially stale object)
            session = self.db.query(ForensicReconciliationSession).filter(
                ForensicReconciliationSession.id == session_id
            ).first()
            
            if session:
                session.summary = summary
                self.db.commit()
            else:
                logger.error(f"Session {session_id} not found when updating summary")
        except Exception as e:
            logger.error(f"Failed to update session summary: {e}", exc_info=True)
            # Rollback and try again
            try:
                self.db.rollback()
                # Re-query session to get fresh state
                session = self.db.query(ForensicReconciliationSession).filter(
                    ForensicReconciliationSession.id == session_id
                ).first()
                if session:
                    session.summary = summary
                    self.db.commit()
            except Exception as retry_error:
                logger.error(f"Failed to update session summary on retry: {retry_error}")
                try:
                    self.db.rollback()
                except Exception:
                    pass
                # Continue anyway - matches are stored
        
        logger.info(f"Found {len(stored_matches)} matches for session {session_id} (failed: {len(failed_matches)}, tiering failures: {len(tiering_failures)})")
        
        # Build response with diagnostic information
        # Use fresh matches from database (already re-queried above)
        try:
            # Final safety check - ensure we have clean transaction state
            try:
                self.db.rollback()
            except Exception:
                pass
            
            # Build response from fresh match objects
            response = {
                'session_id': session_id,
                'matches': [self._match_to_dict(m) for m in stored_matches],
                'matches_by_type': {
                    k: [self._match_to_dict(m) for m in v] for k, v in matches_by_type.items()
                },
                'summary': summary
            }
            
            # Add diagnostic information if there were failures
            diagnostic_info = {}
            if failed_matches:
                diagnostic_info['matches_failed'] = len(failed_matches)
                diagnostic_info['failure_reasons'] = [f['reason'] for f in failed_matches[:5]]  # First 5 reasons
            
            if tiering_failures:
                diagnostic_info['tiering_failures'] = len(tiering_failures)
                diagnostic_info['tiering_warning'] = f"Tiering failed for {len(tiering_failures)} matches but matches were still stored"
            
            if diagnostic_info:
                diagnostic_info['total_matches_found'] = len(all_matches)
                diagnostic_info['matches_stored'] = len(stored_matches)
                response['diagnostic'] = diagnostic_info
            
            return response
        except Exception as e:
            logger.error(f"Error building response: {e}", exc_info=True)
            # Even if response building fails, return what we have
            try:
                self.db.rollback()
            except Exception:
                pass
            
            # Return minimal response with matches
            return {
                'session_id': session_id,
                'matches': [self._match_to_dict(m) for m in stored_matches] if stored_matches else [],
                'matches_by_type': {},
                'summary': summary,
                'warning': f'Error building full response: {str(e)}'
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
                    difference_percent=self._clamp_percent(match.amount_difference_percent),
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
                    difference_percent=self._clamp_percent(match.amount_difference_percent),
                    description=f"Large amount difference (${match.amount_difference:,.2f}) between {match.source_document_type} and {match.target_document_type}",
                    status='open'
                )
                discrepancies.append(discrepancy)
                self.db.add(discrepancy)
        
        # ==================== CALCULATED RULE VALIDATION ====================
        rule_results = []
        failed_rule_count = 0
        try:
            engine = CalculatedRulesEngine(self.db)
            rule_results = engine.evaluate_rules(
                property_id=session.property_id,
                period_id=session.period_id
            )

            for result in rule_results:
                if result.get('status') == 'FAIL':
                    failed_rule_count += 1
                    severity_map = {
                        'critical': 'critical',
                        'high': 'high',
                        'warning': 'medium',
                        'info': 'low',
                        'low': 'low',
                        'medium': 'medium'
                    }
                    severity = severity_map.get(result.get('severity', '').lower(), 'medium')
                    discrepancy = ForensicDiscrepancy(
                        session_id=session_id,
                        match_id=None,
                        discrepancy_type='rule_failure',
                        severity=severity,
                        source_value=Decimal(str(result.get('expected_value'))) if result.get('expected_value') is not None else None,
                        target_value=Decimal(str(result.get('actual_value'))) if result.get('actual_value') is not None else None,
                        expected_value=Decimal(str(result.get('expected_value'))) if result.get('expected_value') is not None else None,
                        actual_value=Decimal(str(result.get('actual_value'))) if result.get('actual_value') is not None else None,
                        difference=Decimal(str(result.get('difference'))) if result.get('difference') is not None else None,
                        difference_percent=self._clamp_percent(result.get('difference_percent')),
                        description=result.get('message') or f"Rule {result.get('rule_id')} failed",
                        status='open'
                    )
                    discrepancies.append(discrepancy)
                    self.db.add(discrepancy)
        except Exception as rule_error:
            logger.warning(f"Calculated rule evaluation failed: {rule_error}")
        
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
            
            # Simple weighted score
            score = 100.0
            score -= (high_discrepancies * 15.0)
            score -= (critical_discrepancies * 25.0)
            score -= ((total_matches - high_confidence_matches) * 2.0)
            
            health_score = max(0.0, min(100.0, score))
        
        # Update session
        session.status = 'completed'
        session.health_score = health_score
        session.discrepancy_count = len(discrepancies)
        session.ended_at = datetime.utcnow()
        session.summary = {
            'total_matches': len(matches),
            'discrepancies': len(discrepancies),
            'rule_failures': failed_rule_count,
            'health_score': health_score,
            'critical_discrepancies': len([d for d in discrepancies if d.severity == 'critical']),
            'rules_total': len(rule_results),
            'rules_failed': failed_rule_count
        }
        
        self.db.commit()
        
        return {
            'session_id': session.id,
            'status': session.status,
            'health_score': float(session.health_score) if session.health_score is not None else 0.0,
            'discrepancies': [self._discrepancy_to_dict(d) for d in discrepancies]
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
        if record_id is None or record_id == 0:
            return 'unknown'
        
        try:
            # Check each document type (with property/period filters for efficiency)
            if self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.id == record_id,
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id
                )
            ).first():
                return 'balance_sheet'
            
            if self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.id == record_id,
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id
                )
            ).first():
                return 'income_statement'
            
            if self.db.query(CashFlowData).filter(
                and_(
                    CashFlowData.id == record_id,
                    CashFlowData.property_id == property_id,
                    CashFlowData.period_id == period_id
                )
            ).first():
                return 'cash_flow'
            
            if self.db.query(RentRollData).filter(
                and_(
                    RentRollData.id == record_id,
                    RentRollData.property_id == property_id,
                    RentRollData.period_id == period_id
                )
            ).first():
                return 'rent_roll'
            
            if self.db.query(MortgageStatementData).filter(
                and_(
                    MortgageStatementData.id == record_id,
                    MortgageStatementData.property_id == property_id,
                    MortgageStatementData.period_id == period_id
                )
            ).first():
                return 'mortgage_statement'
            
            # Fallback: check without property/period filters (slower but more reliable)
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
            
        except Exception as e:
            logger.warning(f"Error determining document type for record {record_id}: {e}")
            return 'unknown'
        
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
        if record_id is None or record_id == 0:
            return {}
        
        try:
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
                        'account_name': record.tenant_name or 'Unknown Tenant',
                        'amount': record.annual_rent or 0,
                        'field_name': 'annual_rent'
                    }
            elif document_type == 'mortgage_statement':
                record = self.db.query(MortgageStatementData).filter(MortgageStatementData.id == record_id).first()
                if record:
                    return {
                        'account_code': record.loan_number,
                        'account_name': f"Loan {record.loan_number}",
                        'amount': record.principal_balance or 0,
                        'field_name': 'principal_balance'
                    }
        except Exception as e:
            logger.warning(f"Error getting record details for {document_type} record {record_id}: {e}")
            return {}
        
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
