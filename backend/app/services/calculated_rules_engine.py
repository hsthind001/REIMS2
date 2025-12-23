"""
Calculated Rules Engine

Evaluates versioned calculated matching rules and provides detailed explanations.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.calculated_rule import CalculatedRule
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.services.matching_engines import MatchResult

logger = logging.getLogger(__name__)


class CalculatedRulesEngine:
    """Engine for evaluating calculated matching rules"""
    
    def __init__(self, db: Session):
        """
        Initialize calculated rules engine
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_active_rules(
        self,
        property_id: int,
        document_types: Optional[List[str]] = None
    ) -> List[CalculatedRule]:
        """
        Get active calculated rules for a property and document types
        
        Args:
            property_id: Property ID
            document_types: Optional list of document types
            
        Returns:
            List of active CalculatedRule objects
        """
        today = date.today()
        
        query = self.db.query(CalculatedRule).filter(
            and_(
                CalculatedRule.is_active == True,
                CalculatedRule.effective_date <= today,
                or_(
                    CalculatedRule.expires_at.is_(None),
                    CalculatedRule.expires_at >= today
                )
            )
        )
        
        # Filter by property scope
        # TODO: Implement property scope filtering (JSONB query)
        # For now, get all active rules
        
        # Filter by document scope if provided
        if document_types:
            # TODO: Implement document scope filtering (JSONB query)
            pass
        
        # Get latest version of each rule
        rules = query.order_by(
            CalculatedRule.rule_id,
            CalculatedRule.version.desc()
        ).all()
        
        # Deduplicate by rule_id (keep only latest version)
        seen = set()
        unique_rules = []
        for rule in rules:
            if rule.rule_id not in seen:
                seen.add(rule.rule_id)
                unique_rules.append(rule)
        
        return unique_rules
    
    def evaluate_rule(
        self,
        rule: CalculatedRule,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Evaluate a calculated rule for a property and period
        
        Args:
            rule: CalculatedRule to evaluate
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            MatchResult if rule matches, None otherwise
        """
        # Parse formula (simple implementation - can be enhanced)
        # Format: "BS.account_code = IS.account_code" or "BS.account_code = IS.account_code + CF.account_code"
        
        try:
            # Simple formula parser (can be enhanced with proper expression evaluator)
            formula = rule.formula.strip()
            
            # For now, handle simple equality: "BS.account_code = IS.account_code"
            if '=' in formula:
                parts = formula.split('=')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # Parse left side (e.g., "BS.3995-0000")
                    left_parts = left.split('.')
                    if len(left_parts) == 2:
                        left_doc_type = left_parts[0].strip().lower()
                        left_account = left_parts[1].strip()
                        
                        # Parse right side
                        right_parts = right.split('.')
                        if len(right_parts) == 2:
                            right_doc_type = right_parts[0].strip().lower()
                            right_account = right_parts[1].strip()
                            
                            # Get values
                            left_value = self._get_account_value(
                                property_id, period_id, left_doc_type, left_account
                            )
                            right_value = self._get_account_value(
                                property_id, period_id, right_doc_type, right_account
                            )
                            
                            if left_value is not None and right_value is not None:
                                # Calculate difference
                                diff = abs(left_value - right_value)
                                max_val = max(abs(left_value), abs(right_value))
                                diff_percent = float((diff / max_val) * 100) if max_val > 0 else 0.0
                                
                                # Check tolerance
                                tolerance_absolute = rule.tolerance_absolute or Decimal('0.01')
                                tolerance_percent = rule.tolerance_percent or Decimal('1.0')
                                
                                within_tolerance = (
                                    diff <= tolerance_absolute or
                                    diff_percent <= float(tolerance_percent)
                                )
                                
                                # Calculate confidence
                                if within_tolerance:
                                    if diff <= Decimal('0.01'):
                                        confidence = 100.0
                                    elif diff_percent <= 0.1:
                                        confidence = 95.0
                                    elif diff_percent <= 1.0:
                                        confidence = 90.0
                                    else:
                                        confidence = max(70.0, 100.0 - diff_percent)
                                else:
                                    confidence = max(50.0, 100.0 - diff_percent)
                                
                                # Get record IDs (simplified - would need actual record lookup)
                                left_record_id = self._get_record_id(
                                    property_id, period_id, left_doc_type, left_account
                                )
                                right_record_id = self._get_record_id(
                                    property_id, period_id, right_doc_type, right_account
                                )
                                
                                if left_record_id and right_record_id:
                                    return MatchResult(
                                        source_record_id=left_record_id,
                                        target_record_id=right_record_id,
                                        match_type='calculated',
                                        confidence_score=confidence,
                                        amount_difference=diff,
                                        amount_difference_percent=diff_percent,
                                        match_algorithm='calculated_rule',
                                        relationship_type='equality',
                                        relationship_formula=formula
                                    )
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
        
        return None
    
    def explain_failure(
        self,
        rule: CalculatedRule,
        property_id: int,
        period_id: int,
        inputs: Dict[str, Any],
        computed: Decimal,
        expected: Decimal
    ) -> str:
        """
        Generate failure explanation for a rule
        
        Args:
            rule: CalculatedRule that failed
            property_id: Property ID
            period_id: Period ID
            inputs: Input values used in calculation
            computed: Computed value
            expected: Expected value
            
        Returns:
            Failure explanation string
        """
        if rule.failure_explanation_template:
            # Use template with placeholders
            explanation = rule.failure_explanation_template
            explanation = explanation.replace('{computed}', str(computed))
            explanation = explanation.replace('{expected}', str(expected))
            explanation = explanation.replace('{difference}', str(abs(computed - expected)))
            return explanation
        
        # Default explanation
        diff = abs(computed - expected)
        diff_percent = float((diff / max(abs(computed), abs(expected))) * 100) if max(abs(computed), abs(expected)) > 0 else 0.0
        
        return (
            f"Rule '{rule.rule_name}' failed: "
            f"Computed value {computed} does not match expected {expected}. "
            f"Difference: ${diff} ({diff_percent:.2f}%). "
            f"Formula: {rule.formula}"
        )
    
    def _get_account_value(
        self,
        property_id: int,
        period_id: int,
        document_type: str,
        account_code: str
    ) -> Optional[Decimal]:
        """Get account value from database"""
        if document_type == 'bs' or document_type == 'balance_sheet':
            record = self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id,
                    BalanceSheetData.account_code == account_code
                )
            ).first()
            return record.amount if record else None
        
        elif document_type == 'is' or document_type == 'income_statement':
            record = self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id,
                    IncomeStatementData.account_code == account_code
                )
            ).first()
            return record.period_amount if record else None
        
        elif document_type == 'cf' or document_type == 'cash_flow':
            record = self.db.query(CashFlowData).filter(
                and_(
                    CashFlowData.property_id == property_id,
                    CashFlowData.period_id == period_id,
                    CashFlowData.account_code == account_code
                )
            ).first()
            return record.amount if record else None
        
        # Add other document types as needed
        
        return None
    
    def _get_record_id(
        self,
        property_id: int,
        period_id: int,
        document_type: str,
        account_code: str
    ) -> Optional[int]:
        """Get record ID from database"""
        if document_type == 'bs' or document_type == 'balance_sheet':
            record = self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id,
                    BalanceSheetData.account_code == account_code
                )
            ).first()
            return record.id if record else None
        
        elif document_type == 'is' or document_type == 'income_statement':
            record = self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id,
                    IncomeStatementData.account_code == account_code
                )
            ).first()
            return record.id if record else None
        
        elif document_type == 'cf' or document_type == 'cash_flow':
            record = self.db.query(CashFlowData).filter(
                and_(
                    CashFlowData.property_id == property_id,
                    CashFlowData.period_id == period_id,
                    CashFlowData.account_code == account_code
                )
            ).first()
            return record.id if record else None
        
        return None

