-- Fine-Tuned Forensic Reconciliation Materialized Views
-- Based on actual data patterns discovered from October 2023 ESP001 data
-- Created: 2025-12-25

-- Drop existing views
DROP MATERIALIZED VIEW IF EXISTS forensic_reconciliation_master CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cash_flow_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS income_statement_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS balance_sheet_summary CASCADE;

-- ============================================================================
-- View 1: Balance Sheet Summary (FINE-TUNED)
-- ============================================================================
-- Pattern discovered: Totals use account codes ending in 99-9000 or 999-0000
-- Examples: 0499-9000 (Current Assets), 1999-0000 (TOTAL ASSETS),
--           2999-0000 (TOTAL LIABILITIES), 3999-0000 (TOTAL CAPITAL)

CREATE MATERIALIZED VIEW balance_sheet_summary AS
SELECT
    bs.property_id,
    bs.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Total Assets (account_code = '1999-0000')
    COALESCE(SUM(CASE
        WHEN bs.account_code = '1999-0000'
        THEN bs.amount
        ELSE 0
    END), 0) as total_assets,

    -- Total Current Assets (account_code = '0499-9000')
    COALESCE(SUM(CASE
        WHEN bs.account_code = '0499-9000'
        THEN bs.amount
        ELSE 0
    END), 0) as total_current_assets,

    -- Cash (codes 0121-0000, 0122-0000)
    COALESCE(SUM(CASE
        WHEN bs.account_code IN ('0121-0000', '0122-0000')
        THEN bs.amount
        ELSE 0
    END), 0) as cash,

    -- Total Liabilities (account_code = '2999-0000')
    COALESCE(SUM(CASE
        WHEN bs.account_code = '2999-0000'
        THEN bs.amount
        ELSE 0
    END), 0) as total_liabilities,

    -- Total Current Liabilities (account_code = '2590-0000')
    COALESCE(SUM(CASE
        WHEN bs.account_code = '2590-0000'
        THEN bs.amount
        ELSE 0
    END), 0) as total_current_liabilities,

    -- Long-Term Debt (account_code = '2700-0000' Wells Fargo mortgage)
    -- This is the CRITICAL field for mortgage principal tie-out
    COALESCE(SUM(CASE
        WHEN bs.account_code = '2700-0000'
        OR bs.account_code = '2900-0000'  -- Total Long Term Liabilities
        THEN bs.amount
        ELSE 0
    END), 0) as long_term_debt,

    -- Total Equity/Capital (account_code = '3999-0000')
    COALESCE(SUM(CASE
        WHEN bs.account_code = '3999-0000'
        THEN bs.amount
        ELSE 0
    END), 0) as total_equity,

    -- Retained Earnings / Current Period Earnings (account_code = '3995-0000')
    COALESCE(SUM(CASE
        WHEN bs.account_code = '3995-0000'
        OR bs.account_name ILIKE '%Current Period Earnings%'
        THEN bs.amount
        ELSE 0
    END), 0) as retained_earnings,

    -- Tenant Deposits (account_code = '2520-0000')
    COALESCE(SUM(CASE
        WHEN bs.account_code = '2520-0000'
        OR bs.account_name ILIKE '%Deposit Refundable to Tenant%'
        THEN bs.amount
        ELSE 0
    END), 0) as tenant_deposits,

    -- Escrow Accounts (codes 1310-0000, 1320-0000, 1330-0000)
    COALESCE(SUM(CASE
        WHEN bs.account_code IN ('1310-0000', '1320-0000', '1330-0000')
        THEN bs.amount
        ELSE 0
    END), 0) as escrow_accounts,

    -- Metadata
    MAX(bs.extraction_confidence) as avg_extraction_confidence,
    COUNT(DISTINCT bs.id) as line_item_count,
    MIN(bs.created_at) as first_extraction_date,
    MAX(bs.updated_at) as last_updated

FROM balance_sheet_data bs
JOIN properties p ON p.id = bs.property_id
JOIN financial_periods fp ON fp.id = bs.period_id
GROUP BY bs.property_id, bs.period_id, p.property_code, p.property_name,
         fp.period_year, fp.period_month;

CREATE UNIQUE INDEX idx_bs_summary_property_period
    ON balance_sheet_summary(property_id, period_id);

CREATE INDEX idx_bs_summary_period
    ON balance_sheet_summary(period_year, period_month);

-- ============================================================================
-- View 2: Income Statement Summary (FINE-TUNED)
-- ============================================================================
-- Pattern discovered:
-- - Account code 6299-0000 = NET OPERATING INCOME (NOI)
-- - Account code 9090-0000 = NET INCOME
-- - Rental income = code 4010-0000
-- - Interest expense = code 7010-0000

CREATE MATERIALIZED VIEW income_statement_summary AS
SELECT
    ist.property_id,
    ist.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Total Income (sum all income codes 4xxx-xxxx)
    COALESCE(SUM(CASE
        WHEN ist.account_code LIKE '4%'
        AND ist.account_code NOT IN ('4060-0000')  -- Exclude Annual Cams adjustment
        THEN ist.period_amount
        ELSE 0
    END), 0) as total_income,

    -- Rental Income (CRITICAL for Rent Roll tie-out)
    -- Account code 4010-0000 = Base Rentals
    COALESCE(SUM(CASE
        WHEN ist.account_code = '4010-0000'
        THEN ist.period_amount
        ELSE 0
    END), 0) as rental_income,

    -- Other Income (all 4xxx except base rentals)
    COALESCE(SUM(CASE
        WHEN ist.account_code LIKE '4%'
        AND ist.account_code != '4010-0000'
        AND ist.account_code != '4060-0000'  -- Exclude adjustment
        THEN ist.period_amount
        ELSE 0
    END), 0) as other_income,

    -- Total Operating Expenses (sum all 5xxx and 6xxx codes)
    COALESCE(SUM(CASE
        WHEN (ist.account_code LIKE '5%' OR ist.account_code LIKE '6%')
        AND ist.account_code NOT IN ('6299-0000')  -- Exclude NOI line
        THEN ist.period_amount
        ELSE 0
    END), 0) as total_operating_expenses,

    -- NOI (CRITICAL for DSCR calculation)
    -- Account code 6299-0000 = NET OPERATING INCOME
    COALESCE(SUM(CASE
        WHEN ist.account_code = '6299-0000'
        THEN ist.period_amount
        ELSE 0
    END), 0) as noi,

    -- Interest Expense (CRITICAL for Mortgage tie-out)
    -- Account code 7010-0000 = Mortgage Interest
    COALESCE(SUM(CASE
        WHEN ist.account_code = '7010-0000'
        THEN ist.period_amount
        ELSE 0
    END), 0) as interest_expense,

    -- Depreciation (account code 7020-0000)
    COALESCE(SUM(CASE
        WHEN ist.account_code = '7020-0000'
        THEN ist.period_amount
        ELSE 0
    END), 0) as depreciation_expense,

    -- Net Income (account code 9090-0000)
    COALESCE(SUM(CASE
        WHEN ist.account_code = '9090-0000'
        THEN ist.period_amount
        ELSE 0
    END), 0) as net_income,

    -- Metadata
    MAX(ist.extraction_confidence) as avg_extraction_confidence,
    COUNT(DISTINCT ist.id) as line_item_count,
    MIN(ist.created_at) as first_extraction_date,
    MAX(ist.updated_at) as last_updated

FROM income_statement_data ist
JOIN properties p ON p.id = ist.property_id
JOIN financial_periods fp ON fp.id = ist.period_id
GROUP BY ist.property_id, ist.period_id, p.property_code, p.property_name,
         fp.period_year, fp.period_month;

CREATE UNIQUE INDEX idx_is_summary_property_period
    ON income_statement_summary(property_id, period_id);

CREATE INDEX idx_is_summary_period
    ON income_statement_summary(period_year, period_month);

-- ============================================================================
-- View 3: Cash Flow Summary (FINE-TUNED)
-- ============================================================================
-- Pattern discovered:
-- - Cash flow uses period_amount field
-- - Beginning cash: codes 0121-0000 + 0122-0000 (from Balance Sheet prior period)
-- - Operating CF: sum of line_section = 'INCOME' + operating expenses
-- - Financing CF: includes distributions (3990-0000), debt payments (2700-0000)
-- - Debt service: account code 7010-0000 (mortgage interest) from IS

CREATE MATERIALIZED VIEW cash_flow_summary AS
SELECT
    cf.property_id,
    cf.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Beginning Cash (cash accounts from start of period)
    -- Use current cash from balance sheet as proxy
    COALESCE(SUM(CASE
        WHEN cf.account_code IN ('0121-0000', '0122-0000')
        AND cf.line_category LIKE '%Operating%'
        THEN cf.period_amount
        ELSE 0
    END), 0) as beginning_cash,

    -- Operating Cash Flow (all income minus operating expenses)
    -- Include section = 'INCOME' and cash_flow_category = 'operating'
    COALESCE(SUM(CASE
        WHEN cf.line_section = 'INCOME'
        OR (cf.cash_flow_category = 'operating' AND cf.account_code LIKE '5%')
        OR (cf.cash_flow_category = 'operating' AND cf.account_code LIKE '6%')
        THEN cf.period_amount
        ELSE 0
    END), 0) as operating_cash_flow,

    -- Investing Activities (cash_flow_category = 'investing')
    COALESCE(SUM(CASE
        WHEN cf.cash_flow_category = 'investing'
        THEN cf.period_amount
        ELSE 0
    END), 0) as investing_cash_flow,

    -- Financing Activities (cash_flow_category = 'financing')
    COALESCE(SUM(CASE
        WHEN cf.cash_flow_category = 'financing'
        THEN cf.period_amount
        ELSE 0
    END), 0) as financing_cash_flow,

    -- Debt Service Payment (CRITICAL for DSCR tie-out)
    -- Wells Fargo payment (2700-0000) + mortgage interest (7010-0000)
    COALESCE(ABS(SUM(CASE
        WHEN cf.account_code = '2700-0000'
        AND cf.cash_flow_category = 'financing'
        THEN cf.period_amount
        ELSE 0
    END)), 0) as debt_service_payment,

    -- Net Change in Cash
    COALESCE(SUM(cf.period_amount), 0) as net_change_in_cash,

    -- Ending Cash
    -- Sum of all cash movements
    COALESCE(SUM(CASE
        WHEN cf.account_code IN ('0121-0000', '0122-0000')
        THEN cf.period_amount
        ELSE 0
    END), 0) as ending_cash,

    -- Metadata
    MAX(cf.extraction_confidence) as avg_extraction_confidence,
    COUNT(DISTINCT cf.id) as line_item_count,
    MIN(cf.created_at) as first_extraction_date,
    MAX(cf.updated_at) as last_updated

FROM cash_flow_data cf
JOIN properties p ON p.id = cf.property_id
JOIN financial_periods fp ON fp.id = cf.period_id
GROUP BY cf.property_id, cf.period_id, p.property_code, p.property_name,
         fp.period_year, fp.period_month;

CREATE UNIQUE INDEX idx_cf_summary_property_period
    ON cash_flow_summary(property_id, period_id);

CREATE INDEX idx_cf_summary_period
    ON cash_flow_summary(period_year, period_month);
