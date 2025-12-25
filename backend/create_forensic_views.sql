-- Create Forensic Reconciliation Materialized Views
-- Big 5 Level Cross-Document Reconciliation

-- Drop existing views if they exist
DROP MATERIALIZED VIEW IF EXISTS forensic_reconciliation_master CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cash_flow_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS income_statement_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS balance_sheet_summary CASCADE;

-- View 1: Balance Sheet Summary
CREATE MATERIALIZED VIEW balance_sheet_summary AS
SELECT
    bs.property_id,
    bs.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Total Assets
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'ASSETS' AND bs.is_total = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_assets,

    -- Current Assets
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'ASSETS'
        AND bs.account_subcategory LIKE '%Current%'
        AND bs.is_subtotal = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_current_assets,

    -- Cash
    COALESCE(SUM(CASE
        WHEN bs.account_code LIKE '1010%'
        OR bs.account_name ILIKE '%cash%'
        OR bs.account_name ILIKE '%bank%'
        THEN bs.amount
        ELSE 0
    END), 0) as cash,

    -- Total Liabilities
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'LIABILITIES' AND bs.is_total = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_liabilities,

    -- Current Liabilities
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'LIABILITIES'
        AND bs.account_subcategory LIKE '%Current%'
        AND bs.is_subtotal = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_current_liabilities,

    -- Long-Term Debt (for Mortgage tie-out)
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'LIABILITIES'
        AND (bs.account_subcategory ILIKE '%Long%Term%'
             OR bs.account_subcategory ILIKE '%Long-Term%'
             OR bs.account_name ILIKE '%Mortgage%'
             OR bs.account_name ILIKE '%Note%Payable%'
             OR bs.account_code LIKE '2%')
        AND bs.account_subcategory NOT ILIKE '%Current%'
        THEN bs.amount
        ELSE 0
    END), 0) as long_term_debt,

    -- Total Equity
    COALESCE(SUM(CASE
        WHEN bs.account_category IN ('CAPITAL', 'EQUITY') AND bs.is_total = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_equity,

    -- Retained Earnings
    COALESCE(SUM(CASE
        WHEN bs.account_name ILIKE '%Retained%Earnings%'
        OR bs.account_name ILIKE '%Accumulated%Earnings%'
        THEN bs.amount
        ELSE 0
    END), 0) as retained_earnings,

    -- Tenant Deposits
    COALESCE(SUM(CASE
        WHEN bs.account_name ILIKE '%Tenant%Deposit%'
        OR bs.account_name ILIKE '%Security%Deposit%'
        THEN bs.amount
        ELSE 0
    END), 0) as tenant_deposits,

    -- Escrow Accounts
    COALESCE(SUM(CASE
        WHEN bs.account_name ILIKE '%Escrow%'
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

-- View 2: Income Statement Summary
CREATE MATERIALIZED VIEW income_statement_summary AS
SELECT
    ist.property_id,
    ist.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Total Income
    COALESCE(SUM(CASE
        WHEN ist.account_category = 'INCOME' AND ist.is_total = TRUE
        THEN ist.amount
        ELSE 0
    END), 0) as total_income,

    -- Rental Income
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Rental%Income%'
        OR ist.account_name ILIKE '%Rent%Income%'
        OR ist.account_code LIKE '40%'
        THEN ist.amount
        ELSE 0
    END), 0) as rental_income,

    -- Other Income
    COALESCE(SUM(CASE
        WHEN ist.account_category = 'INCOME'
        AND ist.account_name NOT ILIKE '%Rental%'
        AND ist.account_name NOT ILIKE '%Rent%'
        AND ist.is_total = FALSE
        THEN ist.amount
        ELSE 0
    END), 0) as other_income,

    -- Total Operating Expenses
    COALESCE(SUM(CASE
        WHEN ist.account_category = 'OPERATING_EXPENSE' AND ist.is_total = TRUE
        THEN ist.amount
        ELSE 0
    END), 0) as total_operating_expenses,

    -- NOI
    COALESCE(SUM(CASE
        WHEN ist.account_category = 'INCOME' AND ist.is_total = TRUE
        THEN ist.amount
        ELSE 0
    END), 0) - COALESCE(SUM(CASE
        WHEN ist.account_category = 'OPERATING_EXPENSE' AND ist.is_total = TRUE
        THEN ist.amount
        ELSE 0
    END), 0) as noi,

    -- Interest Expense
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Interest%Expense%'
        OR ist.account_name ILIKE '%Mortgage%Interest%'
        OR ist.account_code LIKE '7%'
        THEN ist.amount
        ELSE 0
    END), 0) as interest_expense,

    -- Depreciation
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Depreciation%'
        THEN ist.amount
        ELSE 0
    END), 0) as depreciation_expense,

    -- Net Income
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Net%Income%'
        OR ist.account_name ILIKE '%Net%Loss%'
        OR (ist.is_total = TRUE AND ist.account_category = 'NET_INCOME')
        THEN ist.amount
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

-- View 3: Cash Flow Summary
CREATE MATERIALIZED VIEW cash_flow_summary AS
SELECT
    cf.property_id,
    cf.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Beginning Cash
    COALESCE(SUM(CASE
        WHEN cf.account_name ILIKE '%Beginning%Cash%'
        OR cf.account_name ILIKE '%Cash%Beginning%'
        THEN cf.amount
        ELSE 0
    END), 0) as beginning_cash,

    -- Operating Activities
    COALESCE(SUM(CASE
        WHEN cf.activity_category = 'OPERATING'
        OR cf.account_category = 'OPERATING'
        THEN cf.amount
        ELSE 0
    END), 0) as operating_cash_flow,

    -- Investing Activities
    COALESCE(SUM(CASE
        WHEN cf.activity_category = 'INVESTING'
        OR cf.account_category = 'INVESTING'
        THEN cf.amount
        ELSE 0
    END), 0) as investing_cash_flow,

    -- Financing Activities
    COALESCE(SUM(CASE
        WHEN cf.activity_category = 'FINANCING'
        OR cf.account_category = 'FINANCING'
        THEN cf.amount
        ELSE 0
    END), 0) as financing_cash_flow,

    -- Debt Service Payment
    COALESCE(SUM(CASE
        WHEN cf.account_name ILIKE '%Debt%Service%'
        OR cf.account_name ILIKE '%Mortgage%Payment%'
        OR cf.account_name ILIKE '%Loan%Payment%'
        THEN cf.amount
        ELSE 0
    END), 0) as debt_service_payment,

    -- Net Change
    COALESCE(SUM(CASE
        WHEN cf.account_name ILIKE '%Net%Change%'
        OR cf.account_name ILIKE '%Change%Cash%'
        OR (cf.is_total = TRUE AND cf.account_category NOT IN ('BEGINNING', 'ENDING'))
        THEN cf.amount
        ELSE 0
    END), 0) as net_change_in_cash,

    -- Ending Cash
    COALESCE(SUM(CASE
        WHEN cf.account_name ILIKE '%Ending%Cash%'
        OR cf.account_name ILIKE '%Cash%Ending%'
        THEN cf.amount
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
