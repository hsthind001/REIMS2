"""
Business logic validation framework for financial data
"""
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models.validation_rule import ValidationRule
from app.models.validation_result import ValidationResult
from decimal import Decimal
import ast
import operator

# Safe operators for expression evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}


def safe_eval(expression: str) -> any:
    """
    Safely evaluate a mathematical or logical expression.
    Only allows basic arithmetic and comparison operations.
    """
    try:
        tree = ast.parse(expression, mode='eval')
        return _eval_node(tree.body)
    except Exception:
        return None


def _eval_node(node):
    """Recursively evaluate an AST node"""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Num):  # Python 3.7 compatibility
        return node.n
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op = SAFE_OPERATORS.get(type(node.op))
        if op:
            return op(left, right)
        raise ValueError(f"Unsupported operator: {type(node.op)}")
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op = SAFE_OPERATORS.get(type(node.op))
        if op:
            return op(operand)
        raise ValueError(f"Unsupported unary operator: {type(node.op)}")
    elif isinstance(node, ast.Compare):
        left = _eval_node(node.left)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator)
            op_func = SAFE_OPERATORS.get(type(op))
            if op_func:
                result = result and op_func(left, right)
                left = right
            else:
                raise ValueError(f"Unsupported comparison: {type(op)}")
        return result
    elif isinstance(node, ast.BoolOp):
        values = [_eval_node(v) for v in node.values]
        op = SAFE_OPERATORS.get(type(node.op))
        if op:
            result = values[0]
            for v in values[1:]:
                result = op(result, v)
            return result
        raise ValueError(f"Unsupported boolean operator: {type(node.op)}")
    elif isinstance(node, ast.Name):
        # Variable names should already be substituted
        raise ValueError(f"Unknown variable: {node.id}")
    else:
        raise ValueError(f"Unsupported expression type: {type(node)}")


class BusinessValidator:
    """Validates financial data against business rules"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_financial_data(
        self,
        upload_id: int,
        document_type: str,
        financial_data: Dict
    ) -> Dict:
        """
        Validate financial data against business rules
        
        Args:
            upload_id: Document upload ID
            document_type: Type of financial document
            financial_data: Extracted financial data
        
        Returns:
            dict: Validation results
        """
        # Load active rules for this document type
        rules = self.db.query(ValidationRule).filter(
            ValidationRule.document_type == document_type,
            ValidationRule.is_active == True
        ).all()
        
        results = []
        passed_count = 0
        failed_count = 0
        
        for rule in rules:
            result = self._execute_rule(rule, financial_data)
            
            # Store in database
            val_result = ValidationResult(
                upload_id=upload_id,
                rule_id=rule.id,
                passed=result["passed"],
                expected_value=result.get("expected_value"),
                actual_value=result.get("actual_value"),
                difference=result.get("difference"),
                difference_percentage=result.get("difference_percentage"),
                error_message=result.get("error_message"),
                severity=rule.severity
            )
            self.db.add(val_result)
            
            results.append(result)
            
            if result["passed"]:
                passed_count += 1
            else:
                failed_count += 1
        
        self.db.commit()
        
        return {
            "total_rules": len(rules),
            "passed": passed_count,
            "failed": failed_count,
            "results": results,
            "overall_status": "passed" if failed_count == 0 else "failed",
            "success": True
        }
    
    def _execute_rule(self, rule: ValidationRule, data: Dict) -> Dict:
        """Execute a single validation rule"""
        
        try:
            if rule.rule_type == "balance_check":
                return self._check_balance(rule, data)
            elif rule.rule_type == "range_check":
                return self._check_range(rule, data)
            elif rule.rule_type == "required_field":
                return self._check_required(rule, data)
            else:
                return {
                    "rule_name": rule.rule_name,
                    "passed": True,
                    "message": f"Unknown rule type: {rule.rule_type}"
                }
        
        except Exception as e:
            return {
                "rule_name": rule.rule_name,
                "passed": False,
                "error_message": f"Rule execution error: {str(e)}"
            }
    
    def _check_balance(self, rule: ValidationRule, data: Dict) -> Dict:
        """Check balance equations (e.g., Assets = Liabilities + Equity)"""
        
        # Parse formula: "total_assets = total_liabilities + total_equity"
        if '=' in rule.rule_formula:
            left, right = rule.rule_formula.split('=')
            
            left_value = self._evaluate_expression(left.strip(), data)
            right_value = self._evaluate_expression(right.strip(), data)
            
            # Allow 0.01 tolerance for rounding
            difference = abs(left_value - right_value)
            passed = difference < 0.01
            
            return {
                "rule_name": rule.rule_name,
                "passed": passed,
                "expected_value": float(right_value),
                "actual_value": float(left_value),
                "difference": float(difference),
                "difference_percentage": float((difference / max(abs(right_value), 0.01)) * 100),
                "error_message": rule.error_message if not passed else None
            }
        
        return {"rule_name": rule.rule_name, "passed": True}
    
    def _check_range(self, rule: ValidationRule, data: Dict) -> Dict:
        """Check if value is within acceptable range"""
        
        # Simple range check parsing
        # Example: "occupancy_rate >= 0 AND occupancy_rate <= 100"
        passed = True
        
        try:
            # Substitute values into formula
            formula_with_values = rule.rule_formula
            for key, value in data.items():
                formula_with_values = formula_with_values.replace(key, str(value))

            # Convert AND/OR to Python syntax for parsing
            formula_with_values = formula_with_values.replace(' AND ', ' and ').replace(' OR ', ' or ')

            # Safe evaluation
            result = safe_eval(formula_with_values)
            passed = bool(result) if result is not None else False
        except:
            passed = False
        
        return {
            "rule_name": rule.rule_name,
            "passed": passed,
            "error_message": rule.error_message if not passed else None
        }
    
    def _check_required(self, rule: ValidationRule, data: Dict) -> Dict:
        """Check if required fields are present"""
        
        # Parse required fields from formula
        required_fields = rule.rule_formula.split(',')
        
        missing_fields = []
        for field in required_fields:
            field = field.strip()
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        passed = len(missing_fields) == 0
        
        return {
            "rule_name": rule.rule_name,
            "passed": passed,
            "error_message": f"Missing required fields: {', '.join(missing_fields)}" if not passed else None
        }
    
    def _evaluate_expression(self, expression: str, data: Dict) -> Decimal:
        """Evaluate a simple arithmetic expression with variable substitution"""
        
        # Replace variables with values
        for key, value in data.items():
            if key in expression:
                expression = expression.replace(key, str(value))

        # Safe evaluation
        try:
            result = safe_eval(expression)
            if result is not None:
                return Decimal(str(result))
            return Decimal('0')
        except:
            return Decimal('0')

