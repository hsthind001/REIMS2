"""
Business logic validation framework for financial data
"""
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models.validation_rule import ValidationRule
from app.models.validation_result import ValidationResult
from decimal import Decimal


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
            # Basic evaluation (in production, use safer evaluation)
            formula_with_values = rule.rule_formula
            for key, value in data.items():
                formula_with_values = formula_with_values.replace(key, str(value))
            
            # Evaluate (simplified - in production use safer method)
            passed = eval(formula_with_values)
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
        
        # Evaluate (simplified - in production use safer evaluation)
        try:
            result = eval(expression)
            return Decimal(str(result))
        except:
            return Decimal('0')

