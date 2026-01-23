from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

class MortgageRulesMixin:
    
    def _execute_mortgage_rules(self):
        """Execute Mortgage rules"""
        self._rule_mst_1_payment_components()
        self._rule_mst_2_principal_rollforward()
        self._rule_mst_3_interest_rollforward()
        self._rule_mst_4_escrow_audit()
        
    def _get_mst_value(self, column_name, period_id=None):
        """Helper to get value from mortgage_statement_data"""
        if period_id is None:
            period_id = self.period_id
            
        query = text(f"""
            SELECT {column_name}
            FROM mortgage_statement_data
            WHERE property_id = :p_id 
            AND period_id = :period_id
            LIMIT 1
        """)
        result = self.db.execute(query, {
            "p_id": self.property_id, 
            "period_id": period_id
        })
        val = result.scalar()
        return float(val) if val is not None else 0.0

    def _rule_mst_1_payment_components(self):
        """MST-1: Total Payment = Principal + Interest + Escrows"""
        total = self._get_mst_value("total_payment_due")
        principal = self._get_mst_value("principal_due")
        interest = self._get_mst_value("interest_due")
        tax = self._get_mst_value("tax_escrow_due")
        ins = self._get_mst_value("insurance_escrow_due")
        res = self._get_mst_value("reserve_due")
        
        calc_total = principal + interest + tax + ins + res
        diff = total - calc_total
        
        self.results.append(ReconciliationResult(
            rule_id="MST-1",
            rule_name="Payment Components",
            category="Mortgage",
            status="PASS" if abs(diff) < 1.0 else "FAIL",
            source_value=total,
            target_value=calc_total,
            difference=diff,
            variance_pct=0,
            details=f"Total ${total:,.2f} vs Sum ${calc_total:,.2f}",
            severity="high"
        ))

    def _rule_mst_2_principal_rollforward(self):
        """MST-2: Principal Balance Rollforward"""
        curr_bal = self._get_mst_value("principal_balance")
        principal_due = self._get_mst_value("principal_due")
        
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return
            
        prior_bal = self._get_mst_value("principal_balance", period_id=prior_id)
        
        expected = prior_bal - principal_due
        diff = curr_bal - expected
        
        self.results.append(ReconciliationResult(
            rule_id="MST-2",
            rule_name="Principal Rollforward",
            category="Mortgage",
            status="PASS" if abs(diff) < 1.0 else "FAIL",
            source_value=curr_bal,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"Principal Balance rolled correctly (Paid matching Due)",
            severity="critical"
        ))

    def _rule_mst_3_interest_rollforward(self):
        """MST-3: YTD Interest Rollforward"""
        curr_ytd = self._get_mst_value("ytd_interest_paid")
        curr_int = self._get_mst_value("interest_due")
        
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return 
            
        prior_ytd = self._get_mst_value("ytd_interest_paid", period_id=prior_id)
        
        expected = prior_ytd + curr_int
        diff = curr_ytd - expected
        
        status = "PASS" if abs(diff) < 1.0 else "WARNING"
        self.results.append(ReconciliationResult(
            rule_id="MST-3",
            rule_name="YTD Interest Roll",
            category="Mortgage",
            status=status,
            source_value=curr_ytd,
            target_value=expected,
            difference=diff,
            variance_pct=0,
            details=f"YTD Interest ${curr_ytd:,.2f} vs Expected ${expected:,.2f}",
            severity="medium"
        ))
        
    def _rule_mst_4_escrow_audit(self):
        """MST-4: Escrow Audit (Balances positive)"""
        tax_bal = self._get_mst_value("tax_escrow_balance")
        ins_bal = self._get_mst_value("insurance_escrow_balance")
        
        status = "PASS" if tax_bal >= 0 and ins_bal >= 0 else "WARNING"
        
        self.results.append(ReconciliationResult(
            rule_id="MST-4",
            rule_name="Escrow Positive Balances",
            category="Mortgage",
            status=status,
            source_value=tax_bal + ins_bal,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=f"Tax Escrow: ${tax_bal:,.2f}, Ins Escrow: ${ins_bal:,.2f}",
            severity="info"
        ))
