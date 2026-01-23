from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.services.reconciliation_types import ReconciliationResult

from app.services.rules.balance_sheet_rules import BalanceSheetRulesMixin
from app.services.rules.income_statement_rules import IncomeStatementRulesMixin
from app.services.rules.three_statement_rules import ThreeStatementRulesMixin
from app.services.rules.cash_flow_rules import CashFlowRulesMixin
from app.services.rules.mortgage_rules import MortgageRulesMixin
from app.services.rules.rent_roll_rules import RentRollRulesMixin

class ReconciliationRuleEngine(
    BalanceSheetRulesMixin,
    IncomeStatementRulesMixin,
    ThreeStatementRulesMixin,
    CashFlowRulesMixin,
    MortgageRulesMixin,
    RentRollRulesMixin
):
    """
    Executes all 135+ reconciliation rules (Synchronous)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.results: List[ReconciliationResult] = []
        self.property_id = None
        self.period_id = None
        
    def _get_prior_period_id(self) -> Optional[int]:
        """Get ID of the previous financial period"""
        # Get current period details
        import sqlalchemy
        curr_query = sqlalchemy.text("SELECT period_year, period_month FROM financial_periods WHERE id = :p_id")
        curr_res = self.db.execute(curr_query, {"p_id": int(self.period_id)})
        curr_row = curr_res.fetchone()
        
        if not curr_row:
            return None
            
        curr_year, curr_month = curr_row
        
        # Determine prior date
        if curr_month == 1:
            prior_year = curr_year - 1
            prior_month = 12
        else:
            prior_year = curr_year
            prior_month = curr_month - 1
            
        # Find prior period ID
        query = sqlalchemy.text("""
            SELECT id FROM financial_periods 
            WHERE property_id = :prop_id 
            AND period_year = :year 
            AND period_month = :month
        """)
        
        result = self.db.execute(query, {
            "prop_id": int(self.property_id), 
            "year": prior_year, 
            "month": prior_month
        })
        
        row = result.fetchone()
        return row[0] if row else None
        
    def execute_all_rules(self, property_id: int, period_id: int) -> List[ReconciliationResult]:
        """Execute all reconciliation rules"""
        self.property_id = property_id
        self.period_id = period_id
        self.results = []
        
        try:
            self._execute_balance_sheet_rules()
            self._execute_income_statement_rules()
            self._execute_three_statement_rules()
            self._execute_cash_flow_rules()
            self._execute_mortgage_rules()
            self._execute_rent_roll_rules()
        except Exception as e:
            print(f"Error executing rules: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
            
        return self.results

    def save_results(self):
        """Save results to cross_document_reconciliations table"""
        if not self.results:
            return
            
        # Clear existing results for this property/period
        self.db.execute(text("""
            DELETE FROM cross_document_reconciliations 
            WHERE property_id = :p_id AND period_id = :period_id
        """), {"p_id": self.property_id, "period_id": self.period_id})
        
        # Insert new results
        for res in self.results:
            # Determine is_material
            is_material = res.status != "PASS" and abs(res.difference) > 0.01
            
            self.db.execute(text("""
                INSERT INTO cross_document_reconciliations (
                    property_id, period_id, reconciliation_type, rule_code, status,
                    source_document, target_document,
                    source_value, target_value, difference,
                    materiality_threshold, is_material,
                    explanation, recommendation,
                    created_at, updated_at
                ) VALUES (
                    :p_id, :period_id, :rule_name, :rule_id, :status,
                    :src_doc, :tgt_doc,
                    :src, :tgt, :diff,
                    :threshold, :is_material,
                    :explanation, :recommendation,
                    NOW(), NOW()
                )
            """), {
                "p_id": self.property_id,
                "period_id": self.period_id,
                "rule_name": res.rule_name, 
                "rule_id": res.rule_id, 
                "status": res.status,
                "src_doc": res.category, 
                "tgt_doc": "N/A", 
                "src": res.source_value,
                "tgt": res.target_value,
                "diff": res.difference,
                "threshold": 0.0, 
                "is_material": is_material,
                "explanation": res.details,
                "recommendation": None
            })
            
        self.db.commit()
