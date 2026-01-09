"""
Calculated Rules Engine

Evaluates versioned calculated matching rules and provides detailed explanations.
"""
import ast
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from app.models.calculated_rule import CalculatedRule
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.property import Property
from app.models.financial_metrics import FinancialMetrics

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
        
        # Filter by property scope (post-query filtering to keep JSONB flexible)
        
        # Filter by document scope if provided
        if document_types:
            document_types = [doc.lower() for doc in document_types]
        
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
        
        # Apply property/document scope filtering
        scoped_rules = []
        for rule in unique_rules:
            if not self._rule_applies_to_property(rule, property_id):
                continue
            if document_types and not self._rule_applies_to_documents(rule, document_types):
                continue
            scoped_rules.append(rule)

        return scoped_rules
    
    def evaluate_rule(
        self,
        rule: CalculatedRule,
        property_id: int,
        period_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a calculated rule for a property and period
        
        Args:
            rule: CalculatedRule to evaluate
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            MatchResult if rule matches, None otherwise
        """
        try:
            formula = rule.formula.strip()
            if '=' not in formula:
                return self._build_skipped_result(rule, "Unsupported formula (missing '=')")

            left_expr, right_expr = [part.strip() for part in formula.split('=', 1)]

            cache: Dict[str, Any] = {}
            left_value = self._evaluate_expression(left_expr, property_id, period_id, cache)
            right_value = self._evaluate_expression(right_expr, property_id, period_id, cache)

            if left_value is None or right_value is None:
                return self._build_skipped_result(rule, "Missing data for rule inputs")

            diff = abs(left_value - right_value)
            max_val = max(abs(left_value), abs(right_value))
            diff_percent = float((diff / max_val) * 100) if max_val > 0 else 0.0

            tolerance_absolute = rule.tolerance_absolute if rule.tolerance_absolute is not None else Decimal('0.01')
            tolerance_percent = rule.tolerance_percent if rule.tolerance_percent is not None else Decimal('1.0')

            within_tolerance = (
                diff <= tolerance_absolute or
                diff_percent <= float(tolerance_percent)
            )

            status = 'PASS' if within_tolerance else 'FAIL'

            message = None
            if status == 'FAIL':
                message = self.explain_failure(
                    rule=rule,
                    property_id=property_id,
                    period_id=period_id,
                    inputs={'left': left_value, 'right': right_value},
                    computed=right_value,
                    expected=left_value
                )

            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'description': rule.description,
                'formula': rule.formula,
                'severity': rule.severity,
                'status': status,
                'expected_value': float(left_value),
                'actual_value': float(right_value),
                'difference': float(diff),
                'difference_percent': diff_percent,
                'tolerance_absolute': float(tolerance_absolute) if tolerance_absolute is not None else None,
                'tolerance_percent': float(tolerance_percent) if tolerance_percent is not None else None,
                'message': message
            }
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return self._build_skipped_result(rule, f"Evaluation error: {e}")
    
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

    def evaluate_rules(
        self,
        property_id: int,
        period_id: int,
        document_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate all active calculated rules for a property/period."""
        rules = self.get_active_rules(property_id, document_types)
        results = []
        for rule in rules:
            result = self.evaluate_rule(rule, property_id, period_id)
            if result:
                results.append(result)
        return results

    def _evaluate_expression(
        self,
        expression: str,
        property_id: int,
        period_id: int,
        cache: Dict[str, Any]
    ) -> Optional[Decimal]:
        """Evaluate an expression with document tokens replaced by values."""
        token_pattern = re.compile(r'([A-Za-z]+)\.([A-Za-z0-9_\-]+)')
        tokens = token_pattern.findall(expression)

        unique_tokens: Dict[str, Tuple[str, str]] = {}
        for prefix, token in tokens:
            key = f"{prefix}.{token}"
            if key not in unique_tokens:
                unique_tokens[key] = (prefix, token)

        placeholders: Dict[str, Decimal] = {}
        expr_with_placeholders = expression

        for idx, (key, (prefix, token)) in enumerate(unique_tokens.items()):
            value = self._get_token_value(prefix, token, property_id, period_id, cache)
            if value is None:
                return None
            placeholder = f"__VAL{idx}__"
            expr_with_placeholders = expr_with_placeholders.replace(key, placeholder)
            placeholders[placeholder] = value

        for placeholder, value in placeholders.items():
            expr_with_placeholders = expr_with_placeholders.replace(placeholder, str(value))

        return self._safe_eval(expr_with_placeholders)

    def _safe_eval(self, expression: str) -> Optional[Decimal]:
        """Safely evaluate arithmetic expressions."""
        try:
            node = ast.parse(expression, mode='eval')
        except SyntaxError:
            return None

        def _eval(node: ast.AST) -> Decimal:
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Constant):
                return Decimal(str(node.value))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = _eval(node.operand)
                return value if isinstance(node.op, ast.UAdd) else -value
            if isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    if right == 0:
                        raise ValueError("Division by zero")
                    return left / right
                if isinstance(node.op, ast.Mod):
                    return left % right
                if isinstance(node.op, ast.Pow):
                    return left ** right
            raise ValueError("Unsupported expression")

        try:
            return _eval(node)
        except Exception:
            return None

    def _get_token_value(
        self,
        prefix: str,
        token: str,
        property_id: int,
        period_id: int,
        cache: Dict[str, Any]
    ) -> Optional[Decimal]:
        """Resolve a token value for evaluation."""
        prefix = prefix.lower()

        if prefix in ('bs', 'balance_sheet'):
            return self._get_account_value(property_id, period_id, 'balance_sheet', token)

        if prefix in ('is', 'income_statement'):
            return self._get_account_value(property_id, period_id, 'income_statement', token)

        if prefix in ('cf', 'cash_flow'):
            return self._get_account_value(property_id, period_id, 'cash_flow', token)

        if prefix in ('rr', 'rent_roll'):
            return self._get_rent_roll_value(property_id, period_id, token, cache)

        if prefix in ('mst', 'mortgage', 'mortgage_statement'):
            return self._get_mortgage_value(property_id, period_id, token, cache)

        if prefix in ('metrics', 'metric'):
            return self._get_metrics_value(property_id, period_id, token, cache)

        if prefix in ('view', 'recon'):
            return self._get_view_value(property_id, period_id, token, cache)

        return None

    def _get_rent_roll_value(
        self,
        property_id: int,
        period_id: int,
        token: str,
        cache: Dict[str, Any]
    ) -> Optional[Decimal]:
        if 'rent_roll_summary' not in cache:
            total_units = self.db.query(func.count(RentRollData.id)).filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            ).scalar() or 0
            occupied_units = self.db.query(func.count(RentRollData.id)).filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id,
                RentRollData.occupancy_status == 'occupied'
            ).scalar() or 0
            total_monthly_rent = self.db.query(func.sum(RentRollData.monthly_rent)).filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            ).scalar() or Decimal('0')
            total_annual_rent = self.db.query(func.sum(RentRollData.annual_rent)).filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            ).scalar()
            if total_annual_rent is None:
                total_annual_rent = total_monthly_rent * Decimal('12')
            occupancy_rate = Decimal('0')
            if total_units > 0:
                occupancy_rate = (Decimal(str(occupied_units)) / Decimal(str(total_units))) * Decimal('100')

            cache['rent_roll_summary'] = {
                'total_units': Decimal(str(total_units)),
                'occupied_units': Decimal(str(occupied_units)),
                'total_monthly_rent': total_monthly_rent,
                'total_annual_rent': total_annual_rent,
                'occupancy_rate': occupancy_rate
            }

        summary = cache['rent_roll_summary']
        return summary.get(token)

    def _get_mortgage_value(
        self,
        property_id: int,
        period_id: int,
        token: str,
        cache: Dict[str, Any]
    ) -> Optional[Decimal]:
        if 'mortgage_summary' not in cache:
            mortgages = self.db.query(MortgageStatementData).filter(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period_id
            ).all()

            if not mortgages:
                cache['mortgage_summary'] = {}
            else:
                def _sum(field_name: str) -> Decimal:
                    return sum([
                        getattr(m, field_name) or Decimal('0')
                        for m in mortgages
                    ], Decimal('0'))

                cache['mortgage_summary'] = {
                    'principal_balance': _sum('principal_balance'),
                    'interest_due': _sum('interest_due'),
                    'principal_due': _sum('principal_due'),
                    'tax_escrow_due': _sum('tax_escrow_due'),
                    'insurance_escrow_due': _sum('insurance_escrow_due'),
                    'reserve_due': _sum('reserve_due'),
                    'total_payment_due': _sum('total_payment_due'),
                    'tax_escrow_balance': _sum('tax_escrow_balance'),
                    'insurance_escrow_balance': _sum('insurance_escrow_balance'),
                    'reserve_balance': _sum('reserve_balance'),
                    'ytd_principal_paid': _sum('ytd_principal_paid'),
                    'ytd_interest_paid': _sum('ytd_interest_paid'),
                    'interest_rate': sum([
                        getattr(m, 'interest_rate') or Decimal('0')
                        for m in mortgages
                    ], Decimal('0')) / Decimal(str(len(mortgages)))
                }

        return cache['mortgage_summary'].get(token)

    def _get_metrics_value(
        self,
        property_id: int,
        period_id: int,
        token: str,
        cache: Dict[str, Any]
    ) -> Optional[Decimal]:
        if 'metrics' not in cache:
            cache['metrics'] = self.db.query(FinancialMetrics).filter(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id == period_id
            ).first()

        metrics = cache['metrics']
        if not metrics:
            return None

        if hasattr(metrics, token):
            value = getattr(metrics, token)
            return Decimal(str(value)) if value is not None else None
        return None

    def _get_view_value(
        self,
        property_id: int,
        period_id: int,
        token: str,
        cache: Dict[str, Any]
    ) -> Optional[Decimal]:
        if 'recon_view' not in cache:
            try:
                result = self.db.execute(
                    text("""
                        SELECT * FROM forensic_reconciliation_master
                        WHERE property_id = :property_id AND period_id = :period_id
                    """),
                    {'property_id': property_id, 'period_id': period_id}
                ).fetchone()
                cache['recon_view'] = result._mapping if result else None
            except Exception as exc:
                logger.warning(f"Failed to query forensic_reconciliation_master: {exc}")
                cache['recon_view'] = None

        view_row = cache.get('recon_view')
        if not view_row:
            return None

        value = view_row.get(token)
        return Decimal(str(value)) if value is not None else None

    def _rule_applies_to_property(self, rule: CalculatedRule, property_id: int) -> bool:
        if not rule.property_scope:
            return True

        scope = rule.property_scope
        if isinstance(scope, dict):
            if scope.get('all') is True:
                return True

            if 'property_ids' in scope:
                return property_id in scope.get('property_ids', [])

            if 'property_codes' in scope:
                codes = scope.get('property_codes', [])
                if not codes:
                    return False
                count = self.db.query(Property).filter(
                    Property.id == property_id,
                    Property.property_code.in_(codes)
                ).count()
                return count > 0

        if isinstance(scope, list):
            return property_id in scope

        return False

    def _rule_applies_to_documents(self, rule: CalculatedRule, document_types: List[str]) -> bool:
        if not rule.doc_scope:
            return True
        try:
            rule_docs = [doc.lower() for doc in rule.doc_scope]
            return any(doc in document_types for doc in rule_docs)
        except Exception:
            return True

    def _build_skipped_result(self, rule: CalculatedRule, message: str) -> Dict[str, Any]:
        return {
            'rule_id': rule.rule_id,
            'rule_name': rule.rule_name,
            'description': rule.description,
            'formula': rule.formula,
            'severity': rule.severity,
            'status': 'SKIPPED',
            'expected_value': None,
            'actual_value': None,
            'difference': None,
            'difference_percent': None,
            'tolerance_absolute': float(rule.tolerance_absolute) if rule.tolerance_absolute is not None else None,
            'tolerance_percent': float(rule.tolerance_percent) if rule.tolerance_percent is not None else None,
            'message': message
        }
    
    def _get_account_value(
        self,
        property_id: int,
        period_id: int,
        document_type: str,
        account_code: str
    ) -> Optional[Decimal]:
        """Get account value from database"""
        if document_type == 'bs' or document_type == 'balance_sheet':
            return self.db.query(func.sum(BalanceSheetData.amount)).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id,
                    BalanceSheetData.account_code == account_code
                )
            ).scalar()
        
        elif document_type == 'is' or document_type == 'income_statement':
            return self.db.query(func.sum(IncomeStatementData.period_amount)).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id,
                    IncomeStatementData.account_code == account_code
                )
            ).scalar()
        
        elif document_type == 'cf' or document_type == 'cash_flow':
            return self.db.query(func.sum(CashFlowData.period_amount)).filter(
                and_(
                    CashFlowData.property_id == property_id,
                    CashFlowData.period_id == period_id,
                    CashFlowData.account_code == account_code
                )
            ).scalar()
        
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
