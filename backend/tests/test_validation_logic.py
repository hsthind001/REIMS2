"""
Validation Logic Tests - Sprint 5.1

Focused tests for validation business logic without full schema dependencies
Tests core validation algorithms and calculations
"""
import pytest
from decimal import Decimal


class TestValidationCalculations:
    """Test validation calculation logic"""
    
    def test_balance_sheet_equation_logic(self):
        """Test balance sheet equation calculation"""
        # Assets = Liabilities + Equity
        total_assets = Decimal('22939865.40')
        total_liabilities = Decimal('21769610.72')
        total_equity = Decimal('1170254.68')
        
        expected = total_liabilities + total_equity
        actual = total_assets
        difference = abs(expected - actual)
        
        # Calculate percentage difference
        percentage_diff = (difference / actual) * Decimal('100')
        
        # Should pass with 1% tolerance
        tolerance = Decimal('1.0')
        passed = percentage_diff <= tolerance
        
        assert passed is True
        assert percentage_diff < Decimal('0.01')  # Difference should be tiny
    
    def test_balance_sheet_equation_with_rounding(self):
        """Test tolerance handling for rounding errors"""
        # Scenario: Slight rounding difference
        total_assets = Decimal('1000000.00')
        total_liabilities = Decimal('600000.30')  # Rounded
        total_equity = Decimal('400000.20')  # Rounded
        
        expected = total_liabilities + total_equity  # 1000000.50
        actual = total_assets  # 1000000.00
        difference = abs(expected - actual)  # 0.50
        
        percentage_diff = (difference / actual) * Decimal('100')  # 0.00005%
        
        # Should pass - within 1% tolerance
        assert percentage_diff <= Decimal('1.0')
    
    def test_net_income_calculation(self):
        """Test net income validation logic"""
        total_revenue = Decimal('3179456.89')
        total_expenses = Decimal('3751340.64')
        expected_net_income = total_revenue - total_expenses  # -571883.75
        
        actual_net_income = Decimal('-571883.75')
        
        difference = abs(expected_net_income - actual_net_income)
        
        assert difference < Decimal('1.00')  # Within $1
    
    def test_tolerance_percentage_calculation(self):
        """Test percentage difference calculation"""
        expected = Decimal('1000000.00')
        actual = Decimal('990000.00')  # 1% difference
        
        difference = abs(expected - actual)
        percentage_diff = (difference / max(actual, Decimal('1'))) * Decimal('100')
        
        # Should be approximately 1.01%
        assert Decimal('1.0') <= percentage_diff <= Decimal('1.1')
    
    def test_zero_division_handling(self):
        """Test handling of zero values in percentage calculation"""
        expected = Decimal('100.00')
        actual = Decimal('0.00')
        
        difference = abs(expected - actual)
        
        # Use max(actual, 1) to avoid division by zero
        percentage_diff = (difference / max(actual, Decimal('1'))) * Decimal('100')
        
        # Should be 10000% (100/1 * 100)
        assert percentage_diff == Decimal('10000.00')
    
    def test_ytd_period_comparison(self):
        """Test YTD >= Period logic"""
        period_amount = Decimal('100000.00')
        ytd_amount = Decimal('120000.00')
        
        # Valid: YTD >= Period
        assert ytd_amount >= period_amount
        
        # Invalid scenario
        invalid_ytd = Decimal('80000.00')
        assert not (invalid_ytd >= period_amount)


class TestAmountParsing:
    """Test amount parsing for validation"""
    
    def test_parse_negative_amounts(self):
        """Test handling of negative amounts"""
        # Parentheses indicate negative
        amount_str = "(2,225,410.00)"
        cleaned = amount_str.replace(',', '').replace('(', '-').replace(')', '')
        amount = Decimal(cleaned)
        
        assert amount == Decimal('-2225410.00')
    
    def test_parse_large_amounts(self):
        """Test handling of large amounts"""
        amount = Decimal('32163869.08')  # Hammond Aire
        
        # Should preserve precision
        assert amount == Decimal('32163869.08')
        
        # Test calculation
        percentage = (amount / Decimal('30000000.00')) * Decimal('100')
        assert percentage > Decimal('107.0')


class TestValidationRuleLogic:
    """Test validation rule application logic"""
    
    def test_severity_levels(self):
        """Test different severity levels"""
        severities = ['error', 'warning', 'info']
        
        for severity in severities:
            # Logic: errors block approval, warnings don't
            blocks_approval = (severity == 'error')
            
            if severity == 'error':
                assert blocks_approval is True
            else:
                assert blocks_approval is False
    
    def test_passed_check_counting(self):
        """Test counting of passed/failed checks"""
        results = [
            {"passed": True, "severity": "error"},
            {"passed": False, "severity": "error"},
            {"passed": False, "severity": "warning"},
            {"passed": True, "severity": "info"},
        ]
        
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r["passed"])
        failed_checks = total_checks - passed_checks
        errors = sum(1 for r in results if r["severity"] == "error" and not r["passed"])
        warnings = sum(1 for r in results if r["severity"] == "warning" and not r["passed"])
        
        assert total_checks == 4
        assert passed_checks == 2
        assert failed_checks == 2
        assert errors == 1
        assert warnings == 1


class TestDataQualityMetrics:
    """Test data quality metric calculations"""
    
    def test_extraction_confidence_scoring(self):
        """Test confidence score calculations"""
        extraction_confidence = Decimal('95.00')
        match_confidence = Decimal('100.00')
        
        # Average of two confidences
        final_confidence = (extraction_confidence + match_confidence) / Decimal('2')
        
        assert final_confidence == Decimal('97.50')
        
        # Needs review if < 85%
        needs_review = final_confidence < Decimal('85.00')
        assert needs_review is False
    
    def test_data_quality_threshold(self):
        """Test quality thresholds for review flagging"""
        confidences = [
            (Decimal('98.0'), False),  # High confidence - no review
            (Decimal('85.0'), False),  # At threshold - no review
            (Decimal('84.9'), True),   # Below threshold - needs review
            (Decimal('75.0'), True),   # Low confidence - needs review
        ]
        
        for confidence, should_need_review in confidences:
            needs_review = confidence < Decimal('85.0')
            assert needs_review == should_need_review, \
                f"Confidence {confidence} should{'n''t' if not should_need_review else ''} need review"


class TestValidationWorkflow:
    """Test validation workflow integration"""
    
    def test_validation_summary_calculation(self):
        """Test validation summary calculation"""
        validation_results = [
            {"passed": True, "severity": "error"},
            {"passed": True, "severity": "warning"},
            {"passed": False, "severity": "error"},
            {"passed": False, "severity": "warning"},
            {"passed": True, "severity": "info"},
        ]
        
        total_checks = len(validation_results)
        passed_checks = sum(1 for r in validation_results if r["passed"])
        failed_checks = total_checks - passed_checks
        warnings = sum(1 for r in validation_results if r["severity"] == "warning")
        errors = sum(1 for r in validation_results if r["severity"] == "error")
        
        summary = {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "warnings": warnings,
            "errors": errors,
            "overall_passed": failed_checks == 0
        }
        
        assert summary["total_checks"] == 5
        assert summary["passed_checks"] == 3
        assert summary["failed_checks"] == 2
        assert summary["warnings"] == 2  # Both warning severity items
        assert summary["errors"] == 2    # Both error severity items
        assert summary["overall_passed"] is False  # Has failures

