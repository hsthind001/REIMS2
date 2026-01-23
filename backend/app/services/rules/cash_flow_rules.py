from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

class CashFlowRulesMixin:
    
    def _execute_cash_flow_rules(self):
        """Execute Cash Flow rules"""
        self._rule_cf_1_category_sum()
        self._rule_cf_2_reconciliation()
        self._rule_cf_3_ending_cash_positive()
        
    def _get_cf_value(self, account_code_pattern=None, account_name_pattern=None, category=None):
        """Helper to get value from cash_flow_data"""
        if account_code_pattern:
            clause = "account_code LIKE :pattern"
            pattern = account_code_pattern
        else:
            clause = "account_name ILIKE :pattern"
            pattern = account_name_pattern
            
        params = {
            "p_id": self.property_id, 
            "period_id": self.period_id,
            "pattern": pattern
        }
        
        cat_clause = ""
        if category:
            cat_clause = "AND cash_flow_category ILIKE :category"
            params["category"] = category
            
        query = text(f"""
            SELECT period_amount
            FROM cash_flow_data
            WHERE property_id = :p_id 
            AND period_id = :period_id
            AND {clause}
            {cat_clause}
            LIMIT 1
        """)
        result = self.db.execute(query, params)
        val = result.scalar()
        return float(val) if val is not None else 0.0

    def _rule_cf_1_category_sum(self):
        """CF-1: Operating + Investing + Financing = Net Change"""
        # Sum by category
        query = text("""
            SELECT cash_flow_category, SUM(period_amount)
            FROM cash_flow_data
            WHERE property_id = :p_id AND period_id = :period_id
            GROUP BY cash_flow_category
        """)
        rows = self.db.execute(query, {"p_id": self.property_id, "period_id": self.period_id})
        cats = {r[0].lower(): float(r[1]) for r in rows}
        
        operating = cats.get('operating', 0.0)
        investing = cats.get('investing', 0.0)
        financing = cats.get('financing', 0.0)
        
        calculated_net = operating + investing + financing
        
        # Get reported Net Change
        reported_net = self._get_cf_value(account_name_pattern="%NET CHANGE%CASH%")
        
        diff = calculated_net - reported_net
        
        self.results.append(ReconciliationResult(
            rule_id="CF-1",
            rule_name="CF Category Sum",
            category="Cash Flow",
            status="PASS" if abs(diff) < 1.0 else "FAIL",
            source_value=calculated_net,
            target_value=reported_net,
            difference=diff,
            variance_pct=0,
            details=f"Op({operating:,.0f}) + Inv({investing:,.0f}) + Fin({financing:,.0f}) = {calculated_net:,.0f}",
            severity="critical"
        ))

    def _rule_cf_2_reconciliation(self):
        """CF-2: Beginning Cash + Net Change = Ending Cash"""
        beg = self._get_cf_value(account_name_pattern="%BEGINNING CASH%")
        net = self._get_cf_value(account_name_pattern="%NET CHANGE%CASH%")
        end = self._get_cf_value(account_name_pattern="%ENDING CASH%")
        
        calc_end = beg + net
        diff = calc_end - end
        
        self.results.append(ReconciliationResult(
            rule_id="CF-2",
            rule_name="Cash Reconciliation",
            category="Cash Flow",
            status="PASS" if abs(diff) < 1.0 else "FAIL",
            source_value=calc_end,
            target_value=end,
            difference=diff,
            variance_pct=0,
            details=f"Beg({beg:,.0f}) + Net({net:,.0f}) = End({end:,.0f})",
            severity="critical"
        ))

    def _rule_cf_3_ending_cash_positive(self):
        """Ending Cash >= 0"""
        end = self._get_cf_value(account_name_pattern="%ENDING CASH%")
        status = "PASS" if end >= 0 else "WARNING"
        
        self.results.append(ReconciliationResult(
            rule_id="CF-3",
            rule_name="Positive Ending Cash",
            category="Cash Flow",
            status=status,
            source_value=end,
            target_value=0, 
            difference=end,
            variance_pct=0,
            details=f"Ending Cash is ${end:,.2f}",
            severity="high"
        ))
