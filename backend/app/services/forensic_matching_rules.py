"""
Forensic Matching Rules for Cross-Document Reconciliation

Implements all matching rules for relationships between:
- Balance Sheet ↔ Income Statement
- Balance Sheet ↔ Cash Flow Statement
- Balance Sheet ↔ Mortgage Statement
- Income Statement ↔ Mortgage Statement
- Income Statement ↔ Rent Roll
- Cash Flow ↔ Rent Roll
- Cash Flow ↔ Mortgage Statement

Each rule returns MatchResult objects with confidence scores and relationship formulas.
"""
import logging
from typing import List, Dict, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.financial_period import FinancialPeriod
from app.services.matching_engines import MatchResult, ConfidenceScorer

logger = logging.getLogger(__name__)


class ForensicMatchingRules:
    """Collection of matching rules for forensic reconciliation"""
    
    def __init__(self, db: Session):
        """
        Initialize matching rules
        
        Args:
            db: Database session
        """
        self.db = db
        self.confidence_scorer = ConfidenceScorer()
    
    # ==================== BALANCE SHEET ↔ INCOME STATEMENT RULES ====================
    
    def match_current_period_earnings_to_net_income(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 1: Current Period Earnings (BS 3995-0000) = Net Income (IS 9090-0000)
        
        This is a fundamental accounting relationship that must match exactly.
        """
        # Get Current Period Earnings from Balance Sheet
        bs_earnings = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code == '3995-0000'
        ).first()
        
        # Get Net Income from Income Statement
        is_net_income = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('909%')  # Net Income accounts (9090-0000, 9099-0000, etc.)
        ).first()
        
        if not bs_earnings or not is_net_income:
            return None
        
        bs_amount = bs_earnings.amount
        is_amount = is_net_income.period_amount
        
        if bs_amount is None or is_amount is None:
            return None
        
        amount_diff = abs(bs_amount - is_amount)
        max_amount = max(abs(bs_amount), abs(is_amount))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # High confidence if within $0.01, medium if within 1%
        if amount_diff <= Decimal('0.01'):
            confidence = 95.0
        elif amount_diff_percent <= 1.0:
            confidence = 90.0
        else:
            confidence = max(60.0, 100.0 - amount_diff_percent)
        
        return MatchResult(
            source_record_id=bs_earnings.id,
            target_record_id=is_net_income.id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='equality',
            relationship_formula='BS.current_period_earnings = IS.net_income'
        )
    
    def match_retained_earnings_change(
        self,
        property_id: int,
        period_id: int,
        prior_period_id: Optional[int] = None
    ) -> Optional[MatchResult]:
        """
        Rule 2: Retained Earnings Change = Net Income - Distributions
        
        Ending RE = Beginning RE + Net Income - Distributions
        """
        # Get current period balance sheet
        current_bs = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id
        ).all()
        
        # Get beginning retained earnings (3910-0000)
        beginning_re = None
        if prior_period_id:
            prior_bs = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == prior_period_id,
                BalanceSheetData.account_code == '3910-0000'
            ).first()
            if prior_bs:
                beginning_re = prior_bs.amount
        
        # Get ending retained earnings
        ending_re_record = next((r for r in current_bs if r.account_code == '3910-0000'), None)
        if not ending_re_record:
            return None
        
        ending_re = ending_re_record.amount
        
        # Get Net Income
        net_income_record = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('909%')
        ).first()
        
        if not net_income_record:
            return None
        
        net_income = net_income_record.period_amount
        
        # Get Distributions (3990-0000)
        distributions_record = next((r for r in current_bs if r.account_code == '3990-0000'), None)
        distributions = distributions_record.amount if distributions_record else Decimal('0')
        
        if beginning_re is None:
            beginning_re = Decimal('0')
        
        # Calculate expected ending RE
        expected_ending = beginning_re + net_income - distributions
        
        if ending_re is None or expected_ending is None:
            return None
        
        amount_diff = abs(ending_re - expected_ending)
        max_amount = max(abs(ending_re), abs(expected_ending))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # High confidence if within $100 (allows for rounding)
        if amount_diff <= Decimal('100'):
            confidence = 90.0
        else:
            confidence = max(50.0, 100.0 - (amount_diff_percent * 2))
        
        return MatchResult(
            source_record_id=ending_re_record.id,
            target_record_id=0,  # Multiple sources
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='calculation',
            relationship_formula='ending_re = beginning_re + net_income - distributions'
        )
    
    # ==================== BALANCE SHEET ↔ MORTGAGE STATEMENT RULES ====================
    
    def match_long_term_debt_to_mortgages(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 3: Long-Term Debt (BS 2610-xxxx series) = Sum(Mortgage Principal Balances)
        
        All mortgage principal balances should equal long-term debt on balance sheet.
        """
        # Get long-term debt from balance sheet (2610-xxxx series)
        bs_debt = self.db.query(func.sum(BalanceSheetData.amount)).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('261%')  # Long-term debt accounts
        ).scalar() or Decimal('0')
        
        # Get total mortgage principal balances
        mortgage_principal = self.db.query(func.sum(MortgageStatementData.principal_balance)).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).scalar() or Decimal('0')
        
        if bs_debt == 0 and mortgage_principal == 0:
            return None
        
        amount_diff = abs(bs_debt - mortgage_principal)
        max_amount = max(abs(bs_debt), abs(mortgage_principal))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # Allow $100 tolerance for other debt
        if amount_diff <= Decimal('100'):
            confidence = 95.0
        elif amount_diff_percent <= 1.0:
            confidence = 85.0
        else:
            confidence = max(70.0, 100.0 - amount_diff_percent)
        
        # Get a representative record for source (use first long-term debt account)
        bs_record = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('261%')
        ).first()
        
        # Get a representative mortgage record
        mortgage_record = self.db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).first()
        
        source_id = bs_record.id if bs_record else 0
        target_id = mortgage_record.id if mortgage_record else 0
        
        return MatchResult(
            source_record_id=source_id,
            target_record_id=target_id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='equality',
            relationship_formula='BS.long_term_debt = SUM(mortgage.principal_balance)'
        )
    
    def match_escrow_accounts(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 4: Escrow Accounts (BS 1310-1340) = Mortgage Escrow Balances
        
        Balance sheet escrow accounts should match mortgage escrow balances.
        """
        # Get escrow accounts from balance sheet (1310-0000, 1320-0000, 1330-0000)
        bs_escrow = self.db.query(func.sum(BalanceSheetData.amount)).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.in_(['1310-0000', '1320-0000', '1330-0000'])
        ).scalar() or Decimal('0')
        
        # Get total mortgage escrow balances
        mortgages = self.db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).all()
        
        mortgage_escrow = sum([
            (m.tax_escrow_balance or Decimal('0')) +
            (m.insurance_escrow_balance or Decimal('0')) +
            (m.reserve_balance or Decimal('0'))
            for m in mortgages
        ], Decimal('0'))
        
        if bs_escrow == 0 and mortgage_escrow == 0:
            return None
        
        amount_diff = abs(bs_escrow - mortgage_escrow)
        max_amount = max(abs(bs_escrow), abs(mortgage_escrow))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # Allow $1000 tolerance (escrow can vary)
        if amount_diff <= Decimal('1000'):
            confidence = 85.0
        elif amount_diff_percent <= 5.0:
            confidence = 75.0
        else:
            confidence = max(60.0, 100.0 - amount_diff_percent)
        
        # Get representative records
        bs_record = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.in_(['1310-0000', '1320-0000', '1330-0000'])
        ).first()
        
        mortgage_record = mortgages[0] if mortgages else None
        
        source_id = bs_record.id if bs_record else 0
        target_id = mortgage_record.id if mortgage_record else 0
        
        return MatchResult(
            source_record_id=source_id,
            target_record_id=target_id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='equality',
            relationship_formula='BS.escrow_accounts = SUM(mortgage.escrow_balances)'
        )
    
    # ==================== INCOME STATEMENT ↔ MORTGAGE STATEMENT RULES ====================
    
    def match_interest_expense(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 5: Interest Expense (IS 6520-xxxx) = YTD Interest Paid (Mortgage)
        
        Income statement interest expense should match mortgage YTD interest paid.
        """
        # Get interest expense from income statement (6520-xxxx series)
        is_interest = self.db.query(func.sum(IncomeStatementData.period_amount)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('652%')  # Interest expense accounts
        ).scalar() or Decimal('0')
        
        # Get YTD interest paid from mortgages
        mortgage_interest = self.db.query(func.sum(MortgageStatementData.ytd_interest_paid)).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).scalar() or Decimal('0')
        
        # Annualize if needed (get period month)
        period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if period and period.period_month < 12 and mortgage_interest > 0:
            # Annualize YTD interest
            annualized_interest = (mortgage_interest / Decimal(str(period.period_month))) * Decimal('12')
        else:
            annualized_interest = mortgage_interest
        
        if is_interest == 0 and annualized_interest == 0:
            return None
        
        amount_diff = abs(is_interest - annualized_interest)
        max_amount = max(abs(is_interest), abs(annualized_interest))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # Allow 5% tolerance for accruals
        if amount_diff_percent <= 5.0:
            confidence = 90.0
        elif amount_diff_percent <= 10.0:
            confidence = 75.0
        else:
            confidence = max(65.0, 100.0 - amount_diff_percent)
        
        # Get representative records
        is_record = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('652%')
        ).first()
        
        mortgage_record = self.db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).first()
        
        source_id = is_record.id if is_record else 0
        target_id = mortgage_record.id if mortgage_record else 0
        
        return MatchResult(
            source_record_id=source_id,
            target_record_id=target_id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='equality',
            relationship_formula='IS.interest_expense = mortgage.ytd_interest_paid (annualized)'
        )
    
    # ==================== INCOME STATEMENT ↔ RENT ROLL RULES ====================
    
    def match_base_rentals_to_rent_roll(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 6: Base Rentals (IS 4010-0000) = Sum(Rent Roll Annual Rents)
        
        Income statement base rentals should equal sum of all rent roll annual rents.
        """
        # Get base rentals from income statement
        is_base_rentals = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == '4010-0000'
        ).first()
        
        if not is_base_rentals:
            return None
        
        is_amount = is_base_rentals.period_amount
        
        # Get total annual rent from rent roll
        rent_roll_total = self.db.query(func.sum(RentRollData.annual_rent)).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).scalar() or Decimal('0')
        
        # If annual_rent not available, calculate from monthly_rent
        if rent_roll_total == 0:
            monthly_total = self.db.query(func.sum(RentRollData.monthly_rent)).filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            ).scalar() or Decimal('0')
            rent_roll_total = monthly_total * Decimal('12')
        
        if is_amount is None or rent_roll_total is None:
            return None
        
        amount_diff = abs(is_amount - rent_roll_total)
        max_amount = max(abs(is_amount), abs(rent_roll_total))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # Allow 2% tolerance
        if amount_diff_percent <= 2.0:
            confidence = 95.0
        elif amount_diff_percent <= 5.0:
            confidence = 85.0
        else:
            confidence = max(70.0, 100.0 - amount_diff_percent)
        
        # Get a representative rent roll record
        rent_roll_record = self.db.query(RentRollData).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).first()
        
        target_id = rent_roll_record.id if rent_roll_record else 0
        
        return MatchResult(
            source_record_id=is_base_rentals.id,
            target_record_id=target_id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='sum',
            relationship_formula='IS.base_rentals = SUM(rent_roll.annual_rent)'
        )
    
    def match_occupancy_rate(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 7: Occupancy Rate Match
        
        Calculated occupancy from rent roll should match any occupancy metric in income statement.
        """
        # Calculate occupancy from rent roll
        rent_roll = self.db.query(RentRollData).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).all()
        
        if not rent_roll:
            return None
        
        total_units = len(rent_roll)
        occupied_units = sum(1 for r in rent_roll if r.occupancy_status == 'occupied')
        
        if total_units == 0:
            return None
        
        rent_roll_occupancy = (occupied_units / total_units) * 100
        
        # Try to find occupancy in income statement (if stored)
        # This is optional - occupancy may not be in income statement
        is_occupancy_record = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == '4999-0000'  # If occupancy is stored here
        ).first()
        
        if not is_occupancy_record:
            return None  # Occupancy not in income statement
        
        is_occupancy = is_occupancy_record.period_percentage
        
        if is_occupancy is None:
            return None
        
        occupancy_diff = abs(is_occupancy - rent_roll_occupancy)
        
        # Allow 1% tolerance
        if occupancy_diff <= 1.0:
            confidence = 90.0
        elif occupancy_diff <= 5.0:
            confidence = 75.0
        else:
            confidence = max(70.0, 100.0 - occupancy_diff)
        
        return MatchResult(
            source_record_id=is_occupancy_record.id,
            target_record_id=0,  # Multiple rent roll records
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=Decimal(str(occupancy_diff)),
            amount_difference_percent=occupancy_diff,
            match_algorithm='calculated_relationship',
            relationship_type='equality',
            relationship_formula='IS.occupancy_rate = rent_roll.occupied_units / total_units'
        )
    
    # ==================== CASH FLOW ↔ BALANCE SHEET RULES ====================
    
    def match_ending_cash(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 8: Ending Cash (CF) = Cash Operating Account (BS 0122-0000)
        
        Cash flow ending cash should match balance sheet operating cash.
        """
        # Get ending cash from cash flow (typically in cash_flow_headers or last line)
        # For now, we'll look for cash flow data with account_code indicating ending cash
        cf_ending = self.db.query(CashFlowData).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.account_code == '9999-0000'  # Ending cash indicator
        ).first()
        
        # Alternative: Get from cash_flow_headers if available
        from app.models.cash_flow_header import CashFlowHeader
        cf_header = self.db.query(CashFlowHeader).filter(
            CashFlowHeader.property_id == property_id,
            CashFlowHeader.period_id == period_id
        ).first()
        
        if cf_header and hasattr(cf_header, 'ending_cash_balance'):
            cf_ending_cash = cf_header.ending_cash_balance
        elif cf_ending:
            cf_ending_cash = cf_ending.period_amount
        else:
            return None
        
        # Get operating cash from balance sheet
        bs_cash = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code == '0122-0000'  # Cash - Operating
        ).first()
        
        if not bs_cash:
            return None
        
        bs_amount = bs_cash.amount
        
        if cf_ending_cash is None or bs_amount is None:
            return None
        
        amount_diff = abs(cf_ending_cash - bs_amount)
        max_amount = max(abs(cf_ending_cash), abs(bs_amount))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # Allow $100 tolerance (multiple cash accounts possible)
        if amount_diff <= Decimal('100'):
            confidence = 95.0
        elif amount_diff_percent <= 1.0:
            confidence = 85.0
        else:
            confidence = max(75.0, 100.0 - amount_diff_percent)
        
        source_id = cf_ending.id if cf_ending else (cf_header.id if cf_header else 0)
        
        return MatchResult(
            source_record_id=source_id,
            target_record_id=bs_cash.id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='equality',
            relationship_formula='CF.ending_cash = BS.cash_operating'
        )
    
    def match_cash_flow_reconciliation(
        self,
        property_id: int,
        period_id: int,
        prior_period_id: Optional[int] = None
    ) -> Optional[MatchResult]:
        """
        Rule 9: Cash Flow Reconciliation
        
        Ending Cash = Beginning Cash + Net Cash Flow
        """
        if not prior_period_id:
            return None
        
        # Get beginning cash from prior period balance sheet
        prior_bs_cash = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == prior_period_id,
            BalanceSheetData.account_code == '0122-0000'
        ).first()
        
        if not prior_bs_cash:
            return None
        
        beginning_cash = prior_bs_cash.amount
        
        # Get net cash flow from cash flow statement
        from app.models.cash_flow_header import CashFlowHeader
        cf_header = self.db.query(CashFlowHeader).filter(
            CashFlowHeader.property_id == property_id,
            CashFlowHeader.period_id == period_id
        ).first()
        
        if not cf_header:
            return None
        
        net_cash_flow = cf_header.cash_flow if hasattr(cf_header, 'cash_flow') else None
        
        if net_cash_flow is None:
            # Calculate from cash flow data
            cf_data = self.db.query(CashFlowData).filter(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id
            ).all()
            
            # Sum operating, investing, financing activities
            net_cash_flow = sum([
                (r.period_amount or Decimal('0'))
                for r in cf_data
            ], Decimal('0'))
        
        # Get actual ending cash from current balance sheet
        current_bs_cash = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code == '0122-0000'
        ).first()
        
        if not current_bs_cash:
            return None
        
        actual_ending = current_bs_cash.amount
        expected_ending = beginning_cash + net_cash_flow
        
        if actual_ending is None or expected_ending is None:
            return None
        
        amount_diff = abs(actual_ending - expected_ending)
        max_amount = max(abs(actual_ending), abs(expected_ending))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # High confidence if within $100
        if amount_diff <= Decimal('100'):
            confidence = 95.0
        elif amount_diff_percent <= 1.0:
            confidence = 85.0
        else:
            confidence = max(70.0, 100.0 - amount_diff_percent)
        
        return MatchResult(
            source_record_id=current_bs_cash.id,
            target_record_id=0,  # Calculated from multiple sources
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='calculation',
            relationship_formula='ending_cash = beginning_cash + net_cash_flow'
        )
    
    # ==================== CASH FLOW ↔ MORTGAGE STATEMENT RULES ====================
    
    def match_principal_payments(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 10: Principal Payments (CF Financing) = Mortgage YTD Principal Paid
        
        Cash flow principal payments should match mortgage YTD principal paid.
        """
        # Get principal payments from cash flow (financing section, account_code starts with '8')
        cf_principal = self.db.query(func.sum(CashFlowData.period_amount)).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.account_code.like('8%'),  # Financing section
            CashFlowData.account_name.ilike('%principal%')
        ).scalar() or Decimal('0')
        
        # Get YTD principal paid from mortgages
        mortgage_principal = self.db.query(func.sum(MortgageStatementData.ytd_principal_paid)).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).scalar() or Decimal('0')
        
        if cf_principal == 0 and mortgage_principal == 0:
            return None
        
        amount_diff = abs(cf_principal - mortgage_principal)
        max_amount = max(abs(cf_principal), abs(mortgage_principal))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # Allow $1000 tolerance (timing differences possible)
        if amount_diff <= Decimal('1000'):
            confidence = 90.0
        elif amount_diff_percent <= 5.0:
            confidence = 80.0
        else:
            confidence = max(65.0, 100.0 - amount_diff_percent)
        
        # Get representative records
        cf_record = self.db.query(CashFlowData).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.account_code.like('8%'),
            CashFlowData.account_name.ilike('%principal%')
        ).first()
        
        mortgage_record = self.db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).first()
        
        source_id = cf_record.id if cf_record else 0
        target_id = mortgage_record.id if mortgage_record else 0
        
        return MatchResult(
            source_record_id=source_id,
            target_record_id=target_id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='equality',
            relationship_formula='CF.principal_payments = mortgage.ytd_principal_paid'
        )
    
    # ==================== ADDITIONAL RULES ====================
    
    def match_security_deposits(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[MatchResult]:
        """
        Rule 11: Security Deposits (BS Liability) = Sum(Rent Roll Security Deposits)
        
        Balance sheet security deposits liability should equal sum of rent roll security deposits.
        """
        # Get security deposits from balance sheet (typically in liabilities)
        bs_deposits = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('2%'),  # Liabilities
            BalanceSheetData.account_name.ilike('%security%deposit%')
        ).first()
        
        if not bs_deposits:
            return None
        
        bs_amount = bs_deposits.amount
        
        # Get total security deposits from rent roll
        rent_roll_deposits = self.db.query(func.sum(RentRollData.security_deposit)).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).scalar() or Decimal('0')
        
        if bs_amount is None or rent_roll_deposits is None:
            return None
        
        amount_diff = abs(bs_amount - rent_roll_deposits)
        max_amount = max(abs(bs_amount), abs(rent_roll_deposits))
        amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
        
        # Allow 5% tolerance (deposits can be refunded/added)
        if amount_diff_percent <= 5.0:
            confidence = 85.0
        elif amount_diff_percent <= 10.0:
            confidence = 75.0
        else:
            confidence = max(60.0, 100.0 - amount_diff_percent)
        
        rent_roll_record = self.db.query(RentRollData).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).first()
        
        target_id = rent_roll_record.id if rent_roll_record else 0
        
        return MatchResult(
            source_record_id=bs_deposits.id,
            target_record_id=target_id,
            match_type='calculated',
            confidence_score=confidence,
            amount_difference=amount_diff,
            amount_difference_percent=amount_diff_percent,
            match_algorithm='calculated_relationship',
            relationship_type='sum',
            relationship_formula='BS.security_deposits = SUM(rent_roll.security_deposit)'
        )
    
    def find_all_matches(
        self,
        property_id: int,
        period_id: int,
        prior_period_id: Optional[int] = None
    ) -> List[MatchResult]:
        """
        Execute all matching rules and return all matches
        
        Args:
            property_id: Property ID
            period_id: Current period ID
            prior_period_id: Prior period ID (for reconciliation rules)
            
        Returns:
            List of all MatchResult objects
        """
        matches = []
        
        # Balance Sheet ↔ Income Statement
        match1 = self.match_current_period_earnings_to_net_income(property_id, period_id)
        if match1:
            matches.append(match1)
        
        match2 = self.match_retained_earnings_change(property_id, period_id, prior_period_id)
        if match2:
            matches.append(match2)
        
        # Balance Sheet ↔ Mortgage
        match3 = self.match_long_term_debt_to_mortgages(property_id, period_id)
        if match3:
            matches.append(match3)
        
        match4 = self.match_escrow_accounts(property_id, period_id)
        if match4:
            matches.append(match4)
        
        # Income Statement ↔ Mortgage
        match5 = self.match_interest_expense(property_id, period_id)
        if match5:
            matches.append(match5)
        
        # Income Statement ↔ Rent Roll
        match6 = self.match_base_rentals_to_rent_roll(property_id, period_id)
        if match6:
            matches.append(match6)
        
        match7 = self.match_occupancy_rate(property_id, period_id)
        if match7:
            matches.append(match7)
        
        # Cash Flow ↔ Balance Sheet
        match8 = self.match_ending_cash(property_id, period_id)
        if match8:
            matches.append(match8)
        
        match9 = self.match_cash_flow_reconciliation(property_id, period_id, prior_period_id)
        if match9:
            matches.append(match9)
        
        # Cash Flow ↔ Mortgage
        match10 = self.match_principal_payments(property_id, period_id)
        if match10:
            matches.append(match10)
        
        # Additional rules
        match11 = self.match_security_deposits(property_id, period_id)
        if match11:
            matches.append(match11)
        
        logger.info(f"Found {len(matches)} cross-document matches for property {property_id}, period {period_id}")
        
        return matches

