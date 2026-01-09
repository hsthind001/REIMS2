"""
Seed calculated rules for forensic reconciliation.

Rules are derived from /home/hsthind/Downloads/Reconcile - Aduit - Rules
and focus on cross-document tieouts and core statement equations.
"""
from datetime import date
from decimal import Decimal

from app.db.database import SessionLocal
from app.models.calculated_rule import CalculatedRule


def seed_calculated_rules():
    db = SessionLocal()

    try:
        rules = [
            {
            "rule_id": "BS_EQUATION",
            "rule_name": "Balance Sheet Equation",
            "formula": "VIEW.total_assets = VIEW.total_liabilities + VIEW.total_equity",
            "description": "Assets must equal Liabilities plus Equity (BS-1)",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("1.00"),
            "tolerance_percent": Decimal("0.1"),
            "severity": "critical",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CF_RECONCILIATION",
            "rule_name": "Cash Flow Reconciliation",
            "formula": "VIEW.beginning_cash + VIEW.net_change_in_cash = VIEW.cf_ending_cash",
            "description": "Beginning cash plus net change equals ending cash (CF-2)",
            "doc_scope": ["cash_flow"],
            "tolerance_absolute": Decimal("1.00"),
            "tolerance_percent": Decimal("0.1"),
            "severity": "critical",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CF_ENDING_TO_BS_CASH",
            "rule_name": "CF Ending Cash to BS Cash",
            "formula": "VIEW.cf_ending_cash = VIEW.bs_cash",
            "description": "Cash Flow ending cash equals Balance Sheet cash (CF-2)",
            "doc_scope": ["cash_flow", "balance_sheet"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "critical",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_TO_BS_DEBT",
            "rule_name": "Mortgage Principal to Balance Sheet Debt",
            "formula": "VIEW.mst_principal_balance = VIEW.bs_long_term_debt",
            "description": "Mortgage principal ties to long-term debt (RECON-1)",
            "doc_scope": ["mortgage_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("100.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "critical",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_PAYMENT_TO_CF_DEBT_SERVICE",
            "rule_name": "Mortgage Payment to CF Debt Service",
            "formula": "VIEW.mst_total_payment = VIEW.cf_debt_service",
            "description": "Mortgage payment equals cash flow debt service (CF-14)",
            "doc_scope": ["mortgage_statement", "cash_flow"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "critical",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_INTEREST_TO_IS",
            "rule_name": "Mortgage Interest to Income Statement",
            "formula": "VIEW.mst_interest_due = VIEW.is_interest_expense",
            "description": "Mortgage interest due ties to IS interest expense (IS-17)",
            "doc_scope": ["mortgage_statement", "income_statement"],
            "tolerance_absolute": Decimal("100.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_TO_IS_RENTAL",
            "rule_name": "Rent Roll to Income Statement",
            "formula": "VIEW.rr_annual_rent = VIEW.is_rental_income",
            "description": "Annual rent roll ties to IS rental income (RR-IS-1)",
            "doc_scope": ["rent_roll", "income_statement"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ANNUAL_EQUALS_MONTHLY",
            "rule_name": "Rent Roll Annual Rent",
            "formula": "VIEW.rr_annual_rent = VIEW.total_monthly_rent * 12",
            "description": "Annual rent equals monthly rent times 12 (RR-3)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("100.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_OCCUPANCY_RATE",
            "rule_name": "Rent Roll Occupancy Rate",
            "formula": "VIEW.occupancy_rate = (VIEW.occupied_units / VIEW.total_units) * 100",
            "description": "Occupancy rate equals occupied units / total units (RR-2)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("0.5"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_PAYMENT_COMPONENTS",
            "rule_name": "Mortgage Payment Components",
            "formula": "MST.total_payment_due = MST.principal_due + MST.interest_due + MST.tax_escrow_due + MST.insurance_escrow_due + MST.reserve_due",
            "description": "Total payment equals principal + interest + escrows (Mortgage Rule 8)",
            "doc_scope": ["mortgage_statement"],
            "tolerance_absolute": Decimal("1.00"),
            "tolerance_percent": Decimal("0.1"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "NET_INCOME_TO_EARNINGS",
            "rule_name": "Net Income to Current Period Earnings",
            "formula": "METRICS.current_period_earnings = METRICS.net_income",
            "description": "Net income flows to BS current period earnings (IS-BS-1)",
            "doc_scope": ["income_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("100.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "NOI_CALCULATION",
            "rule_name": "NOI Calculation",
            "formula": "METRICS.net_operating_income = METRICS.total_revenue - METRICS.total_expenses",
            "description": "NOI equals revenue minus operating expenses (IS-1)",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
            }
        ]

        inserted = 0
        for rule_data in rules:
            existing = db.query(CalculatedRule).filter(
                CalculatedRule.rule_id == rule_data["rule_id"],
                CalculatedRule.version == 1
            ).first()
            if existing:
                continue

            rule = CalculatedRule(
                rule_id=rule_data["rule_id"],
                version=1,
                rule_name=rule_data["rule_name"],
                formula=rule_data["formula"],
                description=rule_data["description"],
                property_scope=rule_data["property_scope"],
                doc_scope=rule_data["doc_scope"],
                tolerance_absolute=rule_data["tolerance_absolute"],
                tolerance_percent=rule_data["tolerance_percent"],
                severity=rule_data["severity"],
                effective_date=date.today(),
                expires_at=None,
                is_active=True
            )
            db.add(rule)
            inserted += 1

        db.commit()
        print(f"✓ Calculated rules seeded: {inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_calculated_rules()
