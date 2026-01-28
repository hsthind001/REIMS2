from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

from app.services.rules.period_alignment_mixin import PeriodAlignmentMixin
from app.services.rules.balance_sheet_rules import BalanceSheetRulesMixin
from app.services.rules.income_statement_rules import IncomeStatementRulesMixin
from app.services.rules.three_statement_rules import ThreeStatementRulesMixin
from app.services.rules.cash_flow_rules import CashFlowRulesMixin
from app.services.rules.mortgage_rules import MortgageRulesMixin
from app.services.rules.rent_roll_rules import RentRollRulesMixin
from app.services.rules.audit_rules_mixin import AuditRulesMixin
from app.services.rules.analytics_rules_mixin import AnalyticsRulesMixin
from app.services.rules.data_quality_rules_mixin import DataQualityRulesMixin
from app.services.rules.forensic_anomaly_rules_mixin import ForensicAnomalyRulesMixin
from app.services.rules.rent_roll_balance_sheet_rules_mixin import RentRollBalanceSheetRulesMixin
from app.services.market_data_integration import MarketDataIntegration

from app.services.rules.safe_query_mixin import SafeQueryMixin

class ReconciliationRuleEngine(
    SafeQueryMixin,
    PeriodAlignmentMixin,
    BalanceSheetRulesMixin,
    IncomeStatementRulesMixin,
    ThreeStatementRulesMixin,
    CashFlowRulesMixin,
    MortgageRulesMixin,
    RentRollRulesMixin,
    AuditRulesMixin,
    AnalyticsRulesMixin,
    DataQualityRulesMixin,
    ForensicAnomalyRulesMixin,
    RentRollBalanceSheetRulesMixin
):
    """
    Executes all 135+ reconciliation rules (Synchronous)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.results: List[ReconciliationResult] = []
        self.property_id = None
        self.period_id = None
        self.market_data_service = None
        self.market_data_integration = MarketDataIntegration()

    def set_market_data_service(self, service):
        """Optional hook for external market data service integration."""
        self.market_data_service = service
        self.market_data_integration.market_data_service = service
        
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
        """Execute all reconciliation rules with fault isolation"""
        self.property_id = property_id
        self.period_id = period_id
        self.results = []
        self.alignment_context = None

        # Period alignment is the critical foundation for rolling-window reconciliations.
        try:
            alignment_context = self._initialize_period_alignment()
            print(
                "Period alignment resolved: "
                f"begin={alignment_context.begin_period_id} "
                f"end={alignment_context.end_period_id} "
                f"window_months={alignment_context.window_months} "
                f"method={alignment_context.alignment_method}"
            )
        except Exception as alignment_error:
            print(f"Period alignment initialization failed: {alignment_error}")

        # Emit alignment context as a visible rule result for debugging/transparency.
        try:
            ctx = self._get_alignment_context()
            self.results.append(
                ReconciliationResult(
                    rule_id="PAL-CTX",
                    rule_name="Period Alignment Context",
                    category="System",
                    status="INFO",
                    source_value=float(ctx.window_months),
                    target_value=float(ctx.window_months),
                    difference=0.0,
                    variance_pct=0.0,
                    details=(
                        f"Begin={ctx.begin_period_id} End={ctx.end_period_id} "
                        f"WindowMonths={ctx.window_months} Method={ctx.alignment_method} "
                        f"CashDiff=${ctx.cash_match_diff:,.2f}"
                    ),
                    severity="info",
                    formula="PAL / FA-PAL alignment context",
                    intermediate_calculations={"alignment": ctx.to_dict()},
                )
            )
        except Exception:
            # Alignment context is best-effort; do not block other rules.
            pass
        
        # DEBUG RULE: Verify Engine Update
        self.results.append(ReconciliationResult(
            rule_id="ENGINE-TEST",
            rule_name="Engine Active",
            category="System",
            status="PASS",
            source_value=1, target_value=1, difference=0, variance_pct=0,
            details="Engine verified",
            severity="info"
        ))
        
        # Helper to run mixin safely
        def run_module(name, func):
            try:
                func()
            except Exception as e:
                print(f"Error executing {name} rules: {e}")
                self.db.rollback() # Reset session state so other rules can run
                # Optional: Append a System Error result so specific failure is visible in UI
                self.results.append(ReconciliationResult(
                    rule_id=f"SYS-ERR-{name[:3].upper()}",
                    rule_name=f"{name} Engine Failure",
                    category="System",
                    status="FAIL",
                    source_value=0,
                    target_value=0,
                    difference=0,
                    variance_pct=0,
                    details=f"System Error: {str(e)}",
                    severity="critical",
                    formula="N/A"
                ))
                # Re-raise for debugging if it's critical? No, just log distinctively.
                print(f"CRITICAL MODULE FAILURE [{name}]: {e}")
        
        # Execute modules independently
        run_module("Balance Sheet", self._execute_balance_sheet_rules)
        run_module("Income Statement", self._execute_income_statement_rules)
        run_module("Three Statement", self._execute_three_statement_rules)
        run_module("Cash Flow", self._execute_cash_flow_rules)
        run_module("Mortgage", self._execute_mortgage_rules)
        run_module("Audit", self._execute_audit_rules)
        run_module("Analytics", self._execute_analytics_rules)
        run_module("Data Quality", self._execute_data_quality_rules)
        run_module("Forensic", self._execute_forensic_anomaly_rules)
        run_module("RR-BS", self._execute_rent_roll_balance_sheet_rules)
        # Rent Roll usually robust, but wrap it too
        # Custom execution for Rent Roll to debug
        try:
             # Force fresh execution logic
             print("Executing Rent Roll Rules explicitly...")
             self._execute_rent_roll_rules()
        except Exception as e:
             self.results.append(ReconciliationResult(
                rule_id="SYS-RR-Crash",
                rule_name="Rent Roll Crash",
                category="Rent Roll",
                status="FAIL",
                source_value=0, target_value=0, difference=0, variance_pct=0,
                details=str(e),
                severity="critical"
             ))
            
        return self.results

    def save_results(self):
        """Save results to cross_document_reconciliations table with deduplication"""
        if not self.results:
            return

        alignment_summary = None
        try:
            ctx = self._get_alignment_context()
            alignment_summary = {
                "alignment": {
                    "begin_period_id": ctx.begin_period_id,
                    "end_period_id": ctx.end_period_id,
                    "window_months": ctx.window_months,
                    "method": ctx.alignment_method,
                    "confidence": ctx.alignment_confidence,
                    "cf_beginning_cash": ctx.cf_beginning_cash,
                    "cf_ending_cash": ctx.cf_ending_cash,
                    "bs_beginning_cash": ctx.bs_beginning_cash,
                    "bs_ending_cash": ctx.bs_ending_cash,
                    "cash_match_period_id": ctx.cash_match_period_id,
                    "cash_match_bs_cash": ctx.cash_match_bs_cash,
                    "cash_match_diff": ctx.cash_match_diff,
                    "cash_match_candidate_count": ctx.cash_match_candidate_count,
                    "cash_match_within_tolerance": ctx.cash_match_within_tolerance,
                }
            }
        except Exception:
            alignment_summary = None
            
        # DEDUPLICATION: Last Write Wins
        unique_results = {}
        for res in self.results:
            unique_results[res.rule_id] = res
            
        final_list = list(unique_results.values())
        print(f"Saving {len(final_list)} unique results (deduplicated from {len(self.results)})")
            
        try:
            # Clear existing results for this property/period
            self.db.execute(text("""
                DELETE FROM cross_document_reconciliations 
                WHERE property_id = :p_id AND period_id = :period_id
            """), {"p_id": self.property_id, "period_id": self.period_id})
            
            # Insert new results
            formatted_params = []
            for res in final_list:
                # Determine is_material
                is_material = res.status != "PASS" and abs(res.difference) > 0.01
                
                formatted_params.append({
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
                    "recommendation": res.formula,
                    "intermediate_calculations": res.intermediate_calculations or alignment_summary,
                })

            # Bulk Insert using executemany optimization if supported, or loop
            # Using loop for clarity and error pinpointing, but could be optimized
            stmt = text("""
                INSERT INTO cross_document_reconciliations (
                    property_id, period_id, reconciliation_type, rule_code, status,
                    source_document, target_document,
                    source_value, target_value, difference,
                    materiality_threshold, is_material,
                    explanation, recommendation,
                    intermediate_calculations,
                    created_at, updated_at
                ) VALUES (
                    :p_id, :period_id, :rule_name, :rule_id, :status,
                    :src_doc, :tgt_doc,
                    :src, :tgt, :diff,
                    :threshold, :is_material,
                    :explanation, :recommendation,
                    :intermediate_calculations,
                    NOW(), NOW()
                )
            """)
            
            for params in formatted_params:
                try:
                    with self.db.begin_nested():
                        self.db.execute(stmt, params)
                except Exception as row_error:
                    print(f"Skipping rule {params['rule_id']} due to error: {row_error}")
                    # Continue to next row
                
            self.db.commit()
            
        except Exception as e:
            print(f"Error saving reconciliation results: {e}")
            self.db.rollback()
            raise e
