from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

class ThreeStatementRulesMixin:
    
    def _execute_three_statement_rules(self):
        """Execute Three-Statement Integration rules"""
        # Critical Tie-Outs
        self._rule_3s_3_net_income_to_equity()
        self._rule_3s_8_cash_flow_reconciliation()
        
        # Complex Flows
        self._rule_3s_5_depreciation_three_way()
        self._rule_3s_1_cash_balance_check()
        
    def _rule_3s_3_net_income_to_equity(self):
        """3S-3: IS Net Income matches BS Current Period Earnings change"""
        ni = self._get_is_value(account_name_pattern="%NET INCOME%")
        bs_earnings = self._get_bs_value(account_name_pattern="%CURRENT PERIOD EARNINGS%")
        
        if bs_earnings == 0 and ni != 0:
             prior_id = self._get_prior_period_id()
             if prior_id:
                 re_curr = self._get_bs_value(account_name_pattern="%RETAINED EARNINGS%")
                 re_prior = self._get_bs_value(account_name_pattern="%RETAINED EARNINGS%", period_id=prior_id)
                 earnings_change = re_curr - re_prior
                 
                 diff = earnings_change - ni
                 status = "PASS" if abs(diff) < 1.0 else "WARNING"
                 
                 self.results.append(ReconciliationResult(
                    rule_id="3S-RE-1",
                    rule_name="Net Income to RE Change",
                    category="Three-Statement",
                    status=status,
                    source_value=ni,
                    target_value=earnings_change,
                    difference=diff,
                    variance_pct=0,
                    details=f"Net Income vs RE Change (Prior ${re_prior:,.0f} -> Curr ${re_curr:,.0f})",
                    severity="high"
                ))
                 return

        diff = bs_earnings - ni
        status = "PASS" if abs(diff) < 1.0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="3S-3",
            rule_name="Net Income Logic",
            category="Three-Statement",
            status=status,
            source_value=ni,
            target_value=bs_earnings,
            difference=diff,
            variance_pct=0,
            details=f"IS Net Income ${ni:,.2f} vs BS Earnings ${bs_earnings:,.2f}",
            severity="critical"
        ))

    def _rule_3s_8_cash_flow_reconciliation(self):
        """3S-8/CF-2: Cash Flow Net Change matches Balance Sheet Cash Change"""
        cf_net = self._get_cf_value(account_name_pattern="%NET CHANGE%CASH%")
        
        bs_cash_curr = self._get_bs_value(account_name_pattern="%TOTAL CASH%") 
        if bs_cash_curr == 0:
             bs_cash_curr = self._get_bs_value(account_code_pattern="01%") 
             if bs_cash_curr == 0:
                 bs_cash_curr = self._get_bs_value(account_name_pattern="%CASH%")

        prior_id = self._get_prior_period_id()
        if not prior_id:
            self.results.append(ReconciliationResult(
                rule_id="3S-8",
                rule_name="Cash Flow Recon",
                category="Three-Statement",
                status="SKIP",
                source_value=cf_net,
                target_value=0,
                difference=0,
                variance_pct=0,
                details="No prior period for BS comparison",
                severity="critical"
            ))
            return
            
        bs_cash_prior = self._get_bs_value(account_name_pattern="%CASH%", period_id=prior_id)
        
        bs_change = bs_cash_curr - bs_cash_prior
        diff = cf_net - bs_change
        
        status = "PASS" if abs(diff) < 1.0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="3S-8",
            rule_name="Cash Flow Recon (BS Delta)",
            category="Three-Statement",
            status=status,
            source_value=cf_net,
            target_value=bs_change,
            difference=diff,
            variance_pct=0,
            details=f"CF Net Change ${cf_net:,.2f} vs BS Cash Change ${bs_change:,.2f}",
            severity="critical"
        ))

    def _rule_3s_5_depreciation_three_way(self):
        """3S-5: Depreciation Three-Way Match"""
        is_depr = self._get_is_value(account_name_pattern="%DEPRECIATION%")
        cf_depr = self._get_cf_value(account_name_pattern="%DEPRECIATION%", category="Operating")
        
        prior_id = self._get_prior_period_id()
        bs_diff = 0
        if prior_id:
            curr_accum = self._get_bs_value(account_name_pattern="%ACCUM%DEPR%")
            prior_accum = self._get_bs_value(account_name_pattern="%ACCUM%DEPR%", period_id=prior_id)
            bs_diff = abs(curr_accum - prior_accum) 
        
        # 1. IS vs CF
        diff1 = abs(is_depr) - cf_depr
        status1 = "PASS" if abs(diff1) < 1.0 else "WARNING"
        
        self.results.append(ReconciliationResult(
            rule_id="3S-5a",
            rule_name="Depr (IS vs CF)",
            category="Three-Statement",
            status=status1,
            source_value=abs(is_depr),
            target_value=cf_depr,
            difference=diff1,
            variance_pct=0,
            details=f"IS ${abs(is_depr):,.0f} vs CF ${cf_depr:,.0f}",
            severity="high"
        ))
        
        # 2. IS vs BS Delta (if prior exists)
        if prior_id:
            diff2 = abs(is_depr) - bs_diff
            status2 = "PASS" if abs(diff2) < 1.0 else "WARNING" 
            
            self.results.append(ReconciliationResult(
                rule_id="3S-5b",
                rule_name="Depr (IS vs BS Delta)",
                category="Three-Statement",
                status=status2,
                source_value=abs(is_depr),
                target_value=bs_diff,
                difference=diff2,
                variance_pct=0,
                details=f"IS ${abs(is_depr):,.0f} vs BS Delta ${bs_diff:,.0f}",
                severity="high"
            ))

    def _rule_3s_1_cash_balance_check(self):
        """3S-1: BS Cash = CF Ending Cash"""
        bs_cash = self._get_bs_value(account_name_pattern="%CASH%")
        cf_end = self._get_cf_value(account_name_pattern="%ENDING CASH%")
        
        diff = bs_cash - cf_end
        status = "PASS" if abs(diff) < 1.0 else "FAIL"
        
        self.results.append(ReconciliationResult(
            rule_id="3S-1",
            rule_name="Cash Balance Check",
            category="Three-Statement",
            status=status,
            source_value=bs_cash,
            target_value=cf_end,
            difference=diff,
            variance_pct=0,
            details=f"BS Cash ${bs_cash:,.2f} vs CF Ending ${cf_end:,.2f}",
            severity="critical"
        ))
