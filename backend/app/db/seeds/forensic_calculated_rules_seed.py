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
        },
        {
            "rule_id": "IS_NET_INCOME_EQUATION",
            "rule_name": "Income Statement Net Income",
            "formula": "VIEW.net_income = VIEW.total_income - VIEW.total_operating_expenses - (VIEW.is_interest_expense + VIEW.depreciation_expense)",
            "description": "Net Income = Total Income - Total Operating Expenses - (Interest + Depreciation) (IS-1)",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("2.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_ESCROW_TO_BS",
            "rule_name": "Mortgage Escrow to BS Escrow",
            "formula": "VIEW.mst_total_escrow = VIEW.bs_escrow_accounts",
            "description": "Mortgage escrow balances tie to balance sheet escrow accounts (RECON-5/11)",
            "doc_scope": ["mortgage_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("5000.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "VIEW_INCOME_TO_METRICS",
            "rule_name": "Total Income to Metrics",
            "formula": "VIEW.total_income = METRICS.total_revenue",
            "description": "Income statement total income ties to metrics aggregation",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "VIEW_NOI_TO_METRICS",
            "rule_name": "NOI to Metrics",
            "formula": "VIEW.noi = METRICS.net_operating_income",
            "description": "NOI matches metrics calculation",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "VIEW_NET_INCOME_TO_METRICS",
            "rule_name": "Net Income to Metrics",
            "formula": "VIEW.net_income = METRICS.net_income",
            "description": "Net income ties to metrics",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "VIEW_OCCUPANCY_TO_METRICS",
            "rule_name": "Occupancy Rate to Metrics",
            "formula": "VIEW.occupancy_rate = METRICS.occupancy_rate",
            "description": "Occupancy rate ties to metrics occupancy",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("1.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "VIEW_DSCR_TO_METRICS",
            "rule_name": "DSCR to Metrics",
            "formula": "VIEW.dscr = METRICS.dscr",
            "description": "DSCR in reconciliation view matches metrics",
            "doc_scope": ["mortgage_statement", "income_statement"],
            "tolerance_absolute": Decimal("0.05"),
            "tolerance_percent": Decimal("2.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "VIEW_ASSETS_TO_METRICS",
            "rule_name": "Total Assets to Metrics",
            "formula": "VIEW.total_assets = METRICS.total_assets",
            "description": "Balance sheet total assets ties to metrics total assets",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("0.5"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "VIEW_LIAB_EQUITY_TO_METRICS",
            "rule_name": "Liabilities + Equity to Metrics",
            "formula": "VIEW.total_liabilities + VIEW.total_equity = METRICS.total_liabilities + METRICS.total_equity",
            "description": "Liabilities plus equity matches metrics aggregation",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("0.5"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CF_CATEGORY_SUM",
            "rule_name": "CF Category Sum",
            "formula": "VIEW.operating_cash_flow + VIEW.investing_cash_flow + VIEW.financing_cash_flow = VIEW.net_change_in_cash",
            "description": "Operating + Investing + Financing equals net change (CF-1)",
            "doc_scope": ["cash_flow"],
            "tolerance_absolute": Decimal("1.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ANNUAL_TO_METRICS",
            "rule_name": "Rent Roll Annual Rent to Metrics",
            "formula": "VIEW.rr_annual_rent = METRICS.total_annual_rent",
            "description": "Rent roll annual rent ties to metrics annual rent",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("100.00"),
            "tolerance_percent": Decimal("2.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        # ==================== ROLLFORWARD & TREND RULES ====================
        {
            "rule_id": "MST_PRINCIPAL_ROLLFORWARD",
            "rule_name": "Mortgage Principal Rollforward",
            "formula": "PREV.MST.principal_balance - MST.principal_due = MST.principal_balance",
            "description": "Prior principal minus current principal due equals current principal balance",
            "doc_scope": ["mortgage_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("200.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_YTD_PRINCIPAL_ROLL",
            "rule_name": "Mortgage YTD Principal Rollforward",
            "formula": "PREV.MST.ytd_principal_paid + MST.principal_due = MST.ytd_principal_paid",
            "description": "YTD principal increases by current principal due",
            "doc_scope": ["mortgage_statement"],
            "tolerance_absolute": Decimal("200.00"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_YTD_INTEREST_ROLL",
            "rule_name": "Mortgage YTD Interest Rollforward",
            "formula": "PREV.MST.ytd_interest_paid + MST.interest_due = MST.ytd_interest_paid",
            "description": "YTD interest increases by current interest due",
            "doc_scope": ["mortgage_statement"],
            "tolerance_absolute": Decimal("200.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_EARNINGS_ROLL",
            "rule_name": "Current Period Earnings Rollforward",
            "formula": "METRICS.current_period_earnings - PREV.METRICS.current_period_earnings = METRICS.net_income",
            "description": "Change in current period earnings equals net income",
            "doc_scope": ["balance_sheet", "income_statement"],
            "tolerance_absolute": Decimal("200.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_CASH_ROLL",
            "rule_name": "Cash Rollforward",
            "formula": "PREV.VIEW.bs_cash + VIEW.net_change_in_cash = VIEW.bs_cash",
            "description": "Prior cash plus net change equals current cash",
            "doc_scope": ["cash_flow", "balance_sheet"],
            "tolerance_absolute": Decimal("200.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        # ==================== RATIOS ====================
        {
            "rule_id": "EXPENSE_RATIO",
            "rule_name": "Expense Ratio",
            "formula": "METRICS.expense_ratio = METRICS.total_expenses / METRICS.total_revenue",
            "description": "Expense ratio ties to revenue and expenses",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("0.05"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "OPERATING_MARGIN",
            "rule_name": "Operating Margin",
            "formula": "METRICS.operating_margin = METRICS.net_operating_income / METRICS.total_revenue",
            "description": "Operating margin equals NOI divided by revenue",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("0.05"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        # ==================== MORTGAGE PATTERN RULES ====================
        {
            "rule_id": "MST_LATE_CHARGE_CALC",
            "rule_name": "Mortgage Late Charge Calculation",
            "formula": "MST.late_fees = MST.total_payment_due * 0.05",
            "description": "Late charge equals 5% of total payment (Mortgage Rule 12)",
            "doc_scope": ["mortgage_statement"],
            "tolerance_absolute": Decimal("25.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_PI_COMPONENT",
            "rule_name": "Principal + Interest Component",
            "formula": "MST.principal_due + MST.interest_due = MST.total_payment_due - (MST.tax_escrow_due + MST.insurance_escrow_due + MST.reserve_due)",
            "description": "Principal + Interest equals total payment minus escrow components (Mortgage Rule 11/8)",
            "doc_scope": ["mortgage_statement"],
            "tolerance_absolute": Decimal("100.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_PAYMENT_CONSTANT",
            "rule_name": "Mortgage Payment Constant",
            "formula": "MST.total_payment_due = PREV.MST.total_payment_due",
            "description": "Total payment remains constant month over month (Mortgage Rule 9)",
            "doc_scope": ["mortgage_statement"],
            "tolerance_absolute": Decimal("100.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_RATE_CONSTANT",
            "rule_name": "Mortgage Interest Rate Constant",
            "formula": "MST.interest_rate = PREV.MST.interest_rate",
            "description": "Interest rate remains constant across periods (Mortgage Rule 14)",
            "doc_scope": ["mortgage_statement"],
            "tolerance_absolute": Decimal("0.05"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        # ==================== BALANCE SHEET PATTERNS ====================
        {
            "rule_id": "BS_EQUITY_ROLL",
            "rule_name": "Equity Rollforward",
            "formula": "METRICS.total_equity = METRICS.beginning_equity + METRICS.partners_contribution + METRICS.current_period_earnings - METRICS.distributions + METRICS.partners_draw",
            "description": "Total equity rollforward from beginning equity, contributions, earnings, distributions, draws",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("200.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_LAND_CONSTANT",
            "rule_name": "Land Constant",
            "formula": "METRICS.land_value = PREV.METRICS.land_value",
            "description": "Land value remains constant across periods (BS-6)",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("1.00"),
            "tolerance_percent": Decimal("0.5"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_ACCUM_DEPR_NON_DECREASING",
            "rule_name": "Accumulated Depreciation Non-Decreasing",
            "formula": "METRICS.accumulated_depreciation = PREV.METRICS.accumulated_depreciation",
            "description": "Accumulated depreciation should not decrease period over period (tolerance allows minimal change)",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        # ==================== ADDITIONAL COVERAGE RULES ====================
        {
            "rule_id": "BS_CURRENT_RATIO_MIN",
            "rule_name": "Current Ratio Minimum",
            "formula": "METRICS.current_ratio >= 1.0",
            "description": "Current assets should cover current liabilities (BS liquidity check)",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("0.05"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_QUICK_RATIO_MIN",
            "rule_name": "Quick Ratio Minimum",
            "formula": "METRICS.quick_ratio >= 0.75",
            "description": "Quick ratio should stay above 0.75 (working capital adequacy)",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("0.05"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_WORKING_CAPITAL_POSITIVE",
            "rule_name": "Working Capital Positive",
            "formula": "METRICS.working_capital >= 0",
            "description": "Working capital should not be negative absent carve-outs",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("500.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_DEBT_TO_ASSETS_LIMIT",
            "rule_name": "Debt to Assets Limit",
            "formula": "METRICS.debt_to_assets_ratio <= 0.85",
            "description": "Total liabilities should be within 85% of assets (leverage reasonableness)",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("0.02"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_DEBT_TO_EQUITY_LIMIT",
            "rule_name": "Debt to Equity Limit",
            "formula": "METRICS.debt_to_equity_ratio <= 4.0",
            "description": "Debt-to-equity should stay under 4x (capital structure check)",
            "doc_scope": ["balance_sheet"],
            "tolerance_absolute": Decimal("0.10"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_RESTRICTED_CASH_ESCROW",
            "rule_name": "Restricted Cash equals Escrow Accounts",
            "formula": "METRICS.restricted_cash = VIEW.bs_escrow_accounts",
            "description": "Restricted cash roll matches escrow balances on balance sheet (RECON-5 style)",
            "doc_scope": ["balance_sheet", "mortgage_statement"],
            "tolerance_absolute": Decimal("500.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_TENANT_AR_COVERAGE",
            "rule_name": "Tenant A/R Coverage",
            "formula": "METRICS.tenant_receivables <= METRICS.total_monthly_rent * 2",
            "description": "Tenant receivables should not exceed two months of rent (collections sanity check)",
            "doc_scope": ["balance_sheet", "rent_roll"],
            "tolerance_absolute": Decimal("5000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "BS_DEPRECIATION_TO_ACCUM",
            "rule_name": "Depreciation feeds Accumulated Depreciation",
            "formula": "BS.1230-0000 = PREV.BS.1230-0000 - VIEW.is_depreciation",
            "description": "Accumulated depreciation should roll forward by current period depreciation expense",
            "doc_scope": ["balance_sheet", "income_statement"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "IS_EXPENSE_RATIO_UPPER",
            "rule_name": "Expense Ratio Upper Bound",
            "formula": "METRICS.expense_ratio <= 0.70",
            "description": "Operating expense ratio should generally be below 70% of revenue",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("0.02"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "IS_EXPENSE_RATIO_LOWER",
            "rule_name": "Expense Ratio Lower Bound",
            "formula": "METRICS.expense_ratio >= 0.20",
            "description": "Operating expense ratio should not be unrealistically low (<20%)",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("0.02"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "IS_PROFIT_MARGIN_NON_NEGATIVE",
            "rule_name": "Profit Margin Non-Negative",
            "formula": "METRICS.profit_margin >= 0",
            "description": "Net income margin should not be negative for stable assets",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("0.01"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CF_ENDING_CASH_NON_NEGATIVE",
            "rule_name": "Ending Cash Non-Negative",
            "formula": "VIEW.cf_ending_cash >= 0",
            "description": "Ending cash on cash flow should not be negative",
            "doc_scope": ["cash_flow"],
            "tolerance_absolute": Decimal("10.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_ESCROW_BAL_TO_BS",
            "rule_name": "Mortgage Escrow Balances to BS",
            "formula": "MST.tax_escrow_balance + MST.insurance_escrow_balance + MST.reserve_balance = VIEW.bs_escrow_accounts",
            "description": "Mortgage escrow balances should tie to balance sheet escrow accounts (expanded RECON-5)",
            "doc_scope": ["mortgage_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("500.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "MST_PRINCIPAL_NON_INCREASING",
            "rule_name": "Principal Balance Non-Increasing",
            "formula": "PREV.MST.principal_balance >= MST.principal_balance",
            "description": "Amortizing loan principal should not increase period over period",
            "doc_scope": ["mortgage_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("500.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        # ==================== RECONCILIATION GAP RULES ====================
        {
            "rule_id": "RECON_5_ESCROW_TOTAL",
            "rule_name": "Total Escrow Accounts Reconciliation",
            "formula": "MST.tax_escrow_balance + MST.insurance_escrow_balance + MST.reserve_balance = VIEW.bs_escrow_accounts",
            "description": "Sum of mortgage escrow balances ties to balance sheet escrow accounts (RECON-5)",
            "doc_scope": ["mortgage_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("500.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RECON_6_PRINCIPAL_IMPACT",
            "rule_name": "Monthly Principal Reduction Impact",
            "formula": "PREV.VIEW.bs_long_term_debt - MST.principal_due = VIEW.bs_long_term_debt",
            "description": "Prior long-term debt less current principal due should equal current long-term debt (RECON-6)",
            "doc_scope": ["balance_sheet", "mortgage_statement"],
            "tolerance_absolute": Decimal("500.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RECON_7_ESCROW_ROLL",
            "rule_name": "Escrow Account Rollforward",
            "formula": "PREV.VIEW.bs_escrow_accounts + MST.tax_escrow_due + MST.insurance_escrow_due + MST.reserve_due = VIEW.bs_escrow_accounts",
            "description": "Escrow balances roll forward with current escrow charges (RECON-7)",
            "doc_scope": ["balance_sheet", "mortgage_statement"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RECON_8_PROPERTY_TAX",
            "rule_name": "Property Tax Reconciliation",
            "formula": "IS.5150-0000 = MST.tax_escrow_due",
            "description": "Property tax expense aligns with mortgage tax escrow due (IS-BS-6 / RECON-8)",
            "doc_scope": ["income_statement", "mortgage_statement"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("15.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RECON_9_INSURANCE",
            "rule_name": "Insurance Payment Reconciliation",
            "formula": "IS.5140-0000 = MST.insurance_escrow_due",
            "description": "Insurance expense aligns with mortgage insurance escrow due (IS-BS-7 / RECON-9)",
            "doc_scope": ["income_statement", "mortgage_statement"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("15.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "IS_BS_6_PROPERTY_TAX_PAYABLE",
            "rule_name": "Property Tax Payable Rollforward",
            "formula": "PREV.BS.2130-0000 + IS.5150-0000 - MST.tax_escrow_due = BS.2130-0000",
            "description": "Property tax payable rolls with tax expense less escrow payments (IS-BS-6)",
            "doc_scope": ["balance_sheet", "income_statement", "mortgage_statement"],
            "tolerance_absolute": Decimal("1500.00"),
            "tolerance_percent": Decimal("15.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "IS_BS_7_INSURANCE_PAYABLE",
            "rule_name": "Insurance Payable Rollforward",
            "formula": "PREV.BS.2120-0000 + IS.5140-0000 - MST.insurance_escrow_due = BS.2120-0000",
            "description": "Insurance payable rolls with insurance expense less escrow payments (IS-BS-7)",
            "doc_scope": ["balance_sheet", "income_statement", "mortgage_statement"],
            "tolerance_absolute": Decimal("1500.00"),
            "tolerance_percent": Decimal("15.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_IS_2_BASE_RENT",
            "rule_name": "Rent Roll to IS Base Rent",
            "formula": "VIEW.rr_monthly_rent = VIEW.is_rental_income",
            "description": "Monthly rent roll ties to income statement base rent (RR-IS-2)",
            "doc_scope": ["rent_roll", "income_statement"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        # ==================== RENT ROLL FULL FLOW (RR-ALL-1..11) ====================
        {
            "rule_id": "RR_ALL_1_MONTHLY_TO_METRICS",
            "rule_name": "Monthly Rent to Metrics",
            "formula": "VIEW.rr_monthly_rent = METRICS.total_monthly_rent",
            "description": "Aggregated monthly rent from rent roll ties to metrics (RR-ALL-1)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("500.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_2_ANNUAL_TO_INCOME",
            "rule_name": "Annual Rent to Income Statement Total",
            "formula": "VIEW.rr_annual_rent = VIEW.is_total_income",
            "description": "Annual rent roll ties to total income reported (RR-ALL-2)",
            "doc_scope": ["rent_roll", "income_statement"],
            "tolerance_absolute": Decimal("5000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_3_VACANCY_CALC",
            "rule_name": "Vacant Units Calculation",
            "formula": "VIEW.rr_total_units - VIEW.rr_occupied_units = VIEW.rr_vacant_units",
            "description": "Vacant units equals total minus occupied units (RR-ALL-3)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("0.50"),
            "tolerance_percent": Decimal("1.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_4_REVENUE_PER_SF",
            "rule_name": "Revenue per Square Foot Alignment",
            "formula": "(VIEW.rr_annual_rent / VIEW.rr_square_footage) = METRICS.revenue_per_sqft",
            "description": "Rent roll revenue per sqft matches metrics computation (RR-ALL-4)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("0.10"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_5_NOI_PER_SF",
            "rule_name": "NOI per Square Foot Alignment",
            "formula": "METRICS.noi_per_sqft = METRICS.net_operating_income / VIEW.rr_square_footage",
            "description": "NOI per sqft aligns with rent roll square footage (RR-ALL-5)",
            "doc_scope": ["rent_roll", "income_statement"],
            "tolerance_absolute": Decimal("0.10"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_6_OCCUPANCY_FLOW",
            "rule_name": "Occupancy Flow Alignment",
            "formula": "VIEW.rr_occupancy_rate = VIEW.occupancy_rate",
            "description": "Rent roll occupancy equals master view occupancy (RR-ALL-6)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("0.50"),
            "tolerance_percent": Decimal("2.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_7_OCCUPANCY_METRICS",
            "rule_name": "Occupancy to Metrics",
            "formula": "VIEW.rr_occupancy_rate = METRICS.occupancy_rate",
            "description": "Rent roll occupancy ties to metrics occupancy (RR-ALL-7)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("0.50"),
            "tolerance_percent": Decimal("2.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_8_ANNUAL_TO_METRICS",
            "rule_name": "Annual Rent to Metrics",
            "formula": "VIEW.rr_annual_rent = METRICS.total_annual_rent",
            "description": "Annual rent roll ties to metrics annual rent (RR-ALL-8)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("1000.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_9_COLLECTION_GAP",
            "rule_name": "Collections Gap Reasonableness",
            "formula": "METRICS.tenant_receivables <= VIEW.rr_monthly_rent * 2",
            "description": "Tenant receivables should not exceed two months of rent (RR-ALL-9)",
            "doc_scope": ["balance_sheet", "rent_roll"],
            "tolerance_absolute": Decimal("5000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_10_BASE_RENT_TO_IS",
            "rule_name": "Base Rent to IS Rental Income",
            "formula": "VIEW.rr_monthly_rent * 12 = VIEW.is_rental_income * 12",
            "description": "Annualized monthly rent ties to IS rental income (RR-ALL-10)",
            "doc_scope": ["rent_roll", "income_statement"],
            "tolerance_absolute": Decimal("2000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "RR_ALL_11_RENT_FLOW_COMPLETE",
            "rule_name": "Complete Rent Flow Alignment",
            "formula": "VIEW.rr_annual_rent = (VIEW.is_rental_income + VIEW.is_other_income) * 12",
            "description": "Rent roll annual rent reconciles to IS rental plus other income (RR-ALL-11)",
            "doc_scope": ["rent_roll", "income_statement"],
            "tolerance_absolute": Decimal("5000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        # ==================== CALCULATED RATIOS CALC-011..020 ====================
        {
            "rule_id": "CALC_011_NET_INCOME_MARGIN",
            "rule_name": "Net Income Margin",
            "formula": "METRICS.profit_margin = METRICS.net_income / METRICS.total_revenue",
            "description": "Net income margin equals net income divided by revenue (CALC-011)",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("0.02"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_012_CAPEX_RATIO",
            "rule_name": "CapEx as % of Revenue",
            "formula": "(METRICS.investing_cash_flow * -1) <= METRICS.total_revenue * 0.10",
            "description": "Capital spending (investing cash outflow) should be <=10% of revenue absent projects (CALC-012)",
            "doc_scope": ["cash_flow", "income_statement"],
            "tolerance_absolute": Decimal("10000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_013_RENT_PER_SF",
            "rule_name": "Rent per Square Foot",
            "formula": "METRICS.revenue_per_sqft = METRICS.total_annual_rent / METRICS.total_leasable_sqft",
            "description": "Average rent per square foot matches rent roll totals (CALC-013)",
            "doc_scope": ["rent_roll", "income_statement"],
            "tolerance_absolute": Decimal("0.10"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_014_TENANT_CONCENTRATION",
            "rule_name": "Tenant Concentration Top 5",
            "formula": "TENANT.top_5_tenant_pct <= 65",
            "description": "Top 5 tenants should contribute <=65% of total rent (CALC-014)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("2.00"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_015_LEASE_ROLLOVER",
            "rule_name": "Lease Rollover 12mo",
            "formula": "TENANT.lease_rollover_12mo_pct <= 25",
            "description": "Lease rollover within 12 months should be <=25% of rent (CALC-015)",
            "doc_scope": ["rent_roll"],
            "tolerance_absolute": Decimal("2.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_016_CASH_RUNWAY",
            "rule_name": "Cash Runway Months",
            "formula": "METRICS.total_cash_position / (METRICS.total_expenses / 12) >= 3",
            "description": "Cash on hand should cover at least 3 months of expenses (CALC-016)",
            "doc_scope": ["cash_flow", "balance_sheet"],
            "tolerance_absolute": Decimal("0.25"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_017_NOI_PER_SF",
            "rule_name": "NOI per Square Foot",
            "formula": "METRICS.noi_per_sqft = METRICS.net_operating_income / METRICS.total_leasable_sqft",
            "description": "NOI per square foot aligns with total leasable area (CALC-017)",
            "doc_scope": ["income_statement", "rent_roll"],
            "tolerance_absolute": Decimal("0.10"),
            "tolerance_percent": Decimal("5.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_018_SAME_STORE_GROWTH",
            "rule_name": "Same-Store Growth Floor",
            "formula": "METRICS.total_revenue >= PREV.METRICS.total_revenue * 0.90",
            "description": "Revenue should not decline more than 10% vs prior period (CALC-018)",
            "doc_scope": ["income_statement"],
            "tolerance_absolute": Decimal("10000.00"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "warning",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_019_RETURN_ON_EQUITY",
            "rule_name": "Return on Equity",
            "formula": "METRICS.net_income / METRICS.total_equity >= 0.05",
            "description": "Net income should yield at least 5% on equity (CALC-019)",
            "doc_scope": ["income_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("0.01"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "info",
            "property_scope": {"all": True}
        },
        {
            "rule_id": "CALC_020_CAP_RATE",
            "rule_name": "Cap Rate Reasonableness",
            "formula": "METRICS.net_operating_income / METRICS.gross_property_value >= 0.04",
            "description": "Cap rate should be at least 4% based on NOI and property value (CALC-020)",
            "doc_scope": ["income_statement", "balance_sheet"],
            "tolerance_absolute": Decimal("0.01"),
            "tolerance_percent": Decimal("10.0"),
            "severity": "info",
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
