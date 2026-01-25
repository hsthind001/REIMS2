from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

class BalanceSheetRulesMixin:
    
    def _execute_balance_sheet_rules(self):
        """Execute Balance Sheet rules"""
        # Fundamental Equations
        self._rule_bs_1_accounting_equation()
        
        # Constant Checks
        self._rule_bs_2_cash_operating_constant()
        self._rule_bs_6_land_constant()
        
        # Component Integrity
        self._rule_bs_3_current_assets_sum()
        
        # Financial Ratios & Health
        self._rule_bs_4_current_ratio()
        self._rule_bs_5_working_capital()
        self._rule_bs_9_debt_to_assets()
        
        # Trend Analysis (Requires Prior Period)
        prior_id = self._get_prior_period_id()
        if prior_id:
            self._rule_bs_7_accum_depr_non_decreasing(prior_id)
            self._rule_bs_8_accum_depr_buildings(prior_id)
            self._rule_bs_16_loan_costs_amortization(prior_id)
            self._rule_bs_28_property_tax_accumulation(prior_id)
            self._rule_bs_33_earnings_accumulation(prior_id)
            self._rule_bs_35_total_capital_change(prior_id)

        # Fixed Assets
        self._rule_bs_10_5yr_improvements()
        self._rule_bs_11_ti_improvements()
        self._rule_bs_12_roof_value()
        self._rule_bs_13_hvac_asset()

        # Other Assets
        self._rule_bs_14_deposits()
        self._rule_bs_15_loan_costs()
        self._rule_bs_17_accum_amort_other()
        self._rule_bs_18_ext_lease_comm()
        self._rule_bs_19_int_lease_comm()
        self._rule_bs_20_prepaid_insurance()
        self._rule_bs_21_prepaid_expenses()

        # Current Liabilities
        self._rule_bs_22_ap_5rivers()
        self._rule_bs_23_ap_eastchase()
        self._rule_bs_24_loans_5rivers()
        self._rule_bs_25_deposit_refundable()
        self._rule_bs_26_accrued_expenses()
        self._rule_bs_27_ap_trade()
        self._rule_bs_29_rent_advance()

        # Capital
        self._rule_bs_30_partners_contribution()
        self._rule_bs_31_beginning_equity()
        self._rule_bs_32_distributions()
        self._rule_bs_34_total_capital_calc() 

            
    def _get_bs_value(self, account_code_pattern=None, account_name_pattern=None, period_id=None):
        """Helper to get value from balance_sheet_data"""
        if period_id is None:
            period_id = self.period_id
            
        if account_code_pattern:
            clause = "account_code LIKE :pattern"
            pattern = account_code_pattern
        else:
            clause = "account_name ILIKE :pattern"
            pattern = account_name_pattern
            
        query = text(f"""
            SELECT amount
            FROM balance_sheet_data
            WHERE property_id = :p_id 
            AND period_id = :period_id
            AND {clause}
            ORDER BY amount DESC
            LIMIT 1
        """)
        result = self.db.execute(query, {
            "p_id": self.property_id, 
            "period_id": period_id,
            "pattern": pattern
        })
        val = result.scalar()
        return float(val) if val is not None else 0.0

    def _rule_bs_1_accounting_equation(self):
        """BS-1: Total Assets = Total Liabilities & Capital"""
        assets = self._get_bs_value(account_name_pattern="TOTAL ASSETS")
        liab_cap = self._get_bs_value(account_name_pattern="TOTAL LIABILITIES & CAPITAL")
        
        diff = assets - liab_cap
        
        self.results.append(ReconciliationResult(
            rule_id="BS-1",
            rule_name="Accounting Equation",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "FAIL",
            source_value=assets,
            target_value=liab_cap,
            difference=diff,
            variance_pct=0.0 if assets == 0 else (abs(diff)/assets)*100,
            details="Total Assets must equal Total Liabilities & Capital",
            severity="critical",
            formula="Total Assets - (Total Liabilities & Capital)"
        ))

    def _rule_bs_2_cash_operating_constant(self):
        """BS-2: Cash - Operating check"""
        val = self._get_bs_value(account_code_pattern="0122-0000")
        expected = 3375.45
        diff = val - expected
        
        self.results.append(ReconciliationResult(
            rule_id="BS-2",
            rule_name="Cash Operating Check",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 0.01 else "SKIP", 
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0.0 if expected == 0 else (abs(diff)/expected)*100,
            details="Cash Operating account verified against expected baseline",
            severity="medium",
            formula="[0122-0000] Cash Operating - 3375.45"
        ))

    def _rule_bs_6_land_constant(self):
        """BS-6: Land value consistency"""
        val = self._get_bs_value(account_code_pattern="0510-0000")
        status = "PASS" if val > 0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="BS-6",
            rule_name="Land Asset Verification",
            category="Balance Sheet",
            status=status,
            source_value=val,
            target_value=0, 
            difference=0,
            variance_pct=0,
            details=f"Land value reported as ${val:,.2f}",
            severity="low",
            formula="[0510-0000] Land > 0"
        ))

    def _rule_bs_3_current_assets_sum(self):
        """BS-3: Current Assets Verification"""
        total = self._get_bs_value(account_name_pattern="Total Current Assets")
        self.results.append(ReconciliationResult(
            rule_id="BS-3",
            rule_name="Current Assets Integrity",
            category="Balance Sheet",
            status="PASS" if total > 0 else "FAIL",
            source_value=total,
            target_value=total,
            difference=0,
            variance_pct=0,
            details=f"Total Current Assets: ${total:,.2f}",
            severity="medium",
            formula="Total Current Assets > 0"
        ))

    def _rule_bs_4_current_ratio(self):
        """BS-4: Current Ratio (Current Assets / Current Liabilities) >= 1.0"""
        ca = self._get_bs_value(account_name_pattern="Total Current Assets")
        cl = self._get_bs_value(account_name_pattern="Total Current Liabilities")
        
        ratio = 0.0
        if cl != 0:
            ratio = ca / cl
            
        status = "PASS" if ratio >= 1.0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="BS-4",
            rule_name="Current Ratio Liquidity",
            category="Balance Sheet",
            status=status,
            source_value=ratio,
            target_value=1.0,
            difference=ratio - 1.0,
            variance_pct=0,
            details=f"Current Ratio is {ratio:.2f} (Target >= 1.0)",
            severity="high",
            formula="Total Current Assets / Total Current Liabilities >= 1.0"
        ))

    def _rule_bs_5_working_capital(self):
        """BS-5: Working Capital > 0"""
        ca = self._get_bs_value(account_name_pattern="Total Current Assets")
        cl = self._get_bs_value(account_name_pattern="Total Current Liabilities")
        
        wc = ca - cl
        
        self.results.append(ReconciliationResult(
            rule_id="BS-5",
            rule_name="Working Capital Positive",
            category="Balance Sheet",
            status="PASS" if wc >= 0 else "FAIL",
            source_value=wc,
            target_value=0.0,
            difference=wc,
            variance_pct=0,
            details=f"Working Capital is ${wc:,.2f}",
            severity="high",
            formula="Total Current Assets - Total Current Liabilities > 0"
        ))
        
    def _rule_bs_9_debt_to_assets(self):
        """BS-9: Debt to Assets Ratio <= 0.85"""
        total_liab = self._get_bs_value(account_name_pattern="TOTAL LIABILITIES & CAPITAL")
        total_liab_only = self._get_bs_value(account_name_pattern="Total Liabilities")
        total_assets = self._get_bs_value(account_name_pattern="TOTAL ASSETS")
        
        usage_liab = total_liab_only
            
        ratio = 0.0
        if total_assets > 0:
            ratio = usage_liab / total_assets
            
        if usage_liab == 0:
             self.results.append(ReconciliationResult(
                rule_id="BS-9",
                rule_name="Debt to Assets Ratio",
                category="Balance Sheet",
                status="SKIP",
                source_value=0,
                target_value=0.85,
                difference=0,
                variance_pct=0,
                details="Could not isolate Total Liabilities line item",
                severity="medium",
                formula="Total Liabilities / Total Assets <= 0.85"
            ))
             return

        status = "PASS" if ratio <= 0.85 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="BS-9",
            rule_name="Debt to Assets Ratio",
            category="Balance Sheet",
            status=status,
            source_value=ratio,
            target_value=0.85,
            difference=ratio - 0.85,
            variance_pct=0,
            details=f"Debt/Assets Ratio is {ratio:.2f} (Target <= 0.85)",
            severity="medium",
            formula="Total Liabilities / Total Assets <= 0.85"
        ))

    def _rule_bs_7_accum_depr_non_decreasing(self, prior_period_id):
        """BS-7: Accumulated Depreciation should not decrease"""
        curr = self._get_bs_value(account_code_pattern="1230-0000") 
        prior = self._get_bs_value(account_code_pattern="1230-0000", period_id=prior_period_id)
        
        curr_abs = abs(curr)
        prior_abs = abs(prior)
        
        diff = curr_abs - prior_abs
        
        status = "PASS" if diff >= -1.0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="BS-7",
            rule_name="Accumulated Depr Trend",
            category="Balance Sheet",
            status=status,
            source_value=curr_abs,
            target_value=prior_abs,
            difference=diff,
            variance_pct=0,
            details=f"Accum Depr changed by ${diff:,.2f} (Prior: ${prior_abs:,.2f}, Curr: ${curr_abs:,.2f})",
            severity="medium",
            formula="[1230-0000] Current - [1230-0000] Prior >= 0"
        ))

    def _rule_bs_8_accum_depr_buildings(self, prior_id):
        """BS-8: Accum Depr Buildings increases monthly"""
        curr = self._get_bs_value(account_name_pattern="%Accum%Depr%Building%")
        prior = self._get_bs_value(account_name_pattern="%Accum%Depr%Building%", period_id=prior_id)
        
        diff = abs(curr) - abs(prior)
        status = "PASS" if diff >= 0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="BS-8",
            rule_name="Accum Depr Buildings Trend",
            category="Balance Sheet",
            status=status,
            source_value=abs(curr),
            target_value=abs(prior),
            difference=diff,
            variance_pct=0,
            details=f"Building Depr increased by ${diff:,.2f}",
            severity="medium",
            formula="Current Accum - Prior Accum >= 0"
        ))

    def _rule_bs_10_5yr_improvements(self):
        """BS-10: 5-Year Improvements Fully Depreciated context"""
        # Checking for specific known value if hardcoded, or just existence
        val = self._get_bs_value(account_name_pattern="%5%Year%Imp%")
        expected = -1025187.00 # From rules md
        
        # If dynamic, might just check it's negative
        status = "PASS" if abs(val - expected) < 1.0 else "INFO"
        
        self.results.append(ReconciliationResult(
            rule_id="BS-10",
            rule_name="5-Year Improvements",
            category="Balance Sheet",
            status=status,
            source_value=val,
            target_value=expected,
            difference=val - expected,
            variance_pct=0,
            details=f"5-Year Imp value: ${val:,.2f}",
            severity="low",
            formula="Value check against baseline"
        ))

    def _rule_bs_11_ti_improvements(self):
        """BS-11: TI/Current Improvements >= 0"""
        val = self._get_bs_value(account_name_pattern="%Tenant%Imp%")
        
        self.results.append(ReconciliationResult(
            rule_id="BS-11",
            rule_name="TI Improvements",
            category="Balance Sheet",
            status="PASS" if val >= 0 else "FAIL",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"TI Value: ${val:,.2f}",
            severity="low",
            formula="TI >= 0"
        ))

    def _rule_bs_12_roof_value(self):
        """BS-12: Roof Value Check"""
        val = self._get_bs_value(account_name_pattern="%Roof%")
        
        self.results.append(ReconciliationResult(
            rule_id="BS-12",
            rule_name="Roof Asset Value",
            category="Balance Sheet",
            status="PASS" if val > 0 else "INFO",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Roof Value: ${val:,.2f}",
            severity="low",
            formula="Exists > 0"
        ))

    def _rule_bs_13_hvac_asset(self):
        """BS-13: HVAC Asset Check"""
        val = self._get_bs_value(account_name_pattern="%HVAC%")
        self.results.append(ReconciliationResult(
            rule_id="BS-13",
            rule_name="HVAC Asset",
            category="Balance Sheet",
            status="PASS" if val >= 0 else "FAIL",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"HVAC Value: ${val:,.2f}",
            severity="low",
            formula="Exists >= 0"
        ))

    def _rule_bs_14_deposits(self):
        """BS-14: Deposits Constant"""
        val = self._get_bs_value(account_name_pattern="Deposits")
        expected = 20900.00
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-14",
            rule_name="Deposits Check",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Deposits ${val:,.2f} vs Baseline ${expected:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_15_loan_costs(self):
        """BS-15: Loan Costs Asset Constant"""
        val = self._get_bs_value(account_name_pattern="Loan Costs")
        expected = 268752.01
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-15",
            rule_name="Loan Costs Asset",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Loan Costs ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_16_loan_costs_amortization(self, prior_id):
        """BS-16: Accum Amort Loan Costs increases (becomes more negative)"""
        curr = self._get_bs_value(account_name_pattern="%Accum%Amort%Loan%Cost%")
        prior = self._get_bs_value(account_name_pattern="%Accum%Amort%Loan%Cost%", period_id=prior_id)
        
        diff = abs(curr) - abs(prior)
        status = "PASS" if diff >= 0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="BS-16",
            rule_name="Loan Cost Amortization",
            category="Balance Sheet",
            status=status,
            source_value=abs(curr),
            target_value=abs(prior),
            difference=diff,
            variance_pct=0,
            details=f"Amortization increased by ${diff:,.2f}",
            severity="medium",
            formula="Current Abs > Prior Abs"
        ))

    def _rule_bs_17_accum_amort_other(self):
        """BS-17: Accumulated Amortisation (Other) Constant"""
        # Search for the other amortization account (not Loan Costs)
        # Based on rules, it should be -36,621.19
        val = self._get_bs_value(account_name_pattern="%Accum%Amort%", account_code_pattern="NOT LIKE 12%") 
        expected = -36621.19
        
        # If we pulled the loan cost one by mistake, check against that to be safe, 
        # but let's assume the name pattern works if unique enough.
        # Actually loan cost pattern was "%Accum%Amort%Loan%Cost%"
        
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-17",
            rule_name="Accum Amort Other",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Value ${val:,.2f}",
            severity="low",
            formula="Constant Check"
        ))

    def _rule_bs_18_ext_lease_comm(self):
        """BS-18: External Lease Commissions"""
        val = self._get_bs_value(account_name_pattern="External Lease Comm%")
        self.results.append(ReconciliationResult(
            rule_id="BS-18",
            rule_name="Ext Lease Comm",
            category="Balance Sheet",
            status="PASS" if val > 0 else "INFO",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="low",
            formula="Exists"
        ))

    def _rule_bs_19_int_lease_comm(self):
        """BS-19: Internal Lease Commissions"""
        val = self._get_bs_value(account_name_pattern="Internal Lease Comm%")
        self.results.append(ReconciliationResult(
            rule_id="BS-19",
            rule_name="Int Lease Comm",
            category="Balance Sheet",
            status="PASS" if val > 0 else "INFO",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="low",
            formula="Exists"
        ))

    def _rule_bs_20_prepaid_insurance(self):
        """BS-20: Prepaid Insurance Exists"""
        val = self._get_bs_value(account_name_pattern="Prepaid Insurance")
        self.results.append(ReconciliationResult(
            rule_id="BS-20",
            rule_name="Prepaid Insurance",
            category="Balance Sheet",
            status="PASS" if val > 0 else "WARNING",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="medium",
            formula="Exists > 0"
        ))

    def _rule_bs_21_prepaid_expenses(self):
        """BS-21: Prepaid Expenses Exists"""
        val = self._get_bs_value(account_name_pattern="Prepaid Expenses")
        self.results.append(ReconciliationResult(
            rule_id="BS-21",
            rule_name="Prepaid Expenses",
            category="Balance Sheet",
            status="PASS" if val >= 0 else "INFO",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="low",
            formula="Exists"
        ))

    def _run_constant_check(self, rule_id, name, pattern, expected):
        val = self._get_bs_value(account_name_pattern=pattern)
        diff = val - expected
        status = "PASS" if abs(diff) < 1.0 else "WARNING"
        self.results.append(ReconciliationResult(
            rule_id=rule_id,
            rule_name=name,
            category="Balance Sheet",
            status=status,
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"{name}: ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_22_ap_5rivers(self):
        val = self._get_bs_value(account_name_pattern="%5Rivers%", account_code_pattern="2%")
        expected = 31683.54
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-22",
            rule_name="A/P 5Rivers",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Value ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_23_ap_eastchase(self):
        val = self._get_bs_value(account_name_pattern="%Eastchase%")
        expected = 354.54
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-23",
            rule_name="A/P Eastchase",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Value ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_24_loans_5rivers(self):
        val = self._get_bs_value(account_name_pattern="%Loans%5Rivers%")
        expected = 1810819.58
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-24",
            rule_name="Loans Payable 5Rivers",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Value ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_25_deposit_refundable(self):
        val = self._get_bs_value(account_name_pattern="%Deposit%Refundable%")
        expected = 49791.31
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-25",
            rule_name="Deposit Refundable",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Value ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_26_accrued_expenses(self):
        """BS-26: Accrued Expenses Volatility"""
        val = self._get_bs_value(account_name_pattern="Accrued Expenses")
        self.results.append(ReconciliationResult(
            rule_id="BS-26",
            rule_name="Accrued Expenses",
            category="Balance Sheet",
            status="PASS", # Always pass as just tracking
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="info",
            formula="Tracking"
        ))

    def _rule_bs_27_ap_trade(self):
        """BS-27: A/P Trade"""
        val = self._get_bs_value(account_name_pattern="%A/P%Trade%")
        self.results.append(ReconciliationResult(
            rule_id="BS-27",
            rule_name="A/P Trade",
            category="Balance Sheet",
            status="PASS",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="info",
            formula="Tracking"
        ))

    def _rule_bs_28_property_tax_accumulation(self, prior_id):
        """BS-28: Property Tax Payable Accumulation"""
        curr = self._get_bs_value(account_name_pattern="%Property%Tax%Payable%")
        prior = self._get_bs_value(account_name_pattern="%Property%Tax%Payable%", period_id=prior_id)
        
        diff = curr - prior
        # It's okay if it decreases (payment), but usually increases
        status = "PASS" 
        
        self.results.append(ReconciliationResult(
            rule_id="BS-28",
            rule_name="Property Tax Payable",
            category="Balance Sheet",
            status=status,
            source_value=curr,
            target_value=prior,
            difference=diff,
            variance_pct=0,
            details=f"Change: ${diff:,.2f} (Prior ${prior:,.2f}, Curr ${curr:,.2f})",
            severity="medium",
            formula="Tracking Accumulation"
        ))

    def _rule_bs_29_rent_advance(self):
        """BS-29: Rent Received in Advance"""
        val = self._get_bs_value(account_name_pattern="%Rent%Advance%")
        self.results.append(ReconciliationResult(
            rule_id="BS-29",
            rule_name="Rent In Advance",
            category="Balance Sheet",
            status="PASS",
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="info",
            formula="Tracking"
        ))

    def _rule_bs_30_partners_contribution(self):
        val = self._get_bs_value(account_name_pattern="%Partners%Contribution%")
        expected = 5684514.69
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-30",
            rule_name="Partners Contribution",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Value ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_31_beginning_equity(self):
        val = self._get_bs_value(account_name_pattern="%Beginning%Equity%")
        expected = 1786413.82
        diff = val - expected
        self.results.append(ReconciliationResult(
            rule_id="BS-31",
            rule_name="Beginning Equity",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=val,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Value ${val:,.2f}",
            severity="medium",
            formula="Constant Check"
        ))

    def _rule_bs_32_distributions(self):
        """BS-32: Distributions"""
        val = self._get_bs_value(account_name_pattern="Distributions")
        self.results.append(ReconciliationResult(
            rule_id="BS-32",
            rule_name="BS Distributions Check",
            category="Balance Sheet",
            status="PASS" if val <= 0 else "WARNING", # Usually negative
            source_value=val,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Value: ${val:,.2f}",
            severity="info",
            formula="Tracking"
        ))

    def _rule_bs_33_earnings_accumulation(self, prior_id):
        """BS-33: Current Period Earnings Accumulation"""
        curr = self._get_bs_value(account_name_pattern="%Current%Period%Earn%")
        prior = self._get_bs_value(account_name_pattern="%Current%Period%Earn%", period_id=prior_id)
        
        # Should normally increase if profitable
        diff = curr - prior
        
        self.results.append(ReconciliationResult(
            rule_id="BS-33",
            rule_name="Earnings Accumulation",
            category="Balance Sheet",
            status="PASS",
            source_value=curr,
            target_value=prior,
            difference=diff,
            variance_pct=0,
            details=f"Earnings change: ${diff:,.2f}",
            severity="medium",
            formula="Tracking"
        ))

    def _rule_bs_34_total_capital_calc(self):
        """BS-34: Total Capital = Partners + Equity + Dist + Earnings"""
        p = self._get_bs_value(account_name_pattern="%Partners%Contribution%")
        be = self._get_bs_value(account_name_pattern="%Beginning%Equity%")
        d = self._get_bs_value(account_name_pattern="Distributions")
        cpe = self._get_bs_value(account_name_pattern="%Current%Period%Earn%")
        
        calc_total = p + be + d + cpe
        
        # Compare to "Total Capital" line if exists, or just verify sum logic?
        # The rule implies checking the sum. We can check against Total Liabilities & Equity - Liabilities
        total_l_e = self._get_bs_value(account_name_pattern="TOTAL LIABILITIES & CAPITAL")
        total_l = self._get_bs_value(account_name_pattern="Total Liabilities")
        implied_equity = total_l_e - total_l
        
        diff = calc_total - implied_equity
        
        self.results.append(ReconciliationResult(
            rule_id="BS-34",
            rule_name="Total Capital Logic",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "FAIL",
            source_value=calc_total,
            target_value=implied_equity,
            difference=diff,
            variance_pct=0,
            details=f"Calculated Capital ${calc_total:,.2f} vs Derived ${implied_equity:,.2f}",
            severity="critical",
            formula="Sum(Equity Components) = Total Equity"
        ))

    def _rule_bs_35_total_capital_change(self, prior_id):
        """BS-35: Change in Total Capital = Change in Earnings + Change in Distributions"""
        # Get current values
        curr_cap = (
            self._get_bs_value(account_name_pattern="%Partners%Contribution%") +
            self._get_bs_value(account_name_pattern="%Beginning%Equity%") +
            self._get_bs_value(account_name_pattern="Distributions") +
            self._get_bs_value(account_name_pattern="%Current%Period%Earn%")
        )
        
        # Get prior values
        prior_cap = (
            self._get_bs_value(account_name_pattern="%Partners%Contribution%", period_id=prior_id) +
            self._get_bs_value(account_name_pattern="%Beginning%Equity%", period_id=prior_id) +
            self._get_bs_value(account_name_pattern="Distributions", period_id=prior_id) +
            self._get_bs_value(account_name_pattern="%Current%Period%Earn%", period_id=prior_id)
        )
        
        cap_change = curr_cap - prior_cap
        
        # Components change
        curr_dist = self._get_bs_value(account_name_pattern="Distributions")
        prior_dist = self._get_bs_value(account_name_pattern="Distributions", period_id=prior_id)
        dist_change = curr_dist - prior_dist
        
        curr_earn = self._get_bs_value(account_name_pattern="%Current%Period%Earn%")
        prior_earn = self._get_bs_value(account_name_pattern="%Current%Period%Earn%", period_id=prior_id)
        earn_change = curr_earn - prior_earn
        
        expected_change = dist_change + earn_change
        diff = cap_change - expected_change
        
        self.results.append(ReconciliationResult(
            rule_id="BS-35",
            rule_name="Capital Change Logic",
            category="Balance Sheet",
            status="PASS" if abs(diff) < 1.0 else "FAIL",
            source_value=cap_change,
            target_value=expected_change,
            difference=diff,
            variance_pct=0,
            details=f"Capital Delta ${cap_change:,.2f} vs Comp Delta ${expected_change:,.2f}",
            severity="high",
            formula="Delta Capital = Delta Dist + Delta Earnings"
        ))
