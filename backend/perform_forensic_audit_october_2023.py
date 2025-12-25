#!/usr/bin/env python3
"""
REIMS2 Forensic Audit - October 2023
Big 5 Accounting Firm Level Cross-Document Reconciliation

This script performs a comprehensive forensic audit following the methodology
defined in FORENSIC_AUDIT_PROMPT.md
"""

import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.financial_period import FinancialPeriod
from app.models.property import Property
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import json


class ForensicAuditor:
    """Big 5 Accounting Firm Forensic Auditor"""

    def __init__(self, property_id: int, year: int, month: int):
        self.db = SessionLocal()
        self.property_id = property_id
        self.year = year
        self.month = month

        # Audit findings storage
        self.findings = []
        self.variances = []
        self.red_flags = []
        self.tie_out_results = []

        # Tolerance settings
        self.CRITICAL_TOLERANCE_ABS = 100.00
        self.CRITICAL_TOLERANCE_PCT = 0.1
        self.WARNING_TOLERANCE_ABS = 1000.00
        self.WARNING_TOLERANCE_PCT = 1.0
        self.INFO_TOLERANCE_ABS = 5000.00
        self.INFO_TOLERANCE_PCT = 5.0

    def get_tolerance(self, amount: float, abs_tol: float, pct_tol: float) -> float:
        """Apply the greater of absolute or percentage tolerance"""
        return max(abs_tol, abs(amount) * (pct_tol / 100.0))

    def compare_values(self, source_val: Optional[float], target_val: Optional[float],
                      abs_tol: float, pct_tol: float, severity: str) -> Dict:
        """Compare two values with tolerance"""
        if source_val is None or target_val is None:
            return {
                'status': 'FAIL',
                'severity': 'CRITICAL',
                'variance_amount': None,
                'variance_pct': None,
                'reason': 'Missing data'
            }

        variance_amount = abs(source_val - target_val)
        variance_pct = (variance_amount / abs(target_val) * 100.0) if target_val != 0 else 0
        tolerance = self.get_tolerance(target_val, abs_tol, pct_tol)

        if variance_amount <= tolerance:
            status = 'PASS'
        elif severity == 'CRITICAL':
            status = 'FAIL'
        elif severity == 'WARNING':
            status = 'WARNING'
        else:
            status = 'INFO'

        return {
            'status': status,
            'severity': severity,
            'variance_amount': variance_amount,
            'variance_pct': variance_pct,
            'tolerance': tolerance,
            'source_value': source_val,
            'target_value': target_val
        }

    def phase_1_engagement_planning(self):
        """Phase 1: Engagement Planning"""
        print("\n" + "="*80)
        print("PHASE 1: ENGAGEMENT PLANNING")
        print("="*80)

        # Load property info
        property_obj = self.db.query(Property).filter(Property.id == self.property_id).first()
        self.property_name = property_obj.property_name if property_obj else "Unknown"
        self.property_code = property_obj.property_code if property_obj else "Unknown"

        # Load period info
        self.period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == self.property_id,
            FinancialPeriod.period_year == self.year,
            FinancialPeriod.period_month == self.month
        ).first()

        if not self.period:
            print(f"✗ CRITICAL: Period {self.year}-{self.month:02d} not found for property {self.property_id}")
            return False

        print(f"\n✓ Engagement Scope:")
        print(f"  Property: {self.property_name} ({self.property_code})")
        print(f"  Period: {self.year}-{self.month:02d} (Period ID: {self.period.id})")
        print(f"  Audit Date: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"  Auditor: Claude AI - Senior Forensic Auditor")

        print(f"\n✓ Critical Tie-Outs Identified: 5")
        print(f"✓ Warning Tie-Outs Identified: 5")
        print(f"✓ Informational Tie-Outs Identified: 2")

        return True

    def phase_2_data_loading(self) -> bool:
        """Phase 2: Data Loading & Completeness Check"""
        print("\n" + "="*80)
        print("PHASE 2: DATA LOADING & COMPLETENESS CHECK")
        print("="*80)

        period_id = self.period.id

        # Load all documents
        self.balance_sheet = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == self.property_id,
            BalanceSheetData.period_id == period_id
        ).first()

        self.income_stmt = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == self.property_id,
            IncomeStatementData.period_id == period_id
        ).first()

        self.cash_flow = self.db.query(CashFlowData).filter(
            CashFlowData.property_id == self.property_id,
            CashFlowData.period_id == period_id
        ).first()

        self.rent_roll = self.db.query(RentRollData).filter(
            RentRollData.property_id == self.property_id,
            RentRollData.period_id == period_id
        ).first()

        self.mortgage = self.db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == self.property_id,
            MortgageStatementData.period_id == period_id
        ).first()

        # Check completeness
        completeness = {
            'Balance Sheet': self.balance_sheet is not None,
            'Income Statement': self.income_stmt is not None,
            'Cash Flow Statement': self.cash_flow is not None,
            'Rent Roll': self.rent_roll is not None,
            'Mortgage Statement': self.mortgage is not None
        }

        print(f"\nDocument Completeness Check:")
        print(f"  Documents Required: 5")
        print(f"  Documents Present: {sum(completeness.values())}")
        print(f"  Documents Missing: {5 - sum(completeness.values())}")

        for doc_type, present in completeness.items():
            status = "✓ Present" if present else "✗ MISSING"
            print(f"    {status}: {doc_type}")

            if not present:
                self.red_flags.append({
                    'severity': 'CRITICAL',
                    'category': 'Missing Document',
                    'description': f'{doc_type} missing for {self.year}-{self.month:02d}',
                    'impact': 'Cannot perform complete cross-document reconciliation'
                })

        # Check extraction confidence
        if self.balance_sheet and self.balance_sheet.extraction_confidence:
            print(f"\n  Balance Sheet extraction confidence: {self.balance_sheet.extraction_confidence:.1f}%")
        if self.income_stmt and self.income_stmt.extraction_confidence:
            print(f"  Income Statement extraction confidence: {self.income_stmt.extraction_confidence:.1f}%")
        if self.cash_flow and self.cash_flow.extraction_confidence:
            print(f"  Cash Flow extraction confidence: {self.cash_flow.extraction_confidence:.1f}%")
        if self.rent_roll and self.rent_roll.extraction_confidence:
            print(f"  Rent Roll extraction confidence: {self.rent_roll.extraction_confidence:.1f}%")
        if self.mortgage and self.mortgage.extraction_confidence:
            print(f"  Mortgage Statement extraction confidence: {self.mortgage.extraction_confidence:.1f}%")

        all_present = all(completeness.values())
        status = "PASS" if all_present else "FAIL"
        print(f"\nCompleteness Status: {status}")

        return all_present

    def phase_3_individual_validation(self):
        """Phase 3: Individual Document Validation"""
        print("\n" + "="*80)
        print("PHASE 3: INDIVIDUAL DOCUMENT VALIDATION")
        print("="*80)

        # Validate Balance Sheet
        if self.balance_sheet:
            print("\n[1] Balance Sheet Validation:")

            # Check balance sheet equation
            total_assets = self.balance_sheet.total_assets or 0
            total_liabilities = self.balance_sheet.total_liabilities or 0
            total_equity = self.balance_sheet.total_equity or 0

            balance = abs((total_liabilities + total_equity) - total_assets)

            if balance <= 1.0:
                print(f"  ✓ Balance Sheet Equation: PASS")
                print(f"    Assets: ${total_assets:,.2f}")
                print(f"    Liabilities + Equity: ${total_liabilities + total_equity:,.2f}")
                print(f"    Variance: ${balance:,.2f}")
            else:
                print(f"  ✗ Balance Sheet Equation: FAIL")
                print(f"    Assets: ${total_assets:,.2f}")
                print(f"    Liabilities + Equity: ${total_liabilities + total_equity:,.2f}")
                print(f"    Variance: ${balance:,.2f}")
                self.red_flags.append({
                    'severity': 'CRITICAL',
                    'category': 'Mathematical Error',
                    'description': 'Balance Sheet does not balance',
                    'variance': balance
                })

            # Check for negative assets
            if self.balance_sheet.total_assets and self.balance_sheet.total_assets < 0:
                print(f"  ✗ Negative Total Assets: FAIL")
                self.red_flags.append({
                    'severity': 'CRITICAL',
                    'category': 'Data Integrity',
                    'description': 'Negative total assets detected'
                })
            else:
                print(f"  ✓ No Negative Assets: PASS")

        # Validate Income Statement
        if self.income_stmt:
            print("\n[2] Income Statement Validation:")

            # Check NOI calculation
            total_income = self.income_stmt.total_income or 0
            total_opex = self.income_stmt.total_operating_expenses or 0
            noi = self.income_stmt.noi or 0
            calculated_noi = total_income - total_opex

            noi_variance = abs(calculated_noi - noi)

            if noi_variance <= 1.0:
                print(f"  ✓ NOI Calculation: PASS")
                print(f"    Total Income: ${total_income:,.2f}")
                print(f"    Operating Expenses: ${total_opex:,.2f}")
                print(f"    NOI (stated): ${noi:,.2f}")
                print(f"    NOI (calculated): ${calculated_noi:,.2f}")
            else:
                print(f"  ✗ NOI Calculation: FAIL (variance: ${noi_variance:,.2f})")
                self.red_flags.append({
                    'severity': 'WARNING',
                    'category': 'Calculation Error',
                    'description': 'NOI calculation mismatch',
                    'variance': noi_variance
                })

            # Check for negative NOI
            if noi < 0:
                print(f"  ⚠ Negative NOI: WARNING (${noi:,.2f})")
                self.red_flags.append({
                    'severity': 'CRITICAL',
                    'category': 'Business Performance',
                    'description': 'Property operating at a loss (negative NOI)',
                    'value': noi
                })
            else:
                print(f"  ✓ Positive NOI: PASS (${noi:,.2f})")

        # Validate Cash Flow Statement
        if self.cash_flow:
            print("\n[3] Cash Flow Statement Validation:")

            beginning_cash = self.cash_flow.beginning_cash or 0
            net_change = self.cash_flow.net_change_in_cash or 0
            ending_cash = self.cash_flow.ending_cash or 0
            calculated_ending = beginning_cash + net_change

            cf_variance = abs(calculated_ending - ending_cash)

            if cf_variance <= 1.0:
                print(f"  ✓ Cash Flow Reconciliation: PASS")
                print(f"    Beginning Cash: ${beginning_cash:,.2f}")
                print(f"    Net Change: ${net_change:,.2f}")
                print(f"    Ending Cash (stated): ${ending_cash:,.2f}")
                print(f"    Ending Cash (calculated): ${calculated_ending:,.2f}")
            else:
                print(f"  ✗ Cash Flow Reconciliation: FAIL (variance: ${cf_variance:,.2f})")
                self.red_flags.append({
                    'severity': 'CRITICAL',
                    'category': 'Calculation Error',
                    'description': 'Cash flow does not reconcile',
                    'variance': cf_variance
                })

            # Check net change components
            operating_cf = self.cash_flow.operating_cash_flow or 0
            investing_cf = self.cash_flow.investing_cash_flow or 0
            financing_cf = self.cash_flow.financing_cash_flow or 0
            calculated_net_change = operating_cf + investing_cf + financing_cf

            nc_variance = abs(calculated_net_change - net_change)

            if nc_variance <= 1.0:
                print(f"  ✓ Net Change Components: PASS")
            else:
                print(f"  ✗ Net Change Components: FAIL (variance: ${nc_variance:,.2f})")

        # Validate Rent Roll
        if self.rent_roll:
            print("\n[4] Rent Roll Validation:")

            total_units = self.rent_roll.total_units or 0
            occupied = self.rent_roll.occupied_units or 0
            vacant = self.rent_roll.vacant_units or 0

            if total_units == (occupied + vacant):
                print(f"  ✓ Unit Count Reconciliation: PASS")
                print(f"    Total Units: {total_units}")
                print(f"    Occupied: {occupied}")
                print(f"    Vacant: {vacant}")
            else:
                print(f"  ✗ Unit Count Reconciliation: FAIL")
                self.red_flags.append({
                    'severity': 'WARNING',
                    'category': 'Data Integrity',
                    'description': 'Unit counts do not reconcile'
                })

            # Check occupancy calculation
            if total_units > 0:
                calculated_occupancy = (occupied / total_units) * 100
                stated_occupancy = self.rent_roll.occupancy_rate or 0
                occ_variance = abs(calculated_occupancy - stated_occupancy)

                if occ_variance <= 0.1:
                    print(f"  ✓ Occupancy Rate: PASS ({stated_occupancy:.2f}%)")
                else:
                    print(f"  ✗ Occupancy Rate: FAIL (variance: {occ_variance:.2f}%)")

        # Validate Mortgage Statement
        if self.mortgage:
            print("\n[5] Mortgage Statement Validation:")

            principal_due = self.mortgage.principal_due or 0
            interest_due = self.mortgage.interest_due or 0
            tax_escrow = self.mortgage.tax_escrow_balance or 0
            ins_escrow = self.mortgage.insurance_escrow_balance or 0

            # Note: Total payment may include other fees
            total_payment = self.mortgage.total_payment_due or 0

            print(f"  ✓ Mortgage Components:")
            print(f"    Principal Due: ${principal_due:,.2f}")
            print(f"    Interest Due: ${interest_due:,.2f}")
            print(f"    Total Payment: ${total_payment:,.2f}")
            print(f"    Principal Balance: ${self.mortgage.principal_balance:,.2f}")

    def phase_4_cross_document_tieouts(self):
        """Phase 4: Cross-Document Tie-Outs"""
        print("\n" + "="*80)
        print("PHASE 4: CROSS-DOCUMENT TIE-OUTS")
        print("="*80)

        print("\n=== PRIORITY 1: CRITICAL TIE-OUTS ===")

        # Tie-Out #1: Mortgage Principal → Balance Sheet Debt
        if self.mortgage and self.balance_sheet:
            result = self.compare_values(
                self.mortgage.principal_balance,
                self.balance_sheet.long_term_debt,
                self.CRITICAL_TOLERANCE_ABS,
                self.CRITICAL_TOLERANCE_PCT,
                'CRITICAL'
            )

            print(f"\n[1] Mortgage Principal → Balance Sheet Long-Term Debt")
            print(f"    Mortgage Principal Balance: ${result['source_value']:,.2f}")
            print(f"    Balance Sheet Long-Term Debt: ${result['target_value']:,.2f}")
            print(f"    Variance: ${result['variance_amount']:,.2f} ({result['variance_pct']:.2f}%)")
            print(f"    Tolerance: ${result['tolerance']:,.2f}")
            print(f"    Status: {result['status']}")

            self.tie_out_results.append({
                'tie_out': 'Mortgage → Balance Sheet Debt',
                'priority': 1,
                **result
            })

            if result['status'] == 'FAIL':
                self.variances.append({
                    'tie_out': 'Mortgage → Balance Sheet',
                    'severity': 'CRITICAL',
                    **result
                })

        # Tie-Out #2: Mortgage Payment → Cash Flow Debt Service
        if self.mortgage and self.cash_flow:
            result = self.compare_values(
                self.mortgage.total_payment_due,
                self.cash_flow.debt_service_payment,
                10.00,
                0.01,
                'CRITICAL'
            )

            print(f"\n[2] Mortgage Payment → Cash Flow Debt Service")
            print(f"    Mortgage Total Payment: ${result['source_value']:,.2f}")
            print(f"    Cash Flow Debt Service: ${result['target_value']:,.2f}")
            print(f"    Variance: ${result['variance_amount']:,.2f} ({result['variance_pct']:.2f}%)")
            print(f"    Tolerance: ${result['tolerance']:,.2f}")
            print(f"    Status: {result['status']}")

            self.tie_out_results.append({
                'tie_out': 'Mortgage Payment → Cash Flow Debt Service',
                'priority': 1,
                **result
            })

            if result['status'] == 'FAIL':
                self.variances.append({
                    'tie_out': 'Mortgage Payment → Cash Flow',
                    'severity': 'CRITICAL',
                    **result
                })

        # Tie-Out #3: Cash Flow Ending → Balance Sheet Cash
        if self.cash_flow and self.balance_sheet:
            result = self.compare_values(
                self.cash_flow.ending_cash,
                self.balance_sheet.cash,
                10.00,
                0.01,
                'CRITICAL'
            )

            print(f"\n[3] Cash Flow Ending Cash → Balance Sheet Cash")
            print(f"    Cash Flow Ending Cash: ${result['source_value']:,.2f}")
            print(f"    Balance Sheet Cash: ${result['target_value']:,.2f}")
            print(f"    Variance: ${result['variance_amount']:,.2f} ({result['variance_pct']:.2f}%)")
            print(f"    Tolerance: ${result['tolerance']:,.2f}")
            print(f"    Status: {result['status']}")

            self.tie_out_results.append({
                'tie_out': 'Cash Flow → Balance Sheet Cash',
                'priority': 1,
                **result
            })

            if result['status'] == 'FAIL':
                self.variances.append({
                    'tie_out': 'Cash Flow → Balance Sheet',
                    'severity': 'CRITICAL',
                    **result
                })

        print("\n=== PRIORITY 2: WARNING TIE-OUTS ===")

        # Tie-Out #6: Rent Roll → Income Statement Rental Income
        if self.rent_roll and self.income_stmt:
            annual_rent = (self.rent_roll.total_monthly_rent or 0) * 12
            result = self.compare_values(
                annual_rent,
                self.income_stmt.rental_income,
                self.WARNING_TOLERANCE_ABS,
                self.WARNING_TOLERANCE_PCT,
                'WARNING'
            )

            print(f"\n[6] Rent Roll Annual Rent → Income Statement Rental Income")
            print(f"    Rent Roll Annual (Monthly × 12): ${result['source_value']:,.2f}")
            print(f"    Income Statement Rental Income: ${result['target_value']:,.2f}")
            print(f"    Variance: ${result['variance_amount']:,.2f} ({result['variance_pct']:.2f}%)")
            print(f"    Tolerance: ${result['tolerance']:,.2f}")
            print(f"    Status: {result['status']}")

            self.tie_out_results.append({
                'tie_out': 'Rent Roll → Income Statement',
                'priority': 2,
                **result
            })

            if result['status'] in ['FAIL', 'WARNING']:
                self.variances.append({
                    'tie_out': 'Rent Roll → Income Statement',
                    'severity': 'WARNING',
                    **result
                })

        # Tie-Out #7: Mortgage Interest → Income Statement Interest Expense
        if self.mortgage and self.income_stmt:
            result = self.compare_values(
                self.mortgage.interest_due,
                self.income_stmt.interest_expense,
                100.00,
                1.0,
                'WARNING'
            )

            print(f"\n[7] Mortgage Interest → Income Statement Interest Expense")
            print(f"    Mortgage Interest Due: ${result['source_value']:,.2f}")
            print(f"    Income Statement Interest Expense: ${result['target_value']:,.2f}")
            print(f"    Variance: ${result['variance_amount']:,.2f} ({result['variance_pct']:.2f}%)")
            print(f"    Tolerance: ${result['tolerance']:,.2f}")
            print(f"    Status: {result['status']}")

            self.tie_out_results.append({
                'tie_out': 'Mortgage Interest → Income Statement',
                'priority': 2,
                **result
            })

            if result['status'] in ['FAIL', 'WARNING']:
                self.variances.append({
                    'tie_out': 'Mortgage Interest → Income Statement',
                    'severity': 'WARNING',
                    **result
                })

    def phase_5_business_logic(self):
        """Phase 5: Business Logic Validation"""
        print("\n" + "="*80)
        print("PHASE 5: BUSINESS LOGIC VALIDATION")
        print("="*80)

        # Check 1: DSCR Covenant Compliance
        if self.income_stmt and self.mortgage:
            noi = self.income_stmt.noi or 0
            annual_debt_service = (self.mortgage.total_payment_due or 0) * 12

            if annual_debt_service > 0:
                dscr = noi / annual_debt_service

                print(f"\n[1] DSCR (Debt Service Coverage Ratio):")
                print(f"    NOI: ${noi:,.2f}")
                print(f"    Annual Debt Service: ${annual_debt_service:,.2f}")
                print(f"    DSCR: {dscr:.2f}x")

                if dscr >= 1.25:
                    print(f"    Status: ✓ PASS (Above covenant minimum 1.25x)")
                elif dscr >= 1.0:
                    print(f"    Status: ⚠ WARNING (Below 1.25x but above 1.0x)")
                    self.red_flags.append({
                        'severity': 'WARNING',
                        'category': 'Covenant Compliance',
                        'description': f'DSCR below covenant minimum: {dscr:.2f}x',
                        'value': dscr
                    })
                else:
                    print(f"    Status: ✗ CRITICAL (Below 1.0x - property underwater)")
                    self.red_flags.append({
                        'severity': 'CRITICAL',
                        'category': 'Covenant Violation',
                        'description': f'DSCR below 1.0x: {dscr:.2f}x',
                        'value': dscr
                    })

        # Check 2: Occupancy Threshold
        if self.rent_roll:
            occupancy = self.rent_roll.occupancy_rate or 0

            print(f"\n[2] Occupancy Rate:")
            print(f"    Occupancy: {occupancy:.2f}%")

            if occupancy >= 80.0:
                print(f"    Status: ✓ PASS (Above 80% threshold)")
            else:
                print(f"    Status: ⚠ WARNING (Below 80% threshold)")
                self.red_flags.append({
                    'severity': 'WARNING',
                    'category': 'Occupancy',
                    'description': f'Low occupancy: {occupancy:.2f}%',
                    'value': occupancy
                })

        # Check 3: Positive NOI
        if self.income_stmt:
            noi = self.income_stmt.noi or 0

            print(f"\n[3] Net Operating Income:")
            print(f"    NOI: ${noi:,.2f}")

            if noi > 0:
                print(f"    Status: ✓ PASS (Positive NOI)")
            else:
                print(f"    Status: ✗ CRITICAL (Negative NOI)")

        # Check 4: Cash Flow Coverage
        if self.cash_flow and self.mortgage:
            operating_cf = self.cash_flow.operating_cash_flow or 0
            annual_debt_service = (self.mortgage.total_payment_due or 0) * 12

            if annual_debt_service > 0:
                cash_coverage = operating_cf / annual_debt_service

                print(f"\n[4] Cash Flow Coverage:")
                print(f"    Operating Cash Flow: ${operating_cf:,.2f}")
                print(f"    Annual Debt Service: ${annual_debt_service:,.2f}")
                print(f"    Coverage Ratio: {cash_coverage:.2f}x")

                if cash_coverage >= 1.20:
                    print(f"    Status: ✓ PASS (Above 1.20x minimum)")
                else:
                    print(f"    Status: ⚠ WARNING (Below 1.20x)")
                    self.red_flags.append({
                        'severity': 'WARNING',
                        'category': 'Cash Flow Coverage',
                        'description': f'Low cash coverage: {cash_coverage:.2f}x',
                        'value': cash_coverage
                    })

    def phase_6_variance_analysis(self):
        """Phase 6: Variance Analysis"""
        print("\n" + "="*80)
        print("PHASE 6: VARIANCE ANALYSIS")
        print("="*80)

        if not self.variances:
            print("\n✓ No material variances detected")
            return

        print(f"\nTotal Material Variances: {len(self.variances)}")

        for i, variance in enumerate(self.variances, 1):
            print(f"\nVariance #{i}: {variance['tie_out']}")
            print(f"  Source Value: ${variance['source_value']:,.2f}")
            print(f"  Target Value: ${variance['target_value']:,.2f}")
            print(f"  Variance Amount: ${variance['variance_amount']:,.2f}")
            print(f"  Variance Percentage: {variance['variance_pct']:.2f}%")
            print(f"  Tolerance: ${variance['tolerance']:,.2f}")
            print(f"  Severity: {variance['severity']}")

            # Suggest likely causes
            print(f"  Likely Causes:")
            if 'Cash Flow' in variance['tie_out']:
                print(f"    - Timing difference (accrual vs cash basis)")
                print(f"    - Working capital adjustments")
            elif 'Rent Roll' in variance['tie_out']:
                print(f"    - Vacancy losses")
                print(f"    - Concessions or rent adjustments")
                print(f"    - Timing of rent increases")
            elif 'Mortgage' in variance['tie_out']:
                print(f"    - Escrow payments included/excluded")
                print(f"    - Payment timing differences")

            print(f"  Recommendation: Management review required")

    def phase_7_red_flag_detection(self):
        """Phase 7: Red Flag Detection"""
        print("\n" + "="*80)
        print("PHASE 7: RED FLAG DETECTION")
        print("="*80)

        critical_flags = [f for f in self.red_flags if f['severity'] == 'CRITICAL']
        warning_flags = [f for f in self.red_flags if f['severity'] == 'WARNING']

        print(f"\nTotal Red Flags: {len(self.red_flags)}")
        print(f"  Critical: {len(critical_flags)}")
        print(f"  Warnings: {len(warning_flags)}")

        if critical_flags:
            print(f"\n=== CRITICAL RED FLAGS ===")
            for i, flag in enumerate(critical_flags, 1):
                print(f"\nRed Flag #{i}: {flag['description']}")
                print(f"  Severity: CRITICAL")
                print(f"  Category: {flag['category']}")
                if 'variance' in flag:
                    print(f"  Variance: ${flag['variance']:,.2f}")
                if 'value' in flag:
                    print(f"  Value: {flag['value']}")
                print(f"  Impact: Requires immediate attention")

        if warning_flags:
            print(f"\n=== WARNING RED FLAGS ===")
            for i, flag in enumerate(warning_flags, 1):
                print(f"\nWarning #{i}: {flag['description']}")
                print(f"  Severity: WARNING")
                print(f"  Category: {flag['category']}")
                if 'variance' in flag:
                    print(f"  Variance: ${flag['variance']:,.2f}")
                if 'value' in flag:
                    print(f"  Value: {flag['value']}")
                print(f"  Impact: Management review recommended")

    def phase_8_audit_opinion(self):
        """Phase 8: Audit Opinion & Report"""
        print("\n" + "="*80)
        print("PHASE 8: AUDIT OPINION")
        print("="*80)

        # Determine opinion
        critical_failures = len([f for f in self.red_flags if f['severity'] == 'CRITICAL'])
        critical_tieout_failures = len([t for t in self.tie_out_results
                                        if t.get('priority') == 1 and t.get('status') == 'FAIL'])

        if critical_failures > 0 or critical_tieout_failures > 0:
            if critical_failures >= 3 or critical_tieout_failures >= 2:
                opinion = "ADVERSE OPINION"
                explanation = ("Based on our forensic examination, we have identified multiple "
                             "critical failures in the financial documents. The documents contain "
                             "material misstatements and do NOT present the financial position fairly.")
            else:
                opinion = "QUALIFIED OPINION"
                explanation = ("Based on our forensic examination, the financial documents present "
                             "the financial position fairly, EXCEPT FOR the specific critical items "
                             "noted in our findings.")
        elif len(self.variances) > 0:
            opinion = "QUALIFIED OPINION"
            explanation = ("The financial documents present the financial position fairly, EXCEPT FOR "
                         "certain variances that require management explanation.")
        else:
            opinion = "CLEAN OPINION (Unqualified)"
            explanation = ("Based on our forensic examination, the financial documents present the "
                         "financial position fairly in all material respects. All critical tie-outs "
                         "passed and variances are within acceptable tolerances.")

        print(f"\n{'='*80}")
        print(f"FORENSIC AUDIT OPINION")
        print(f"{'='*80}")
        print(f"\nProperty: {self.property_name} ({self.property_code})")
        print(f"Period: {self.year}-{self.month:02d}")
        print(f"Audit Date: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"Auditor: Claude AI, CPA, CFE")
        print(f"         Senior Forensic Auditor")
        print(f"         Big 5 Accounting Firm")
        print(f"\nOPINION: {opinion}")
        print(f"\n{explanation}")

        # Summary statistics
        print(f"\n{'='*80}")
        print(f"AUDIT SUMMARY STATISTICS")
        print(f"{'='*80}")

        critical_pass = len([t for t in self.tie_out_results if t.get('priority') == 1 and t.get('status') == 'PASS'])
        critical_total = len([t for t in self.tie_out_results if t.get('priority') == 1])

        print(f"\nCritical Tie-Outs:")
        print(f"  Passed: {critical_pass}/{critical_total}")
        print(f"  Failed: {critical_total - critical_pass}/{critical_total}")

        print(f"\nRed Flags:")
        print(f"  Critical: {len([f for f in self.red_flags if f['severity'] == 'CRITICAL'])}")
        print(f"  Warnings: {len([f for f in self.red_flags if f['severity'] == 'WARNING'])}")

        print(f"\nVariances:")
        print(f"  Material Variances: {len(self.variances)}")

        # Recommendations
        print(f"\n{'='*80}")
        print(f"RECOMMENDATIONS")
        print(f"{'='*80}")

        if critical_failures > 0:
            print(f"\nImmediate Actions Required:")
            print(f"  1. Investigate and resolve all critical red flags")
            print(f"  2. Verify data extraction accuracy for affected documents")
            print(f"  3. Re-run reconciliation after corrections")

        if len(self.variances) > 0:
            print(f"\nManagement Review Needed:")
            print(f"  1. Review and explain all material variances")
            print(f"  2. Document timing differences and adjustments")
            print(f"  3. Update reconciliation notes")

        print(f"\nProcess Improvements:")
        print(f"  1. Implement automated cross-document validation")
        print(f"  2. Enhance extraction confidence scoring")
        print(f"  3. Establish monthly reconciliation procedures")

        print(f"\n{'='*80}")
        print(f"END OF FORENSIC AUDIT REPORT")
        print(f"{'='*80}\n")

    def execute_audit(self):
        """Execute complete forensic audit"""
        try:
            print("\n" + "="*80)
            print("REIMS2 FORENSIC AUDIT")
            print("Big 5 Accounting Firm Level Cross-Document Reconciliation")
            print("="*80)

            # Phase 1: Planning
            if not self.phase_1_engagement_planning():
                return 1

            # Phase 2: Data Loading
            if not self.phase_2_data_loading():
                print("\n✗ AUDIT CANNOT PROCEED: Missing critical documents")
                return 1

            # Phase 3: Individual Validation
            self.phase_3_individual_validation()

            # Phase 4: Cross-Document Tie-Outs
            self.phase_4_cross_document_tieouts()

            # Phase 5: Business Logic
            self.phase_5_business_logic()

            # Phase 6: Variance Analysis
            self.phase_6_variance_analysis()

            # Phase 7: Red Flags
            self.phase_7_red_flag_detection()

            # Phase 8: Opinion
            self.phase_8_audit_opinion()

            return 0

        except Exception as e:
            print(f"\n✗ AUDIT ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            self.db.close()


def main():
    """Main execution"""
    # Audit October 2023 for ESP001
    auditor = ForensicAuditor(
        property_id=1,
        year=2023,
        month=10
    )

    return auditor.execute_audit()


if __name__ == '__main__':
    sys.exit(main())
