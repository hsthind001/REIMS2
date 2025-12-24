"""
Adaptive Matching Service

Dynamically generates matching rules based on discovered account codes.
Uses ML to identify relationships and adapts to different account code schemes.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.services.forensic_matching_rules import ForensicMatchingRules
from app.services.matching_engines import MatchResult
from app.services.account_code_discovery_service import AccountCodeDiscoveryService
from app.models.discovered_account_code import DiscoveredAccountCode
from app.models.account_code_pattern import AccountCodePattern
from app.models.account_code_synonym import AccountCodeSynonym
from app.models.learned_match_pattern import LearnedMatchPattern
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData

logger = logging.getLogger(__name__)


class AdaptiveMatchingService(ForensicMatchingRules):
    """
    Adaptive matching service that extends ForensicMatchingRules
    with dynamic rule generation based on discovered account codes
    """
    
    def __init__(self, db: Session):
        """
        Initialize adaptive matching service
        
        Args:
            db: Database session
        """
        super().__init__(db)
        self.discovery_service = AccountCodeDiscoveryService(db)
    
    def find_all_matches(
        self,
        property_id: int,
        period_id: int,
        prior_period_id: Optional[int] = None
    ) -> List[MatchResult]:
        """
        Execute adaptive matching rules based on discovered account codes
        
        First tries adaptive rules, then falls back to hard-coded rules.
        
        Args:
            property_id: Property ID
            period_id: Current period ID
            prior_period_id: Prior period ID (for reconciliation rules)
            
        Returns:
            List of all MatchResult objects
        """
        logger.info(f"Starting adaptive matching for property {property_id}, period {period_id}")
        
        matches = []
        
        # Step 1: Discover account codes for this property/period
        discovery_results = self.discovery_service.discover_all_account_codes(
            property_id=property_id,
            period_id=period_id
        )
        
        # Step 2: Try adaptive matching rules
        adaptive_matches = self._try_adaptive_rules(
            property_id=property_id,
            period_id=period_id,
            prior_period_id=prior_period_id,
            discovery_results=discovery_results
        )
        matches.extend(adaptive_matches)
        
        # Step 3: Fall back to hard-coded rules for any missing relationships
        hard_coded_matches = super().find_all_matches(
            property_id=property_id,
            period_id=period_id,
            prior_period_id=prior_period_id
        )
        
        # Filter out duplicates (same source and target record IDs)
        existing_pairs = {(m.source_record_id, m.target_record_id) for m in matches}
        for match in hard_coded_matches:
            pair = (match.source_record_id, match.target_record_id)
            if pair not in existing_pairs:
                matches.append(match)
                existing_pairs.add(pair)
        
        logger.info(f"Found {len(matches)} total matches ({len(adaptive_matches)} adaptive, {len(hard_coded_matches)} hard-coded)")
        
        return matches
    
    def _try_adaptive_rules(
        self,
        property_id: int,
        period_id: int,
        prior_period_id: Optional[int],
        discovery_results: Dict[str, Any]
    ) -> List[MatchResult]:
        """Try adaptive matching rules based on discovered codes"""
        matches = []
        
        # Rule 1: Adaptive Current Period Earnings to Net Income
        match = self._adaptive_match_current_period_earnings_to_net_income(
            property_id, period_id, discovery_results
        )
        if match:
            matches.append(match)
        
        # Rule 2: Adaptive Base Rentals to Rent Roll
        match = self._adaptive_match_base_rentals_to_rent_roll(
            property_id, period_id, discovery_results
        )
        if match:
            matches.append(match)
        
        # Rule 3: Adaptive Long-Term Debt to Mortgages
        match = self._adaptive_match_long_term_debt_to_mortgages(
            property_id, period_id, discovery_results
        )
        if match:
            matches.append(match)
        
        # Rule 4: Adaptive Interest Expense
        match = self._adaptive_match_interest_expense(
            property_id, period_id, discovery_results
        )
        if match:
            matches.append(match)
        
        # Rule 5: Adaptive Ending Cash
        match = self._adaptive_match_ending_cash(
            property_id, period_id, discovery_results
        )
        if match:
            matches.append(match)
        
        # Rule 6: Try learned patterns
        learned_matches = self._try_learned_patterns(
            property_id, period_id, discovery_results
        )
        matches.extend(learned_matches)
        
        return matches
    
    def _adaptive_match_current_period_earnings_to_net_income(
        self,
        property_id: int,
        period_id: int,
        discovery_results: Dict[str, Any]
    ) -> Optional[MatchResult]:
        """
        Adaptive version: Find Current Period Earnings and Net Income
        by discovering actual account codes instead of hard-coding
        """
        # Discover balance sheet codes that might be Current Period Earnings
        bs_codes = self.discovery_service.get_discovered_codes(
            document_type='balance_sheet',
            property_id=property_id,
            period_id=period_id
        )
        
        # Look for earnings-related accounts (3995-0000, 3990-0000, or similar)
        earnings_codes = [
            code for code in bs_codes
            if any(keyword in code.account_name.lower() for keyword in [
                'current period earnings', 'earnings', 'retained earnings',
                'net income', 'net earnings'
            ]) or code.account_code.startswith('399')
        ]
        
        # Discover income statement codes that might be Net Income
        is_codes = self.discovery_service.get_discovered_codes(
            document_type='income_statement',
            property_id=property_id,
            period_id=period_id
        )
        
        # Look for net income accounts (9090-0000, 9099-0000, or similar)
        net_income_codes = [
            code for code in is_codes
            if any(keyword in code.account_name.lower() for keyword in [
                'net income', 'net earnings', 'net profit'
            ]) or code.account_code.startswith('909')
        ]
        
        if not earnings_codes or not net_income_codes:
            return None
        
        # Try to match using discovered codes
        for earnings_code in earnings_codes[:1]:  # Try first match
            for net_income_code in net_income_codes[:1]:  # Try first match
                # Get actual records
                bs_earnings = self.db.query(BalanceSheetData).filter(
                    and_(
                        BalanceSheetData.property_id == property_id,
                        BalanceSheetData.period_id == period_id,
                        BalanceSheetData.account_code == earnings_code.account_code
                    )
                ).first()
                
                is_net_income = self.db.query(IncomeStatementData).filter(
                    and_(
                        IncomeStatementData.property_id == property_id,
                        IncomeStatementData.period_id == period_id,
                        IncomeStatementData.account_code == net_income_code.account_code
                    )
                ).first()
                
                if bs_earnings and is_net_income:
                    # Use parent class method logic
                    return self.match_current_period_earnings_to_net_income(property_id, period_id)
        
        return None
    
    def _adaptive_match_base_rentals_to_rent_roll(
        self,
        property_id: int,
        period_id: int,
        discovery_results: Dict[str, Any]
    ) -> Optional[MatchResult]:
        """Adaptive version: Find Base Rentals by discovering actual codes"""
        # Discover income statement codes that might be Base Rentals
        is_codes = self.discovery_service.get_discovered_codes(
            document_type='income_statement',
            property_id=property_id,
            period_id=period_id
        )
        
        # Look for base rentals accounts (4010-0000 or similar)
        base_rentals_codes = [
            code for code in is_codes
            if any(keyword in code.account_name.lower() for keyword in [
                'base rental', 'base rent', 'rental income', 'rent income'
            ]) or code.account_code.startswith('401')
        ]
        
        if not base_rentals_codes:
            return None
        
        # Try to match using discovered code
        for base_rentals_code in base_rentals_codes[:1]:
            is_base_rentals = self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id,
                    IncomeStatementData.account_code == base_rentals_code.account_code
                )
            ).first()
            
            if is_base_rentals:
                # Use parent class method logic
                return self.match_base_rentals_to_rent_roll(property_id, period_id)
        
        return None
    
    def _adaptive_match_long_term_debt_to_mortgages(
        self,
        property_id: int,
        period_id: int,
        discovery_results: Dict[str, Any]
    ) -> Optional[MatchResult]:
        """Adaptive version: Find Long-Term Debt by discovering actual codes"""
        # Discover balance sheet codes that might be Long-Term Debt
        bs_codes = self.discovery_service.get_discovered_codes(
            document_type='balance_sheet',
            property_id=property_id,
            period_id=period_id
        )
        
        # Look for long-term debt accounts (2610-xxxx or similar)
        debt_codes = [
            code for code in bs_codes
            if any(keyword in code.account_name.lower() for keyword in [
                'long term debt', 'mortgage', 'loan', 'notes payable'
            ]) or code.account_code.startswith('261')
        ]
        
        if not debt_codes:
            return None
        
        # Use parent class method logic
        return self.match_long_term_debt_to_mortgages(property_id, period_id)
    
    def _adaptive_match_interest_expense(
        self,
        property_id: int,
        period_id: int,
        discovery_results: Dict[str, Any]
    ) -> Optional[MatchResult]:
        """Adaptive version: Find Interest Expense by discovering actual codes"""
        # Discover income statement codes that might be Interest Expense
        is_codes = self.discovery_service.get_discovered_codes(
            document_type='income_statement',
            property_id=property_id,
            period_id=period_id
        )
        
        # Look for interest expense accounts (6520-xxxx or similar)
        interest_codes = [
            code for code in is_codes
            if any(keyword in code.account_name.lower() for keyword in [
                'interest expense', 'interest', 'loan interest'
            ]) or code.account_code.startswith('652')
        ]
        
        if not interest_codes:
            return None
        
        # Use parent class method logic
        return self.match_interest_expense(property_id, period_id)
    
    def _adaptive_match_ending_cash(
        self,
        property_id: int,
        period_id: int,
        discovery_results: Dict[str, Any]
    ) -> Optional[MatchResult]:
        """Adaptive version: Find Ending Cash by discovering actual codes"""
        # Discover balance sheet codes that might be Cash Operating
        bs_codes = self.discovery_service.get_discovered_codes(
            document_type='balance_sheet',
            property_id=property_id,
            period_id=period_id
        )
        
        # Look for cash accounts (0122-0000 or similar)
        cash_codes = [
            code for code in bs_codes
            if any(keyword in code.account_name.lower() for keyword in [
                'cash', 'operating', 'checking'
            ]) or code.account_code.startswith('012')
        ]
        
        if not cash_codes:
            return None
        
        # Use parent class method logic
        return self.match_ending_cash(property_id, period_id)
    
    def _try_learned_patterns(
        self,
        property_id: int,
        period_id: int,
        discovery_results: Dict[str, Any]
    ) -> List[MatchResult]:
        """Try learned match patterns from previous successful matches"""
        matches = []
        
        # Get active learned patterns
        learned_patterns = self.db.query(LearnedMatchPattern).filter(
            LearnedMatchPattern.is_active == True
        ).order_by(LearnedMatchPattern.priority.desc(), LearnedMatchPattern.success_rate.desc()).limit(20).all()
        
        for pattern in learned_patterns:
            try:
                match = self._apply_learned_pattern(pattern, property_id, period_id)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.error(f"Error applying learned pattern {pattern.id}: {e}")
                continue
        
        return matches
    
    def _apply_learned_pattern(
        self,
        pattern: LearnedMatchPattern,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """Apply a learned match pattern"""
        # Get source record
        source_records = self._get_records_by_pattern(
            pattern.source_document_type,
            pattern.source_account_code,
            pattern.source_account_name,
            property_id,
            period_id
        )
        
        # Get target record
        target_records = self._get_records_by_pattern(
            pattern.target_document_type,
            pattern.target_account_code,
            pattern.target_account_name,
            property_id,
            period_id
        )
        
        if not source_records or not target_records:
            return None
        
        # Try to match based on pattern relationship
        source_record = source_records[0]
        target_record = target_records[0]
        
        # Calculate match based on relationship type
        if pattern.relationship_type == 'equality':
            source_amount = self._get_amount_from_record(source_record, pattern.source_document_type)
            target_amount = self._get_amount_from_record(target_record, pattern.target_document_type)
            
            if source_amount and target_amount:
                amount_diff = abs(source_amount - target_amount)
                max_amount = max(abs(source_amount), abs(target_amount))
                amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
                
                # Use pattern's average confidence as base
                confidence = float(pattern.average_confidence) if pattern.average_confidence else 80.0
                
                # Adjust confidence based on amount difference
                if amount_diff_percent > 1.0:
                    confidence = max(50.0, confidence - amount_diff_percent)
                
                return MatchResult(
                    source_record_id=source_record.id,
                    target_record_id=target_record.id,
                    match_type='learned',
                    confidence_score=confidence,
                    amount_difference=amount_diff,
                    amount_difference_percent=amount_diff_percent,
                    match_algorithm='learned_pattern',
                    relationship_type=pattern.relationship_type,
                    relationship_formula=pattern.relationship_formula
                )
        
        return None
    
    def _get_records_by_pattern(
        self,
        document_type: str,
        account_code: Optional[str],
        account_name: Optional[str],
        property_id: int,
        period_id: int
    ) -> List[Any]:
        """Get records matching a pattern"""
        if document_type == 'balance_sheet':
            query = self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id
                )
            )
            if account_code:
                query = query.filter(BalanceSheetData.account_code == account_code)
            elif account_name:
                query = query.filter(BalanceSheetData.account_name.ilike(f"%{account_name}%"))
            return query.all()
        
        elif document_type == 'income_statement':
            query = self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id
                )
            )
            if account_code:
                query = query.filter(IncomeStatementData.account_code == account_code)
            elif account_name:
                query = query.filter(IncomeStatementData.account_name.ilike(f"%{account_name}%"))
            return query.all()
        
        elif document_type == 'cash_flow':
            query = self.db.query(CashFlowData).filter(
                and_(
                    CashFlowData.property_id == property_id,
                    CashFlowData.period_id == period_id
                )
            )
            if account_code:
                query = query.filter(CashFlowData.account_code == account_code)
            elif account_name:
                query = query.filter(CashFlowData.account_name.ilike(f"%{account_name}%"))
            return query.all()
        
        return []
    
    def _get_amount_from_record(self, record: Any, document_type: str) -> Optional[Decimal]:
        """Get amount from a record based on document type"""
        if document_type == 'balance_sheet':
            return record.amount if hasattr(record, 'amount') else None
        elif document_type in ['income_statement', 'cash_flow']:
            return record.period_amount if hasattr(record, 'period_amount') else None
        return None

