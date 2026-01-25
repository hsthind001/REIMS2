"""
Seed calculated rules for forensic reconciliation.

Rules are derived from the active Python ReconciliationRuleEngine to ensure
Database Definitions match the Executed Runtime Rules.
"""
from datetime import date
from app.db.database import SessionLocal
from app.models.calculated_rule import CalculatedRule

def seed_calculated_rules():
    db = SessionLocal()

    try:
        rules = [
            # ==================== BALANCE SHEET (BS-1 to BS-35) ====================
            {"rule_id": "BS-1", "rule_name": "Accounting Equation", "formula": "VIEW.total_assets = VIEW.total_liabilities + VIEW.total_equity", "doc_scope": ["balance_sheet"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "BS-2", "rule_name": "Cash Operating Check", "formula": "BS.0122-0000 = 3375.45", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-3", "rule_name": "Current Assets Integrity", "formula": "VIEW.total_current_assets > 0", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-4", "rule_name": "Current Ratio Liquidity", "formula": "VIEW.total_current_assets / VIEW.total_current_liabilities >= 1.0", "doc_scope": ["balance_sheet"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "BS-5", "rule_name": "Working Capital Positive", "formula": "VIEW.total_current_assets - VIEW.total_current_liabilities > 0", "doc_scope": ["balance_sheet"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "BS-6", "rule_name": "Land Asset Verification", "formula": "BS.0510-0000 > 0", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-7", "rule_name": "Accum Depr Trend", "formula": "abs(BS.1230-0000) >= abs(PREV.BS.1230-0000)", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-8", "rule_name": "Accum Depr Buildings Trend", "formula": "PYTHON_LOGIC_CHECK", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-9", "rule_name": "Debt to Assets Ratio", "formula": "VIEW.total_liabilities / VIEW.total_assets <= 0.85", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-10", "rule_name": "5-Year Improvements", "formula": "BS.5YR_IMP = -1025187.00", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-11", "rule_name": "TI Improvements", "formula": "BS.TENANT_IMP >= 0", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-12", "rule_name": "Roof Asset Value", "formula": "BS.ROOF > 0", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-13", "rule_name": "HVAC Asset", "formula": "BS.HVAC >= 0", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-14", "rule_name": "Deposits Check", "formula": "BS.DEPOSITS = 20900.00", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-15", "rule_name": "Loan Costs Asset", "formula": "BS.LOAN_COSTS = 268752.01", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-16", "rule_name": "Loan Cost Amortization", "formula": "abs(BS.ACCUM_AMORT_LOAN) >= abs(PREV.BS.ACCUM_AMORT_LOAN)", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-17", "rule_name": "Accum Amort Other", "formula": "BS.ACCUM_AMORT_OTHER = -36621.19", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-18", "rule_name": "Ext Lease Comm", "formula": "BS.EXT_LEASE_COMM > 0", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-19", "rule_name": "Int Lease Comm", "formula": "BS.INT_LEASE_COMM > 0", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-20", "rule_name": "Prepaid Insurance", "formula": "BS.PREPAID_INS > 0", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-21", "rule_name": "Prepaid Expenses", "formula": "BS.PREPAID_EXP >= 0", "doc_scope": ["balance_sheet"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "BS-22", "rule_name": "A/P 5Rivers", "formula": "BS.AP_5RIVERS = 31683.54", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-23", "rule_name": "A/P Eastchase", "formula": "BS.AP_EASTCHASE = 354.54", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-24", "rule_name": "Loans Payable 5Rivers", "formula": "BS.LOANS_5RIVERS = 1810819.58", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-25", "rule_name": "Deposit Refundable", "formula": "BS.DEPOSIT_REFUND = 49791.31", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-26", "rule_name": "Accrued Expenses", "formula": "Tracking", "doc_scope": ["balance_sheet"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "BS-27", "rule_name": "A/P Trade", "formula": "Tracking", "doc_scope": ["balance_sheet"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "BS-28", "rule_name": "Property Tax Payable", "formula": "Tracking Accumulation", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-29", "rule_name": "Rent In Advance", "formula": "Tracking", "doc_scope": ["balance_sheet"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "BS-30", "rule_name": "Partners Contribution", "formula": "BS.PARTNERS_CONTRIB = 5684514.69", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-31", "rule_name": "Beginning Equity", "formula": "BS.BEG_EQUITY = 1786413.82", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-32", "rule_name": "Distributions", "formula": "BS.DISTRIBUTIONS <= 0", "doc_scope": ["balance_sheet"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "BS-33", "rule_name": "Earnings Accumulation", "formula": "BS.CURR_EARNINGS - PREV.BS.CURR_EARNINGS = NET_INCOME", "doc_scope": ["balance_sheet", "income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-34", "rule_name": "Total Capital Logic", "formula": "Calculated Sum verification", "doc_scope": ["balance_sheet"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "BS-35", "rule_name": "Total Capital Change", "formula": "Tracking", "doc_scope": ["balance_sheet"], "severity": "info", "property_scope": {"all": True}},

            # ==================== CASH FLOW (CF-1 to CF-23) ====================
            {"rule_id": "CF-1", "rule_name": "CF Category Sum", "formula": "Op + Inv + Fin = Net Change", "doc_scope": ["cash_flow"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "CF-2", "rule_name": "Cash Reconciliation", "formula": "Beg + Net = End", "doc_scope": ["cash_flow"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "CF-3", "rule_name": "Positive Ending Cash", "formula": "Ending Cash >= 0", "doc_scope": ["cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "CF-4", "rule_name": "Cash Operating Constant", "formula": "CF.0122 = 3375.45", "doc_scope": ["cash_flow"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "CF-5", "rule_name": "Op Cash Concentration", "formula": "Analysis", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-6", "rule_name": "Indirect Method Logic", "formula": "CF = NI + Adj", "doc_scope": ["cash_flow"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "CF-7", "rule_name": "Depr Add-Back", "formula": "Depr >= 0", "doc_scope": ["cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "CF-8", "rule_name": "A/R Adjustment", "formula": "Tracking", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-9", "rule_name": "A/P Adjustment", "formula": "Tracking", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-10", "rule_name": "Prepaid Adj", "formula": "Tracking", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-11", "rule_name": "Accrued Adj", "formula": "Tracking", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-12", "rule_name": "CapEx Outflow", "formula": "CapEx <= 0", "doc_scope": ["cash_flow"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "CF-13", "rule_name": "Escrow Tax Adj", "formula": "Tracking", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-14", "rule_name": "Mortgage Principal", "formula": "Principal <= 0", "doc_scope": ["cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "CF-15", "rule_name": "Distributions", "formula": "Distributions <= 0", "doc_scope": ["cash_flow"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "CF-16", "rule_name": "Lease Comm", "formula": "Lease Comm <= 0", "doc_scope": ["cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "CF-17", "rule_name": "Rent Advance Adj", "formula": "Tracking", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-18", "rule_name": "Tax Payable Adj", "formula": "Tracking", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-19", "rule_name": "YTD Accumulation", "formula": "YTD Calculation", "doc_scope": ["cash_flow"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "CF-20", "rule_name": "Operating Dominance", "formula": "Analysis", "doc_scope": ["cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "CF-21", "rule_name": "Seasonality", "formula": "Analysis", "doc_scope": ["cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "CF-22", "rule_name": "Major Uses", "formula": "Analysis", "doc_scope": ["cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "CF-23", "rule_name": "Major Sources", "formula": "Analysis", "doc_scope": ["cash_flow"], "severity": "low", "property_scope": {"all": True}},

            # ==================== INCOME STATEMENT (IS-1 to IS-27) ====================
            {"rule_id": "IS-1", "rule_name": "Net Income Verification", "formula": "NI = NOI - (Int+Depr+Amort)", "doc_scope": ["income_statement"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "IS-NOI", "rule_name": "NOI Calculation", "formula": "NOI = Rev - OpEx", "doc_scope": ["income_statement"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "IS-RATIO-1", "rule_name": "Expense Ratio Check", "formula": "OpEx / Rev target", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-MARGIN", "rule_name": "Operating Margin", "formula": "NOI / Rev > 30%", "doc_scope": ["income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "IS-PROFIT", "rule_name": "Profit Margin Non-Negative", "formula": "NI / Rev >= 0", "doc_scope": ["income_statement"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "IS-2", "rule_name": "YTD Formula", "formula": "YTD = Prior YTD + PTD", "doc_scope": ["income_statement"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "IS-3", "rule_name": "YTD Non-Decreasing", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "IS-4", "rule_name": "Total Income Exists", "formula": "Total Income > 0", "doc_scope": ["income_statement"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "IS-5", "rule_name": "Reimbursement Constants", "formula": "Tax/Ins Reimb Check", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-6", "rule_name": "Base Rent Variance", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "IS-7", "rule_name": "CAM Variance", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "IS-8", "rule_name": "Percentage Rent", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "IS-9", "rule_name": "Total Expense Check", "formula": "Total Exp > 0", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-10", "rule_name": "Property Tax Pattern", "formula": "Pattern Check", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-11", "rule_name": "Insurance Pattern", "formula": "Pattern Check", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-12", "rule_name": "Offsite Management Fee (4%)", "formula": "Fee = 4% Income", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-13", "rule_name": "Asset Mgmt Fee (1%)", "formula": "Fee = 1% Income", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-14", "rule_name": "Accounting Fee (~0.75%)", "formula": "Fee ~ 0.75% Income", "doc_scope": ["income_statement"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "IS-15", "rule_name": "Utilities", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "IS-16", "rule_name": "R&M Lighting Contract", "formula": "Cost = 4758.00", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-17", "rule_name": "Mortgage Interest Trend", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-18", "rule_name": "Depreciation Pattern", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-19", "rule_name": "Amortization Pattern", "formula": "Tracking", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "IS-20", "rule_name": "OpEx Ratio Alias", "formula": "Alias", "doc_scope": ["income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "IS-21", "rule_name": "NOI Margin", "formula": "NOI / Rev", "doc_scope": ["income_statement"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "IS-22", "rule_name": "Net Margin", "formula": "NI / Rev", "doc_scope": ["income_statement"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "IS-23", "rule_name": "Oct-Nov Check", "formula": "Manual", "doc_scope": ["income_statement"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "IS-24", "rule_name": "Nov-Dec Check", "formula": "Manual", "doc_scope": ["income_statement"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "IS-25", "rule_name": "State Taxes", "formula": "Usually 0", "doc_scope": ["income_statement"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "IS-26", "rule_name": "Parking Lot Sweeping", "formula": "Range Check", "doc_scope": ["income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "IS-27", "rule_name": "Landscaping Contract", "formula": "Contract Logic", "doc_scope": ["income_statement"], "severity": "medium", "property_scope": {"all": True}},

            # ==================== MORTGAGE (MST-1 to MST-14) ====================
            {"rule_id": "MST-1", "rule_name": "Payment Components", "formula": "Total = P + I + Escrows", "doc_scope": ["mortgage_statement"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "MST-2", "rule_name": "Principal Rollforward", "formula": "Curr Bal = Prior Bal - Pd Principal", "doc_scope": ["mortgage_statement"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "MST-3", "rule_name": "YTD Interest Roll", "formula": "Curr YTD = Prior YTD + Interest", "doc_scope": ["mortgage_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "MST-4", "rule_name": "Escrow Positive Balances", "formula": "Balances >= 0", "doc_scope": ["mortgage_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "MST-5", "rule_name": "Tax Escrow Roll", "formula": "Rollforward Logic", "doc_scope": ["mortgage_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "MST-6", "rule_name": "Reserve Roll", "formula": "Rollforward Logic", "doc_scope": ["mortgage_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "MST-7", "rule_name": "Principal Reduct Check", "formula": "Tracking", "doc_scope": ["mortgage_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "MST-8", "rule_name": "Payment Composition", "formula": "Tracking", "doc_scope": ["mortgage_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "MST-9", "rule_name": "Constant Payment", "formula": "Payment = 206734.24", "doc_scope": ["mortgage_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "MST-10", "rule_name": "Constant Escrows", "formula": "Constant Check", "doc_scope": ["mortgage_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "MST-11", "rule_name": "P+I Constant", "formula": "P+I = 125629.71", "doc_scope": ["mortgage_statement"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "MST-12", "rule_name": "Late Charge Calc", "formula": "Late = 5% Payment", "doc_scope": ["mortgage_statement"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "MST-13", "rule_name": "YTD Tracking", "formula": "Tracking", "doc_scope": ["mortgage_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "MST-14", "rule_name": "Interest Rate Check", "formula": "Rate = 4.78%", "doc_scope": ["mortgage_statement"], "severity": "info", "property_scope": {"all": True}},

            # ==================== RENT ROLL (RR-1 to RR-9) ====================
            {"rule_id": "RR-1", "rule_name": "Annual vs Monthly Rent", "formula": "Annual = Monthly * 12", "doc_scope": ["rent_roll"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "RR-2", "rule_name": "Occupancy Rate", "formula": "Occ Units / Total Units", "doc_scope": ["rent_roll"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "RR-3", "rule_name": "Vacancy Area Check", "formula": "Occ Area + Vac Area = Total Area", "doc_scope": ["rent_roll"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "RR-4", "rule_name": "Monthly Rent PSF", "formula": "Rent / Area", "doc_scope": ["rent_roll"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "RR-5", "rule_name": "Annual Rent PSF", "formula": "Annual / Area", "doc_scope": ["rent_roll"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "RR-6", "rule_name": "Petsmart Rent Check", "formula": "Tenant Check", "doc_scope": ["rent_roll"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "RR-7", "rule_name": "Spirit Halloween/Unit 600", "formula": "Seasonal Check", "doc_scope": ["rent_roll"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "RR-8", "rule_name": "Total Monthly Rent", "formula": "Total > 220k", "doc_scope": ["rent_roll"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "RR-9", "rule_name": "Vacant Unit Count", "formula": "Count [2,3]", "doc_scope": ["rent_roll"], "severity": "medium", "property_scope": {"all": True}},

            # ==================== THREE STATEMENT (3S-1 to 3S-22) ====================
            {"rule_id": "3S-1", "rule_name": "Cash Balance Check", "formula": "BS Cash = CF End Cash", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "3S-2", "rule_name": "Integration Logic", "formula": "Conceptual", "doc_scope": ["balance_sheet", "cash_flow", "income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "3S-3", "rule_name": "Net Income Logic", "formula": "IS Net Income = BS Earnings", "doc_scope": ["balance_sheet", "income_statement"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "3S-RE-1", "rule_name": "Net Income to RE Change", "formula": "IS NI = Delta Retained Earnings", "doc_scope": ["balance_sheet", "income_statement"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-4", "rule_name": "NI to CF Start", "formula": "IS NI = CF NI Line", "doc_scope": ["income_statement", "cash_flow"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "3S-5a", "rule_name": "Depr (IS vs CF)", "formula": "IS Depr = CF Depr", "doc_scope": ["income_statement", "cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-5b", "rule_name": "Depr (IS vs BS Delta)", "formula": "IS Depr = BS Delta Accum", "doc_scope": ["income_statement", "balance_sheet"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-5", "rule_name": "Depr Three-Way", "formula": "Alias", "doc_scope": ["balance_sheet", "cash_flow", "income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "3S-6", "rule_name": "Depr Complete", "formula": "Alias", "doc_scope": ["balance_sheet", "cash_flow", "income_statement"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "3S-7", "rule_name": "Amortization Flow", "formula": "IS Exp = CF AddBack", "doc_scope": ["income_statement", "cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-8", "rule_name": "Cash Flow Recon (BS Delta)", "formula": "CF Net Change = BS Cash Change", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "critical", "property_scope": {"all": True}},
            {"rule_id": "3S-9", "rule_name": "Cash Components", "formula": "Alias", "doc_scope": ["balance_sheet"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "3S-10", "rule_name": "A/R Three-Way", "formula": "CF = -Delta BS", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-11", "rule_name": "A/P Three-Way", "formula": "CF = Delta BS", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-12", "rule_name": "Property Tax Flow", "formula": "Manual", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "3S-13", "rule_name": "CapEx (TI) Flow", "formula": "|CF| = BS Delta", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "3S-14", "rule_name": "CapEx Future Depr", "formula": "Conceptual", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "3S-15", "rule_name": "Mortgage Principal Flow", "formula": "|CF| = BS Reduction", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-16", "rule_name": "Interest Flow", "formula": "Alias", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "3S-17", "rule_name": "Escrow Flow", "formula": "N/A", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "low", "property_scope": {"all": True}},
            {"rule_id": "3S-18", "rule_name": "Distributions Flow", "formula": "Tracking", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "medium", "property_scope": {"all": True}},
            {"rule_id": "3S-19", "rule_name": "Equity Recon", "formula": "Alias", "doc_scope": ["balance_sheet", "cash_flow"], "severity": "high", "property_scope": {"all": True}},
            {"rule_id": "3S-20", "rule_name": "Monthly Recon", "formula": "Meta Rule", "doc_scope": ["all"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "3S-21", "rule_name": "YTD Recon", "formula": "Meta Rule", "doc_scope": ["all"], "severity": "info", "property_scope": {"all": True}},
            {"rule_id": "3S-22", "rule_name": "Golden Rules", "formula": "N/A", "doc_scope": ["all"], "severity": "low", "property_scope": {"all": True}},
        ]

        # Sync rules to database
        db_rules = {r.rule_id: r for r in db.query(CalculatedRule).all()}

        print(f"Syncing {len(rules)} Python-defined rules to Database...")

        for r_data in rules:
            rule_id = r_data["rule_id"]
            
            # Check if exists
            if rule_id in db_rules:
                # Update existing
                rule = db_rules[rule_id]
                rule.rule_name = r_data["rule_name"]
                rule.formula = r_data["formula"] # Updating formula to match python logic desc
                rule.severity = r_data["severity"]
                rule.doc_scope = r_data["doc_scope"]
                # description?
            else:
                # Create new
                new_rule = CalculatedRule(
                    rule_id=rule_id,
                    rule_name=r_data["rule_name"],
                    description=f"{r_data['rule_name']} (Synced from Python)",
                    formula=r_data["formula"],
                    doc_scope=r_data["doc_scope"],
                    severity=r_data["severity"],
                    property_scope=r_data["property_scope"],
                    version=1,
                    is_active=True,
                    effective_date=date.today()
                )
                db.add(new_rule)
        
        # Optional: Deactivate rules not in Python list?
        # User said "update check to match actual rules running". 
        # So we should probably flag or delete extras.
        python_ids = set([r["rule_id"] for r in rules])
        for db_rule in db_rules.values():
            if db_rule.rule_id not in python_ids:
                print(f"Marking obsolete rule inactive: {db_rule.rule_id}")
                db_rule.is_active = False

        db.commit()
        print(f"✅ Successfully synced {len(rules)} calculated rules.")

    except Exception as e:
        print(f"❌ Error seeding calculated rules: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_calculated_rules()
