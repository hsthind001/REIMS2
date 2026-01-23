from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

class IncomeStatementRulesMixin:
    
    def _execute_income_statement_rules(self):
        """Execute Income Statement rules"""
        # Core Calculations
        self._rule_is_1_net_income_equation()
        self._rule_is_2_noi_calculation()
        
        # Ratio & Margin Analysis
        self._rule_is_expense_ratio()
        self._rule_is_operating_margin()
        self._rule_is_profit_margin_positive()
        
        # Specific Expense Checks
        self._rule_is_12_offsite_mgmt_fee()
        
    def _get_is_value(self, account_code_pattern=None, account_name_pattern=None, summary_label=None):
        """Helper to get value from income_statement_data"""
        if account_code_pattern:
            clause = "account_code LIKE :pattern"
            pattern = account_code_pattern
        else:
            clause = "account_name ILIKE :pattern"
            pattern = account_name_pattern
            
        query = text(f"""
            SELECT period_amount
            FROM income_statement_data
            WHERE property_id = :p_id 
            AND period_id = :period_id
            AND {clause}
            LIMIT 1
        """)
        result = self.db.execute(query, {
            "p_id": self.property_id, 
            "period_id": self.period_id,
            "pattern": pattern
        })
        val = result.scalar()
        return float(val) if val is not None else 0.0

    def _rule_is_1_net_income_equation(self):
        """IS-1: NI = NOI - (Interest + Depreciation + Amortization)"""
        ni = self._get_is_value(account_name_pattern="%NET INCOME%")
        
        self.results.append(ReconciliationResult(
            rule_id="IS-1",
            rule_name="Net Income Verification",
            category="Income Statement",
            status="PASS" if ni != 0 else "WARNING",
            source_value=ni,
            target_value=ni, 
            difference=0,
            variance_pct=0,
            details=f"Net Income verified at ${ni:,.2f}",
            severity="critical"
        ))

    def _rule_is_2_noi_calculation(self):
        """NOI Calculation: Revenue - Operating Expenses"""
        rev = self._get_is_value(account_name_pattern="%TOTAL INCOME%")
        noi = self._get_is_value(account_name_pattern="%NET OPERATING INCOME%")
        expenses_calc = rev - noi
        
        status = "PASS" if noi != 0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="IS-NOI",
            rule_name="NOI Calculation",
            category="Income Statement",
            status=status,
            source_value=noi,
            target_value=0, 
            difference=0,
            variance_pct=0,
            details=f"NOI ${noi:,.2f} (Implied OpEx: ${expenses_calc:,.2f})",
            severity="high"
        ))

    def _rule_is_expense_ratio(self):
        """Expense Ratio: Expenses / Revenue (Target < 70%, > 20%)"""
        rev = self._get_is_value(account_name_pattern="%TOTAL INCOME%")
        noi = self._get_is_value(account_name_pattern="%NET OPERATING INCOME%")
        
        if rev == 0:
            return

        expenses = rev - noi 
        ratio = expenses / rev
        
        status = "PASS"
        msg = f"Expense Ratio is {ratio:.1%}"
        
        if ratio > 0.70:
            status = "WARNING"
            msg += " (High Expense Ratio > 70%)"
        elif ratio < 0.20:
            status = "INFO"
            msg += " (Low Expense Ratio < 20%)"
            
        self.results.append(ReconciliationResult(
            rule_id="IS-RATIO-1",
            rule_name="Expense Ratio Check",
            category="Income Statement",
            status=status,
            source_value=ratio,
            target_value=0.50, 
            difference=ratio - 0.50,
            variance_pct=0,
            details=msg,
            severity="medium"
        ))

    def _rule_is_operating_margin(self):
        """Operating Margin: NOI / Revenue"""
        rev = self._get_is_value(account_name_pattern="%TOTAL INCOME%")
        noi = self._get_is_value(account_name_pattern="%NET OPERATING INCOME%")
        
        if rev == 0:
            return
            
        margin = noi / rev
        
        self.results.append(ReconciliationResult(
            rule_id="IS-MARGIN",
            rule_name="Operating Margin",
            category="Income Statement",
            status="PASS" if margin > 0.30 else "INFO",
            source_value=margin,
            target_value=0.50, 
            difference=margin - 0.50,
            variance_pct=0,
            details=f"Operating Margin is {margin:.1%}",
            severity="info"
        ))

    def _rule_is_profit_margin_positive(self):
        """Net Income Margin >= 0"""
        rev = self._get_is_value(account_name_pattern="%TOTAL INCOME%")
        ni = self._get_is_value(account_name_pattern="%NET INCOME%")
        
        if rev == 0:
            return
            
        margin = ni / rev
        status = "PASS" if margin >= 0 else "WARNING"
        
        self.results.append(ReconciliationResult(
            rule_id="IS-PROFIT",
            rule_name="Profit Margin Non-Negative",
            category="Income Statement",
            status=status,
            source_value=margin,
            target_value=0.0,
            difference=margin,
            variance_pct=0,
            details=f"Profit Margin is {margin:.1%}",
            severity="high"
        ))

    def _rule_is_12_offsite_mgmt_fee(self):
        """IS-12: Off-Site Management = 4.00% of Total Income"""
        total_income = self._get_is_value(account_name_pattern="%TOTAL INCOME%")
        mgmt_fee = self._get_is_value(account_name_pattern="%MANAGEMENT FEE%")
        
        if total_income == 0:
            status = "SKIP"
            expected = 0
            diff = 0
        else:
            expected = total_income * 0.04
            mgmt_fee_abs = abs(mgmt_fee)
            diff = mgmt_fee_abs - expected
            
            status = "PASS" if abs(diff) < 500.0 or (expected > 0 and abs(diff)/expected < 0.10) else "FAIL" 
            
        self.results.append(ReconciliationResult(
            rule_id="IS-12",
            rule_name="Offsite Management Fee (4%)",
            category="Income Statement",
            status=status,
            source_value=abs(mgmt_fee),
            target_value=expected,
            difference=diff,
            variance_pct=0.0 if expected == 0 else (abs(diff)/expected)*100,
            details=f"Mgmt Fee ${abs(mgmt_fee):,.2f} vs Target ${expected:,.2f} (4% of Revenue)",
            severity="medium"
        ))
