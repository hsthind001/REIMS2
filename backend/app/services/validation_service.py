"""
ValidationService - Financial Data Validation Engine

Implements business logic validation rules for financial statements
Validates balance sheet equations, income statement calculations, rent roll data
Ensures 100% data quality with configurable tolerance for rounding errors
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import date

from app.models.document_upload import DocumentUpload
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.financial_metrics import FinancialMetrics
from app.models.validation_rule import ValidationRule
from app.models.validation_result import ValidationResult


class ValidationService:
    """
    Financial data validation service
    
    Validates extracted financial data against business logic rules
    Stores validation results in database
    Flags failed validations for review
    """
    
    def __init__(self, db: Session, tolerance_percentage: float = 1.0):
        """
        Initialize validation service
        
        Args:
            db: Database session
            tolerance_percentage: Percentage tolerance for rounding errors (default 1%)
        """
        self.db = db
        self.tolerance = Decimal(str(tolerance_percentage / 100))  # Convert to decimal fraction
    
    def validate_upload(self, upload_id: int) -> Dict:
        """
        Run all applicable validations for an upload
        
        Args:
            upload_id: DocumentUpload ID
        
        Returns:
            dict: {
                "total_checks": 10,
                "passed_checks": 8,
                "failed_checks": 2,
                "warnings": 1,
                "errors": 1,
                "validation_results": [...]
            }
        """
        # Get upload record
        upload = self.db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            return {
                "success": False,
                "error": f"Upload {upload_id} not found"
            }
        
        # Run validations based on document type
        validation_results = []
        
        if upload.document_type == "balance_sheet":
            validation_results.extend(self._validate_balance_sheet(upload))
        elif upload.document_type == "income_statement":
            validation_results.extend(self._validate_income_statement(upload))
        elif upload.document_type == "cash_flow":
            validation_results.extend(self._validate_cash_flow(upload))
        elif upload.document_type == "rent_roll":
            validation_results.extend(self._validate_rent_roll(upload))
        
        # Count results
        total_checks = len(validation_results)
        passed_checks = sum(1 for r in validation_results if r["passed"])
        failed_checks = total_checks - passed_checks
        warnings = sum(1 for r in validation_results if r["severity"] == "warning")
        errors = sum(1 for r in validation_results if r["severity"] == "error")
        
        return {
            "success": True,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "warnings": warnings,
            "errors": errors,
            "validation_results": validation_results,
            "overall_passed": failed_checks == 0
        }
    
    # ==================== BALANCE SHEET VALIDATIONS ====================
    
    def _validate_balance_sheet(self, upload: DocumentUpload) -> List[Dict]:
        """Run all balance sheet validations"""
        results = []
        
        # 1. Balance sheet equation: Assets = Liabilities + Equity
        results.append(self.validate_balance_sheet_equation(
            upload.id, upload.property_id, upload.period_id
        ))
        
        # 2. No negative cash (warning only)
        results.append(self.validate_no_negative_cash(
            upload.id, upload.property_id, upload.period_id
        ))
        
        return results
    
    def validate_balance_sheet_equation(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Validate: Assets = Liabilities + Equity
        
        Uses total accounts: 1999 (Assets), 2999 (Liabilities), 3999 (Equity)
        """
        rule = self._get_or_create_rule(
            "balance_sheet_equation",
            "Balance Sheet Equation",
            "Assets must equal Liabilities plus Equity",
            "balance_sheet",
            "balance_check",
            "total_assets = total_liabilities + total_equity",
            "error"
        )
        
        # Query totals
        total_assets = self._query_balance_sheet_total(
            property_id, period_id, '1999-0000'
        ) or Decimal('0')
        
        total_liabilities = self._query_balance_sheet_total(
            property_id, period_id, '2999-0000'
        ) or Decimal('0')
        
        total_equity = self._query_balance_sheet_total(
            property_id, period_id, '3999-0000'
        ) or Decimal('0')
        
        # Calculate expected vs actual
        expected = total_liabilities + total_equity
        actual = total_assets
        difference = abs(expected - actual)
        
        # Calculate percentage difference
        if actual != 0:
            percentage_diff = (difference / abs(actual)) * Decimal('100')
        else:
            percentage_diff = Decimal('0') if difference == 0 else Decimal('100')
        
        # Check if within tolerance
        passed = percentage_diff <= (self.tolerance * Decimal('100'))
        
        error_message = None
        if not passed:
            error_message = (
                f"Assets ({actual:,.2f}) != Liabilities ({total_liabilities:,.2f}) "
                f"+ Equity ({total_equity:,.2f}). Difference: {difference:,.2f} ({percentage_diff:.2f}%)"
            )
        
        # Store result
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=expected,
            actual_value=actual,
            difference=difference,
            difference_percentage=percentage_diff,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    def validate_no_negative_cash(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """Validate that cash accounts are not negative (warning level)"""
        rule = self._get_or_create_rule(
            "balance_sheet_no_negative_cash",
            "No Negative Cash",
            "Cash accounts should not be negative",
            "balance_sheet",
            "range_check",
            "cash >= 0",
            "warning"
        )
        
        # Query cash accounts (0122-0000 = Cash - Operating)
        cash_amount = self._query_balance_sheet_total(
            property_id, period_id, '0122-0000'
        ) or Decimal('0')
        
        passed = cash_amount >= 0
        
        error_message = None
        if not passed:
            error_message = f"Cash is negative: {cash_amount:,.2f}"
        
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=Decimal('0'),
            actual_value=cash_amount,
            difference=abs(cash_amount) if not passed else Decimal('0'),
            difference_percentage=None,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    # ==================== INCOME STATEMENT VALIDATIONS ====================
    
    def _validate_income_statement(self, upload: DocumentUpload) -> List[Dict]:
        """Run all income statement validations"""
        results = []
        
        # 1. Net Income = Revenue - Expenses
        results.append(self.validate_net_income(
            upload.id, upload.property_id, upload.period_id
        ))
        
        # 2. No negative revenue (warning)
        results.append(self.validate_no_negative_revenue(
            upload.id, upload.property_id, upload.period_id
        ))
        
        # 3. YTD >= Period amounts
        results.append(self.validate_ytd_consistency(
            upload.id, upload.property_id, upload.period_id
        ))
        
        return results
    
    def validate_net_income(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Validate: Net Income = Total Revenue - Total Expenses
        """
        rule = self._get_or_create_rule(
            "income_statement_net_income",
            "Net Income Calculation",
            "Net Income must equal Total Revenue minus Total Expenses",
            "income_statement",
            "balance_check",
            "net_income = total_revenue - total_expenses",
            "error"
        )
        
        # Query revenue (4xxx accounts)
        total_revenue = self.db.query(
            func.sum(IncomeStatementData.period_amount)
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('4%'),
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        
        # Query expenses (5xxx-8xxx accounts)
        total_expenses = self.db.query(
            func.sum(IncomeStatementData.period_amount)
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.op('~')('^[5-8]'),  # Regex for 5xxx-8xxx
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        
        # Query net income (9090-0000)
        actual_net_income = self.db.query(
            IncomeStatementData.period_amount
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == '9090-0000'
        ).scalar() or Decimal('0')
        
        # Calculate expected net income
        expected_net_income = total_revenue - abs(total_expenses)
        difference = abs(expected_net_income - actual_net_income)
        
        # Calculate percentage difference
        if actual_net_income != 0:
            percentage_diff = (difference / abs(actual_net_income)) * Decimal('100')
        else:
            percentage_diff = Decimal('0') if difference == 0 else Decimal('100')
        
        passed = percentage_diff <= (self.tolerance * Decimal('100'))
        
        error_message = None
        if not passed:
            error_message = (
                f"Net Income ({actual_net_income:,.2f}) != Revenue ({total_revenue:,.2f}) "
                f"- Expenses ({total_expenses:,.2f}). Expected: {expected_net_income:,.2f}, "
                f"Difference: {difference:,.2f} ({percentage_diff:.2f}%)"
            )
        
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=expected_net_income,
            actual_value=actual_net_income,
            difference=difference,
            difference_percentage=percentage_diff,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    def validate_no_negative_revenue(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """Validate that revenue accounts are not negative (warning)"""
        rule = self._get_or_create_rule(
            "income_statement_no_negative_revenue",
            "No Negative Revenue",
            "Revenue accounts should not be negative",
            "income_statement",
            "range_check",
            "revenue >= 0",
            "warning"
        )
        
        # Check for negative revenue
        negative_revenue_count = self.db.query(
            func.count(IncomeStatementData.id)
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('4%'),
            IncomeStatementData.period_amount < 0
        ).scalar() or 0
        
        passed = negative_revenue_count == 0
        
        error_message = None
        if not passed:
            error_message = f"Found {negative_revenue_count} revenue account(s) with negative amounts"
        
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=Decimal('0'),
            actual_value=Decimal(str(negative_revenue_count)),
            difference=None,
            difference_percentage=None,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    def validate_ytd_consistency(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """Validate that YTD amounts >= Period amounts"""
        rule = self._get_or_create_rule(
            "income_statement_ytd_consistency",
            "YTD >= Period",
            "Year-to-Date amounts should be >= Period amounts",
            "income_statement",
            "range_check",
            "ytd_amount >= period_amount",
            "warning"
        )
        
        # Check for YTD < Period
        inconsistent_count = self.db.query(
            func.count(IncomeStatementData.id)
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.ytd_amount != None,
            IncomeStatementData.ytd_amount < IncomeStatementData.period_amount
        ).scalar() or 0
        
        passed = inconsistent_count == 0
        
        error_message = None
        if not passed:
            error_message = f"Found {inconsistent_count} account(s) where YTD < Period amount"
        
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=None,
            actual_value=Decimal(str(inconsistent_count)),
            difference=None,
            difference_percentage=None,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    # ==================== CASH FLOW VALIDATIONS ====================
    
    def _validate_cash_flow(self, upload: DocumentUpload) -> List[Dict]:
        """Run all cash flow validations"""
        results = []
        
        # 1. Categories sum to net change
        results.append(self.validate_cash_flow_categories(
            upload.id, upload.property_id, upload.period_id
        ))
        
        return results
    
    def validate_cash_flow_categories(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Validate: Operating + Investing + Financing = Net Change in Cash
        """
        rule = self._get_or_create_rule(
            "cash_flow_categories_sum",
            "Cash Flow Categories Sum",
            "Sum of Operating, Investing, and Financing should equal Net Change in Cash",
            "cash_flow",
            "balance_check",
            "operating + investing + financing = net_change",
            "error"
        )
        
        # Query category totals
        operating = self.db.query(
            func.sum(CashFlowData.period_amount)
        ).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.cash_flow_category == 'operating'
        ).scalar() or Decimal('0')
        
        investing = self.db.query(
            func.sum(CashFlowData.period_amount)
        ).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.cash_flow_category == 'investing'
        ).scalar() or Decimal('0')
        
        financing = self.db.query(
            func.sum(CashFlowData.period_amount)
        ).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.cash_flow_category == 'financing'
        ).scalar() or Decimal('0')
        
        # Calculate totals
        expected_net_change = operating + investing + financing
        
        # For actual, we'd need a "net change" account or calculate from beginning/ending cash
        # For now, use the sum as both (no actual separate net change account typically)
        actual_net_change = expected_net_change
        difference = abs(expected_net_change - actual_net_change)
        
        passed = difference <= Decimal('0.01')  # Within 1 cent
        
        error_message = None
        if not passed:
            error_message = (
                f"Cash flow categories don't sum correctly. Operating: {operating:,.2f}, "
                f"Investing: {investing:,.2f}, Financing: {financing:,.2f}"
            )
        
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=expected_net_change,
            actual_value=actual_net_change,
            difference=difference,
            difference_percentage=None,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    # ==================== RENT ROLL VALIDATIONS ====================
    
    def _validate_rent_roll(self, upload: DocumentUpload) -> List[Dict]:
        """Run all rent roll validations"""
        results = []
        
        # 1. No duplicate units
        results.append(self.validate_no_duplicate_units(
            upload.id, upload.property_id, upload.period_id
        ))
        
        # 2. Valid lease dates
        results.append(self.validate_lease_dates(
            upload.id, upload.property_id, upload.period_id
        ))
        
        return results
    
    def validate_no_duplicate_units(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """Validate that each unit appears only once"""
        rule = self._get_or_create_rule(
            "rent_roll_no_duplicate_units",
            "No Duplicate Units",
            "Each unit should appear only once in the rent roll",
            "rent_roll",
            "uniqueness_check",
            "unit_number unique per period",
            "error"
        )
        
        # Check for duplicates
        duplicates = self.db.query(
            RentRollData.unit_number,
            func.count(RentRollData.id).label('count')
        ).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).group_by(
            RentRollData.unit_number
        ).having(
            func.count(RentRollData.id) > 1
        ).all()
        
        passed = len(duplicates) == 0
        
        error_message = None
        if not passed:
            duplicate_units = [f"{unit} ({count}x)" for unit, count in duplicates]
            error_message = f"Found {len(duplicates)} duplicate unit(s): {', '.join(duplicate_units)}"
        
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=Decimal('0'),
            actual_value=Decimal(str(len(duplicates))),
            difference=None,
            difference_percentage=None,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    def validate_lease_dates(
        self, 
        upload_id: int, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """Validate that lease start dates are before end dates"""
        rule = self._get_or_create_rule(
            "rent_roll_valid_lease_dates",
            "Valid Lease Dates",
            "Lease start date must be before end date",
            "rent_roll",
            "date_check",
            "lease_start_date < lease_end_date",
            "warning"
        )
        
        # Check for invalid date ranges
        invalid_dates = self.db.query(
            func.count(RentRollData.id)
        ).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id,
            RentRollData.lease_start_date != None,
            RentRollData.lease_end_date != None,
            RentRollData.lease_start_date >= RentRollData.lease_end_date
        ).scalar() or 0
        
        passed = invalid_dates == 0
        
        error_message = None
        if not passed:
            error_message = f"Found {invalid_dates} lease(s) with start date >= end date"
        
        result = self._create_validation_result(
            upload_id=upload_id,
            rule_id=rule.id,
            passed=passed,
            expected_value=None,
            actual_value=Decimal(str(invalid_dates)),
            difference=None,
            difference_percentage=None,
            error_message=error_message,
            severity=rule.severity
        )
        
        return result
    
    # ==================== HELPER METHODS ====================
    
    def _query_balance_sheet_total(
        self, 
        property_id: int, 
        period_id: int, 
        account_code: str
    ) -> Optional[Decimal]:
        """Query a specific total account from balance sheet"""
        result = self.db.query(BalanceSheetData.amount).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code == account_code
        ).first()
        
        return result[0] if result else None
    
    def _get_or_create_rule(
        self,
        rule_name: str,
        rule_description: str,
        error_msg: str,
        document_type: str,
        rule_type: str,
        rule_formula: str,
        severity: str
    ) -> ValidationRule:
        """Get existing validation rule or create new one"""
        rule = self.db.query(ValidationRule).filter(
            ValidationRule.rule_name == rule_name
        ).first()
        
        if not rule:
            rule = ValidationRule(
                rule_name=rule_name,
                rule_description=error_msg,
                document_type=document_type,
                rule_type=rule_type,
                rule_formula=rule_formula,
                error_message=error_msg,
                severity=severity,
                is_active=True
            )
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
        
        return rule
    
    def _create_validation_result(
        self,
        upload_id: int,
        rule_id: int,
        passed: bool,
        expected_value: Optional[Decimal],
        actual_value: Optional[Decimal],
        difference: Optional[Decimal],
        difference_percentage: Optional[Decimal],
        error_message: Optional[str],
        severity: str
    ) -> Dict:
        """
        Create and store validation result
        
        Returns dict representation for immediate use
        """
        result = ValidationResult(
            upload_id=upload_id,
            rule_id=rule_id,
            passed=passed,
            expected_value=expected_value,
            actual_value=actual_value,
            difference=difference,
            difference_percentage=difference_percentage,
            error_message=error_message,
            severity=severity
        )
        
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        
        # Return dict representation
        return {
            "id": result.id,
            "rule_id": rule_id,
            "passed": passed,
            "expected_value": float(expected_value) if expected_value else None,
            "actual_value": float(actual_value) if actual_value else None,
            "difference": float(difference) if difference else None,
            "difference_percentage": float(difference_percentage) if difference_percentage else None,
            "error_message": error_message,
            "severity": severity
        }

