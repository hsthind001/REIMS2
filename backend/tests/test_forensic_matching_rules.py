"""
Unit tests for forensic reconciliation matching rules

Tests for cross-document matching rules:
- Balance Sheet <-> Income Statement
- Balance Sheet <-> Mortgage Statement
- Income Statement <-> Rent Roll
- Cash Flow <-> Balance Sheet
- etc.
"""

import pytest
from decimal import Decimal
from app.services import forensic_matching_rules as rules


class TestBalanceSheetIncomeStatementRules:
    """Test rules matching Balance Sheet to Income Statement"""
    
    def test_current_period_earnings_to_net_income_exact(self):
        bs_data = [
            {'account_code': '3995-0000', 'amount': Decimal('125000.00')}
        ]
        is_data = [
            {'account_code': '9090-0000', 'period_amount': Decimal('125000.00')}
        ]
        
        result = rules.match_current_period_earnings_to_net_income(bs_data, is_data)
        assert result is not None
        assert result['relationship_type'] == 'equality'
        assert result['relationship_formula'] == 'BS.CurrentPeriodEarnings = IS.NetIncome'
        assert result['confidence_score'] == Decimal('95.00')
    
    def test_current_period_earnings_to_net_income_mismatch(self):
        bs_data = [
            {'account_code': '3995-0000', 'amount': Decimal('125000.00')}
        ]
        is_data = [
            {'account_code': '9090-0000', 'period_amount': Decimal('130000.00')}
        ]
        
        result = rules.match_current_period_earnings_to_net_income(bs_data, is_data)
        assert result is not None
        assert result['confidence_score'] == Decimal('60.00')  # Lower confidence for mismatch
    
    def test_current_period_earnings_missing_source(self):
        bs_data = []
        is_data = [
            {'account_code': '9090-0000', 'period_amount': Decimal('125000.00')}
        ]
        
        result = rules.match_current_period_earnings_to_net_income(bs_data, is_data)
        assert result is None
    
    def test_current_period_earnings_missing_target(self):
        bs_data = [
            {'account_code': '3995-0000', 'amount': Decimal('125000.00')}
        ]
        is_data = []
        
        result = rules.match_current_period_earnings_to_net_income(bs_data, is_data)
        assert result is None


class TestBalanceSheetMortgageRules:
    """Test rules matching Balance Sheet to Mortgage Statement"""
    
    def test_long_term_debt_to_mortgages_exact(self):
        bs_data = [
            {'account_code': '2610-0000', 'amount': Decimal('5000000.00')},
            {'account_code': '2610-0100', 'amount': Decimal('2000000.00')}
        ]
        mortgage_data = [
            {'principal_balance': Decimal('5000000.00')},
            {'principal_balance': Decimal('2000000.00')}
        ]
        
        result = rules.match_long_term_debt_to_mortgages(bs_data, mortgage_data)
        assert result is not None
        assert result['relationship_type'] == 'equality'
        assert result['relationship_formula'] == 'BS.LongTermDebt = SUM(Mortgage.PrincipalBalances)'
        assert result['confidence_score'] == Decimal('95.00')
    
    def test_long_term_debt_to_mortgages_within_tolerance(self):
        bs_data = [
            {'account_code': '2610-0000', 'amount': Decimal('5000000.00')}
        ]
        mortgage_data = [
            {'principal_balance': Decimal('5000050.00')}  # $50 difference
        ]
        
        result = rules.match_long_term_debt_to_mortgages(bs_data, mortgage_data)
        assert result is not None
        assert result['confidence_score'] == Decimal('95.00')  # Within $100 tolerance
    
    def test_long_term_debt_to_mortgages_outside_tolerance(self):
        bs_data = [
            {'account_code': '2610-0000', 'amount': Decimal('5000000.00')}
        ]
        mortgage_data = [
            {'principal_balance': Decimal('5100000.00')}  # $100,000 difference
        ]
        
        result = rules.match_long_term_debt_to_mortgages(bs_data, mortgage_data)
        assert result is not None
        assert result['confidence_score'] == Decimal('70.00')  # Lower confidence


class TestIncomeStatementRentRollRules:
    """Test rules matching Income Statement to Rent Roll"""
    
    def test_base_rentals_to_rent_roll_exact(self):
        is_data = [
            {'account_code': '4010-0000', 'period_amount': Decimal('1200000.00')}
        ]
        rent_roll_data = [
            {'annual_rent': Decimal('300000.00')},
            {'annual_rent': Decimal('300000.00')},
            {'annual_rent': Decimal('300000.00')},
            {'annual_rent': Decimal('300000.00')}
        ]
        
        result = rules.match_base_rentals_to_rent_roll(is_data, rent_roll_data)
        assert result is not None
        assert result['relationship_type'] == 'equality'
        assert result['confidence_score'] >= Decimal('95.00')
    
    def test_base_rentals_to_rent_roll_with_vacancy(self):
        is_data = [
            {'account_code': '4010-0000', 'period_amount': Decimal('1200000.00')}
        ]
        rent_roll_data = [
            {'annual_rent': Decimal('300000.00')},
            {'annual_rent': Decimal('300000.00')},
            {'annual_rent': Decimal('300000.00')},
            {'annual_rent': Decimal('0.00')}  # Vacant unit
        ]
        
        result = rules.match_base_rentals_to_rent_roll(is_data, rent_roll_data)
        # Should still match but with lower confidence due to vacancy
        assert result is not None


class TestCashFlowBalanceSheetRules:
    """Test rules matching Cash Flow to Balance Sheet"""
    
    def test_ending_cash_to_cash_operating_account(self):
        cf_data = [
            {'account_code': '9999-0000', 'amount': Decimal('150000.00')}
        ]
        bs_data = [
            {'account_code': '0122-0000', 'amount': Decimal('150000.00')}
        ]
        
        result = rules.match_ending_cash_to_cash_operating_account(cf_data, bs_data)
        assert result is not None
        assert result['relationship_type'] == 'equality'
        assert result['confidence_score'] >= Decimal('95.00')
    
    def test_cash_flow_reconciliation(self):
        cf_data = [
            {'account_code': '9999-0000', 'amount': Decimal('150000.00')}  # Ending cash
        ]
        bs_data = [
            {'account_code': '0122-0000', 'amount': Decimal('100000.00')},  # Beginning cash
            {'account_code': '0122-0000', 'amount': Decimal('150000.00')}  # Ending cash
        ]
        
        # This would require beginning cash from prior period
        # For now, test that the rule exists
        assert hasattr(rules, 'match_cash_flow_reconciliation')


class TestRuleHelpers:
    """Test helper functions for matching rules"""
    
    def test_get_amount_by_account_code(self):
        data = [
            {'account_code': '0122-0000', 'amount': Decimal('100000.00')},
            {'account_code': '0123-0000', 'amount': Decimal('50000.00')}
        ]
        
        amount = rules._get_amount(data, '0122-0000')
        assert amount == Decimal('100000.00')
        
        amount = rules._get_amount(data, '9999-0000')
        assert amount == Decimal('0.00')  # Not found
    
    def test_get_sum_for_prefix(self):
        data = [
            {'account_code': '2610-0000', 'amount': Decimal('5000000.00')},
            {'account_code': '2610-0100', 'amount': Decimal('2000000.00')},
            {'account_code': '0122-0000', 'amount': Decimal('100000.00')}  # Should be excluded
        ]
        
        total = rules._get_sum_for_prefix(data, '261')
        assert total == Decimal('7000000.00')

