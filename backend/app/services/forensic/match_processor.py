import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.forensic_match import ForensicMatch
from app.models.financial_period import FinancialPeriod
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
from app.services.adaptive_matching_service import AdaptiveMatchingService
from app.services.exception_tiering_service import ExceptionTieringService

logger = logging.getLogger(__name__)

class ForensicMatchProcessor:
    """
    Processor for executing forensic matching logic.
    Separated from the main service to adhere to Single Responsibility Principle.
    """

    def __init__(
        self, 
        db: Session,
        matching_rules: AdaptiveMatchingService,
        tiering_service: ExceptionTieringService,
        exact_engine: Optional[ExactMatchEngine] = None,
        fuzzy_engine: Optional[FuzzyMatchEngine] = None,
        calculated_engine: Optional[CalculatedMatchEngine] = None,
        inferred_engine: Optional[InferredMatchEngine] = None
    ):
        self.db = db
        self.matching_rules = matching_rules
        self.tiering_service = tiering_service
        
        # Helper engines - injected or defaulted
        self.exact_engine = exact_engine or ExactMatchEngine()
        self.fuzzy_engine = fuzzy_engine or FuzzyMatchEngine()
        self.calculated_engine = calculated_engine or CalculatedMatchEngine()
        self.inferred_engine = inferred_engine or InferredMatchEngine()

    def process_matches(
        self,
        session_id: int,
        property_id: int,
        period_id: int,
        use_exact: bool = True,
        use_fuzzy: bool = True,
        use_calculated: bool = True,
        use_inferred: bool = True,
        use_rules: bool = True
    ) -> Dict[str, Any]:
        """
        Process matches for a session
        
        Orchestrates the matching process:
        1. Clears existing matches
        2. Runs matching engines
        3. Applies tiering logic
        4. Stores results
        """
        logger.info(f"Processing matches for session {session_id} (Prop: {property_id}, Period: {period_id})")
        
        # Clear existing matches for this session to ensure idempotency
        # This prevents duplicate matches if the reconciliation is run multiple times for the same session
        try:
            self.db.query(ForensicMatch).filter(ForensicMatch.session_id == session_id).delete()
            # We flush to ensure the delete happens before new inserts, 
            # though usually SQLAlchemy handles this in transaction flush order.
            self.db.flush()
        except Exception as e:
            logger.error(f"Error clearing existing matches for session {session_id}: {e}")
            # Continue, as we might be starting fresh anyway

        # Verify deletion and build existing set if needed
        existing_matches_set = set()
        try:
            existing_count = self.db.query(ForensicMatch).filter(ForensicMatch.session_id == session_id).count()
            if existing_count > 0:
                logger.warning(f"Deletion incomplete, found {existing_count} existing matches for session {session_id}. Enabling deduplication.")
                existing_rows = self.db.query(ForensicMatch.source_record_id, ForensicMatch.target_record_id).filter(ForensicMatch.session_id == session_id).all()
                for row in existing_rows:
                    existing_matches_set.add((row.source_record_id, row.target_record_id))
        except Exception as e:
            logger.error(f"Error checking existing matches: {e}")

        all_matches = []
        
        # Get prior period for reconciliation rules
        period = self.db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        prior_period_id = self._get_prior_period_id(property_id, period)
        
        # 1. Execute cross-document matching rules (adaptive matching)
        if use_rules:
            try:
                rule_matches = self.matching_rules.find_all_matches(
                    property_id=property_id,
                    period_id=period_id,
                    prior_period_id=prior_period_id
                )
                
                # Deduplicate matches before adding
                for match in rule_matches:
                    pair = (match.source_record_id, match.target_record_id)
                    if pair not in existing_matches_set:
                        all_matches.append(match)
                        existing_matches_set.add(pair)
                    else:
                        logger.debug(f"Skipping duplicate match pair: {pair}")
                        
                logger.info(f"Found {len(rule_matches)} rule-based matches")
            except Exception as e:
                logger.error(f"Error running matching rules: {e}", exc_info=True)
            
        # 2. Execute other engines if needed (placeholder for now as per original code)

        return self._prepare_and_store_matches(session_id, property_id, period_id, all_matches)

    def _get_prior_period_id(self, property_id: int, period: Optional[FinancialPeriod]) -> Optional[int]:
        if not period:
            return None
        
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
            
        return prior_period.id if prior_period else None

    def _prepare_and_store_matches(
        self, 
        session_id: int, 
        property_id: int, 
        period_id: int, 
        match_results: List[MatchResult]
    ) -> Dict[str, Any]:
        """
        Convert MatchResults to ForensicMatch objects and add to session.
        Does NOT commit.
        """
        stored_matches = []
        failed_matches = []

        for match in match_results:
            try:
                # Determine source and target document types
                source_doc_type = self._get_document_type(match.source_record_id, property_id, period_id)
                target_doc_type = self._get_document_type(match.target_record_id, property_id, period_id)
                
                if source_doc_type == 'unknown' or target_doc_type == 'unknown':
                    failed_matches.append({
                        'match': match,
                        'reason': f'Unknown document type (source: {source_doc_type}, target: {target_doc_type})'
                    })
                    continue

                # Get details
                source_details = self._get_record_details(match.source_record_id, source_doc_type) or {}
                target_details = self._get_record_details(match.target_record_id, target_doc_type) or {}

                match_record = ForensicMatch(
                    session_id=session_id,
                    source_document_type=source_doc_type,
                    source_table_name=self._get_table_name(source_doc_type),
                    source_record_id=match.source_record_id,
                    source_account_code=source_details.get('account_code'),
                    source_account_name=source_details.get('account_name') or 'Unknown',
                    source_amount=source_details.get('amount'),
                    source_field_name=source_details.get('field_name'),
                    target_document_type=target_doc_type,
                    target_table_name=self._get_table_name(target_doc_type),
                    target_record_id=match.target_record_id,
                    target_account_code=target_details.get('account_code'),
                    target_account_name=target_details.get('account_name') or 'Unknown',
                    target_amount=target_details.get('amount'),
                    target_field_name=target_details.get('field_name'),
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
                logger.warning(f"Failed to process match: {e}")
                failed_matches.append({'match': match, 'reason': str(e)})

        # Flush to get IDs for tiering, but do not commit yet
        self.db.flush()
        
        # Apply tiering
        tiering_failures = self._apply_tiering(stored_matches)

        return {
            'stored_matches': stored_matches,
            'failed_matches': failed_matches,
            'tiering_failures': tiering_failures
        }

    def _apply_tiering(self, matches: List[ForensicMatch]) -> List[Dict[str, Any]]:
        failures = []
        for match in matches:
            try:
                self.tiering_service.classify_and_apply_tiering(
                    match,
                    auto_resolve=True
                )
            except Exception as e:
                logger.error(f"Error applying tiering to match {match.id}: {e}")
                failures.append({'match_id': match.id, 'error': str(e)})
        return failures

    def _get_document_type(self, record_id: int, property_id: int, period_id: int) -> str:
        # Helper logic from original service
        # In a real refactor we might cache this or optimize the query strategy
        # Simplified lookup for now
        
        # Check Balance Sheet
        if self.db.query(BalanceSheetData).filter(BalanceSheetData.id == record_id).first():
            return 'balance_sheet'
        # Check Income Statement
        if self.db.query(IncomeStatementData).filter(IncomeStatementData.id == record_id).first():
            return 'income_statement'
        # Check Cash Flow
        if self.db.query(CashFlowData).filter(CashFlowData.id == record_id).first():
            return 'cash_flow'
        # Check Rent Roll
        if self.db.query(RentRollData).filter(RentRollData.id == record_id).first():
            return 'rent_roll'
        # Check Mortgage Statement
        if self.db.query(MortgageStatementData).filter(MortgageStatementData.id == record_id).first():
            return 'mortgage_statement'
            
        return 'unknown'

    def _get_table_name(self, doc_type: str) -> str:
        mapping = {
            'balance_sheet': 'balance_sheet_data',
            'income_statement': 'income_statement_data',
            'cash_flow': 'cash_flow_data',
            'rent_roll': 'rent_roll_data',
            'mortgage_statement': 'mortgage_statement_data'
        }
        return mapping.get(doc_type, 'unknown')

    def _get_record_details(self, record_id: int, doc_type: str) -> Optional[Dict[str, Any]]:
        model_map = {
            'balance_sheet': BalanceSheetData,
            'income_statement': IncomeStatementData,
            'cash_flow': CashFlowData,
            'rent_roll': RentRollData, 
            'mortgage_statement': MortgageStatementData
        }
        
        model = model_map.get(doc_type)
        if not model:
            return None
            
        record = self.db.query(model).filter(model.id == record_id).first()
        if not record:
            return None
            
        # Map fields based on document type
        if doc_type == 'rent_roll':
            return {
                'account_code': None,
                'account_name': getattr(record, 'tenant_name', 'Unknown Tenant'),
                'amount': getattr(record, 'annual_rent', 0) or getattr(record, 'monthly_rent', 0) * 12,
                'field_name': 'annual_rent'
            }
        elif doc_type == 'mortgage_statement':
            return {
                'account_code': getattr(record, 'loan_number', None),
                'account_name': f"Loan {getattr(record, 'loan_number', 'Unknown')}",
                'amount': getattr(record, 'principal_balance', 0),
                'field_name': 'principal_balance'
            }
        else:
            # Standard financial statements
            return {
                'account_code': getattr(record, 'account_code', None),
                'account_name': getattr(record, 'line_item', None) or getattr(record, 'description', None),
                'amount': getattr(record, 'amount', getattr(record, 'current_period', 0)),
                'field_name': 'amount' if hasattr(record, 'amount') else 'current_period'
            }
