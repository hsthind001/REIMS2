-- Create Forensic Reconciliation Materialized Views (CORRECTED)
-- Big 5 Level Cross-Document Reconciliation
-- Schema-corrected version matching actual REIMS2 database

-- Drop existing views if they exist
DROP MATERIALIZED VIEW IF EXISTS forensic_reconciliation_master CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cash_flow_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS income_statement_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS balance_sheet_summary CASCADE;

-- ============================================================================
-- View 1: Balance Sheet Summary
-- ============================================================================
CREATE MATERIALIZED VIEW balance_sheet_summary AS
SELECT
    bs.property_id,
    bs.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Total Assets (use account_category from actual schema)
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'ASSETS' AND bs.is_total = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_assets,

    -- Current Assets
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'ASSETS'
        AND bs.account_subcategory ILIKE '%Current%'
        AND bs.is_subtotal = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_current_assets,

    -- Cash (multiple patterns for matching)
    COALESCE(SUM(CASE
        WHEN (bs.account_code ILIKE '101%'
        OR bs.account_name ILIKE '%cash%'
        OR bs.account_name ILIKE '%bank%'
        OR bs.account_name ILIKE '%checking%'
        OR bs.account_name ILIKE '%money market%')
        AND bs.is_subtotal = FALSE
        AND bs.is_total = FALSE
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
        AND bs.account_subcategory ILIKE '%Current%'
        AND bs.is_subtotal = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_current_liabilities,

    -- Long-Term Debt (CRITICAL for Mortgage tie-out)
    COALESCE(SUM(CASE
        WHEN bs.account_category = 'LIABILITIES'
        AND (bs.account_subcategory ILIKE '%Long%Term%'
             OR bs.account_subcategory ILIKE '%Long-Term%'
             OR bs.account_name ILIKE '%Mortgage%'
             OR bs.account_name ILIKE '%Note%Payable%'
             OR bs.account_name ILIKE '%Loan%Payable%'
             OR bs.account_code ILIKE '2%')
        AND bs.account_subcategory NOT ILIKE '%Current%'
        AND bs.is_subtotal = FALSE
        AND bs.is_total = FALSE
        THEN bs.amount
        ELSE 0
    END), 0) as long_term_debt,

    -- Total Equity (account_category could be CAPITAL or EQUITY)
    COALESCE(SUM(CASE
        WHEN bs.account_category IN ('CAPITAL', 'EQUITY', 'OWNER EQUITY', 'OWNERS EQUITY')
        AND bs.is_total = TRUE
        THEN bs.amount
        ELSE 0
    END), 0) as total_equity,

    -- Retained Earnings
    COALESCE(SUM(CASE
        WHEN bs.account_name ILIKE '%Retained%Earnings%'
        OR bs.account_name ILIKE '%Accumulated%Earnings%'
        OR bs.account_name ILIKE '%Retained%Income%'
        THEN bs.amount
        ELSE 0
    END), 0) as retained_earnings,

    -- Tenant Deposits
    COALESCE(SUM(CASE
        WHEN bs.account_name ILIKE '%Tenant%Deposit%'
        OR bs.account_name ILIKE '%Security%Deposit%'
        OR bs.account_name ILIKE '%Resident%Deposit%'
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
    AVG(bs.extraction_confidence) as avg_extraction_confidence,
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
-- View 2: Income Statement Summary
-- ============================================================================
CREATE MATERIALIZED VIEW income_statement_summary AS
SELECT
    ist.property_id,
    ist.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,

    -- Total Income (using line_category from actual schema, period_amount for current period)
    COALESCE(SUM(CASE
        WHEN (ist.line_category ILIKE '%Income%'
              OR ist.line_category ILIKE '%Revenue%'
              OR ist.is_income = TRUE)
        AND ist.is_total = TRUE
        THEN ist.period_amount
        ELSE 0
    END), 0) as total_income,

    -- Rental Income (CRITICAL for Rent Roll tie-out)
    COALESCE(SUM(CASE
        WHEN (ist.account_name ILIKE '%Rental%Income%'
        OR ist.account_name ILIKE '%Rent%Income%'
        OR ist.account_name ILIKE '%Rental%Revenue%'
        OR ist.account_code ILIKE '4%')
        AND ist.is_subtotal = FALSE
        AND ist.is_total = FALSE
        THEN ist.period_amount
        ELSE 0
    END), 0) as rental_income,

    -- Other Income
    COALESCE(SUM(CASE
        WHEN (ist.line_category ILIKE '%Income%' OR ist.is_income = TRUE)
        AND ist.account_name NOT ILIKE '%Rental%'
        AND ist.account_name NOT ILIKE '%Rent%'
        AND ist.is_total = FALSE
        AND ist.is_subtotal = FALSE
        THEN ist.period_amount
        ELSE 0
    END), 0) as other_income,

    -- Total Operating Expenses
    COALESCE(SUM(CASE
        WHEN (ist.line_category ILIKE '%Expense%'
              OR ist.line_category ILIKE '%Operating%Expense%'
              OR ist.is_income = FALSE)
        AND ist.is_below_the_line = FALSE
        AND ist.is_total = TRUE
        THEN ist.period_amount
        ELSE 0
    END), 0) as total_operating_expenses,

    -- NOI (Total Income - Operating Expenses) - CRITICAL for DSCR
    COALESCE(SUM(CASE
        WHEN (ist.line_category ILIKE '%Income%' OR ist.is_income = TRUE)
        AND ist.is_total = TRUE
        THEN ist.period_amount
        ELSE 0
    END), 0) - COALESCE(SUM(CASE
        WHEN (ist.line_category ILIKE '%Expense%' OR ist.is_income = FALSE)
        AND ist.is_below_the_line = FALSE
        AND ist.is_total = TRUE
        THEN ist.period_amount
        ELSE 0
    END), 0) as noi,

    -- Interest Expense (CRITICAL for Mortgage tie-out)
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Interest%Expense%'
        OR ist.account_name ILIKE '%Mortgage%Interest%'
        OR ist.account_name ILIKE '%Loan%Interest%'
        OR ist.account_code ILIKE '7%'
        THEN ist.period_amount
        ELSE 0
    END), 0) as interest_expense,

    -- Depreciation
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Depreciation%'
        OR ist.account_name ILIKE '%Amortization%'
        THEN ist.period_amount
        ELSE 0
    END), 0) as depreciation_expense,

    -- Net Income
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Net%Income%'
        OR ist.account_name ILIKE '%Net%Loss%'
        OR ist.account_name ILIKE '%Bottom%Line%'
        THEN ist.period_amount
        ELSE 0
    END), 0) as net_income,

    -- YTD versions for comparison
    COALESCE(SUM(CASE
        WHEN ist.account_name ILIKE '%Interest%Expense%'
        OR ist.account_name ILIKE '%Mortgage%Interest%'
        THEN ist.ytd_amount
        ELSE 0
    END), 0) as ytd_interest_expense,

    -- Metadata
    AVG(ist.extraction_confidence) as avg_extraction_confidence,
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
-- View 3: Cash Flow Summary
-- ============================================================================
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
        OR cf.account_name ILIKE '%Cash%Start%'
        OR cf.line_section ILIKE '%Beginning%'
        THEN cf.period_amount
        ELSE 0
    END), 0) as beginning_cash,

    -- Operating Activities (using cash_flow_category from actual schema)
    COALESCE(SUM(CASE
        WHEN cf.cash_flow_category = 'OPERATING'
        OR cf.line_category ILIKE '%Operating%'
        OR cf.line_section ILIKE '%Operating%'
        THEN cf.period_amount
        ELSE 0
    END), 0) as operating_cash_flow,

    -- Investing Activities
    COALESCE(SUM(CASE
        WHEN cf.cash_flow_category = 'INVESTING'
        OR cf.line_category ILIKE '%Investing%'
        OR cf.line_section ILIKE '%Investing%'
        THEN cf.period_amount
        ELSE 0
    END), 0) as investing_cash_flow,

    -- Financing Activities
    COALESCE(SUM(CASE
        WHEN cf.cash_flow_category = 'FINANCING'
        OR cf.line_category ILIKE '%Financing%'
        OR cf.line_section ILIKE '%Financing%'
        THEN cf.period_amount
        ELSE 0
    END), 0) as financing_cash_flow,

    -- Debt Service Payment (CRITICAL for Mortgage tie-out)
    COALESCE(SUM(CASE
        WHEN cf.account_name ILIKE '%Debt%Service%'
        OR cf.account_name ILIKE '%Mortgage%Payment%'
        OR cf.account_name ILIKE '%Loan%Payment%'
        OR cf.account_name ILIKE '%Principal%Payment%'
        THEN ABS(cf.period_amount)  -- Use ABS as payments are usually negative
        ELSE 0
    END), 0) as debt_service_payment,

    -- Net Change in Cash
    COALESCE(SUM(CASE
        WHEN cf.account_name ILIKE '%Net%Change%'
        OR cf.account_name ILIKE '%Change%Cash%'
        OR cf.account_name ILIKE '%Increase%Decrease%'
        OR (cf.is_total = TRUE AND cf.line_section NOT ILIKE '%Beginning%' AND cf.line_section NOT ILIKE '%Ending%')
        THEN cf.period_amount
        ELSE 0
    END), 0) as net_change_in_cash,

    -- Ending Cash (CRITICAL for Balance Sheet tie-out)
    COALESCE(SUM(CASE
        WHEN cf.account_name ILIKE '%Ending%Cash%'
        OR cf.account_name ILIKE '%Cash%Ending%'
        OR cf.account_name ILIKE '%Cash%End%'
        OR cf.line_section ILIKE '%Ending%'
        THEN cf.period_amount
        ELSE 0
    END), 0) as ending_cash,

    -- Metadata
    AVG(cf.extraction_confidence) as avg_extraction_confidence,
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

-- ============================================================================
-- View 4: Master Reconciliation View (with all tie-outs and metrics)
-- ============================================================================
CREATE MATERIALIZED VIEW forensic_reconciliation_master AS
SELECT
    p.id as property_id,
    p.property_code,
    p.property_name,
    fp.id as period_id,
    fp.period_year,
    fp.period_month,

    -- Balance Sheet Summary
    bs.total_assets,
    bs.total_current_assets,
    bs.cash as bs_cash,
    bs.total_liabilities,
    bs.total_current_liabilities,
    bs.long_term_debt as bs_long_term_debt,
    bs.total_equity,
    bs.retained_earnings,
    bs.tenant_deposits as bs_tenant_deposits,
    bs.escrow_accounts as bs_escrow_accounts,
    bs.avg_extraction_confidence as bs_confidence,

    -- Income Statement Summary
    ist.total_income,
    ist.rental_income as is_rental_income,
    ist.other_income,
    ist.total_operating_expenses,
    ist.noi,
    ist.interest_expense as is_interest_expense,
    ist.ytd_interest_expense,
    ist.depreciation_expense,
    ist.net_income,
    ist.avg_extraction_confidence as is_confidence,

    -- Cash Flow Summary
    cf.beginning_cash,
    cf.operating_cash_flow,
    cf.investing_cash_flow,
    cf.financing_cash_flow,
    cf.debt_service_payment as cf_debt_service,
    cf.net_change_in_cash,
    cf.ending_cash as cf_ending_cash,
    cf.avg_extraction_confidence as cf_confidence,

    -- Rent Roll Summary
    rr.total_units,
    rr.occupied_units,
    rr.vacant_units,
    rr.occupancy_rate,
    rr.total_monthly_rent,
    (rr.total_monthly_rent * 12) as rr_annual_rent,
    rr.total_square_footage,
    rr.extraction_confidence as rr_confidence,

    -- Mortgage Statement Summary
    mst.loan_number,
    mst.principal_balance as mst_principal_balance,
    mst.interest_rate,
    mst.principal_due,
    mst.interest_due as mst_interest_due,
    mst.tax_escrow_due,
    mst.insurance_escrow_due,
    mst.total_payment_due as mst_total_payment,
    mst.ytd_principal_paid,
    mst.ytd_interest_paid,
    mst.annual_debt_service,
    mst.monthly_debt_service,
    mst.tax_escrow_balance as mst_tax_escrow_balance,
    mst.insurance_escrow_balance as mst_insurance_escrow_balance,
    (mst.tax_escrow_balance + mst.insurance_escrow_balance) as mst_total_escrow,
    mst.extraction_confidence as mst_confidence,

    -- ======== CRITICAL TIE-OUT CALCULATIONS ========

    -- Tie-Out #1: Mortgage Principal → Balance Sheet Debt
    ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) as tieout_1_variance,
    CASE
        WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 'PASS'
        WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 1000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_1_status,

    -- Tie-Out #2: Mortgage Payment → Cash Flow Debt Service
    ABS(COALESCE(mst.total_payment_due, 0) - COALESCE(cf.debt_service_payment, 0)) as tieout_2_variance,
    CASE
        WHEN ABS(COALESCE(mst.total_payment_due, 0) - COALESCE(cf.debt_service_payment, 0)) <= 10 THEN 'PASS'
        WHEN ABS(COALESCE(mst.total_payment_due, 0) - COALESCE(cf.debt_service_payment, 0)) <= 100 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_2_status,

    -- Tie-Out #3: Cash Flow Ending → Balance Sheet Cash
    ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) as tieout_3_variance,
    CASE
        WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 10 THEN 'PASS'
        WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 100 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_3_status,

    -- Tie-Out #4: Balance Sheet Equation
    ABS((COALESCE(bs.total_assets, 0)) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) as tieout_4_variance,
    CASE
        WHEN ABS((COALESCE(bs.total_assets, 0)) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) <= 1 THEN 'PASS'
        WHEN ABS((COALESCE(bs.total_assets, 0)) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) <= 100 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_4_status,

    -- Tie-Out #5: Cash Flow Reconciliation
    ABS((COALESCE(cf.beginning_cash, 0) + COALESCE(cf.net_change_in_cash, 0)) - COALESCE(cf.ending_cash, 0)) as tieout_5_variance,
    CASE
        WHEN ABS((COALESCE(cf.beginning_cash, 0) + COALESCE(cf.net_change_in_cash, 0)) - COALESCE(cf.ending_cash, 0)) <= 1 THEN 'PASS'
        WHEN ABS((COALESCE(cf.beginning_cash, 0) + COALESCE(cf.net_change_in_cash, 0)) - COALESCE(cf.ending_cash, 0)) <= 100 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_5_status,

    -- Tie-Out #6: Rent Roll → Income Statement
    ABS(COALESCE((rr.total_monthly_rent * 12), 0) - COALESCE(ist.rental_income, 0)) as tieout_6_variance,
    CASE
        WHEN ABS(COALESCE((rr.total_monthly_rent * 12), 0) - COALESCE(ist.rental_income, 0)) <= 1000 THEN 'PASS'
        WHEN ABS(COALESCE((rr.total_monthly_rent * 12), 0) - COALESCE(ist.rental_income, 0)) <= 10000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_6_status,

    -- Tie-Out #7: Mortgage Interest → Income Statement
    ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) as tieout_7_variance,
    CASE
        WHEN ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) <= 100 THEN 'PASS'
        WHEN ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) <= 1000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_7_status,

    -- ======== BUSINESS METRICS ========

    -- DSCR (Debt Service Coverage Ratio)
    CASE
        WHEN COALESCE(mst.annual_debt_service, 0) > 0
        THEN ROUND((COALESCE(ist.noi, 0) / COALESCE(mst.annual_debt_service, 1))::numeric, 2)
        ELSE NULL
    END as dscr,

    -- DSCR Status
    CASE
        WHEN COALESCE(mst.annual_debt_service, 0) > 0 AND (COALESCE(ist.noi, 0) / COALESCE(mst.annual_debt_service, 1)) >= 1.25
        THEN 'PASS'
        WHEN COALESCE(mst.annual_debt_service, 0) > 0 AND (COALESCE(ist.noi, 0) / COALESCE(mst.annual_debt_service, 1)) >= 1.0
        THEN 'WARNING'
        WHEN COALESCE(mst.annual_debt_service, 0) > 0
        THEN 'CRITICAL'
        ELSE 'N/A'
    END as dscr_status,

    -- Cash Flow Coverage
    CASE
        WHEN COALESCE(mst.annual_debt_service, 0) > 0
        THEN ROUND((COALESCE(cf.operating_cash_flow, 0) / COALESCE(mst.annual_debt_service, 1))::numeric, 2)
        ELSE NULL
    END as cash_flow_coverage,

    -- Occupancy Status
    CASE
        WHEN COALESCE(rr.occupancy_rate, 0) >= 80 THEN 'PASS'
        WHEN COALESCE(rr.occupancy_rate, 0) >= 70 THEN 'WARNING'
        ELSE 'CRITICAL'
    END as occupancy_status,

    -- NOI Status
    CASE
        WHEN COALESCE(ist.noi, 0) > 0 THEN 'PASS'
        WHEN COALESCE(ist.noi, 0) = 0 THEN 'WARNING'
        ELSE 'CRITICAL'
    END as noi_status,

    -- Overall Quality Score (0-100)
    ROUND((
        COALESCE(bs.avg_extraction_confidence, 0) * 0.2 +
        COALESCE(ist.avg_extraction_confidence, 0) * 0.2 +
        COALESCE(cf.avg_extraction_confidence, 0) * 0.2 +
        COALESCE(rr.extraction_confidence, 0) * 0.2 +
        COALESCE(mst.extraction_confidence, 0) * 0.2
    )::numeric, 1) as overall_quality_score,

    -- Critical Tie-Outs Pass Count
    (
        CASE WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 1 ELSE 0 END +
        CASE WHEN ABS(COALESCE(mst.total_payment_due, 0) - COALESCE(cf.debt_service_payment, 0)) <= 10 THEN 1 ELSE 0 END +
        CASE WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 10 THEN 1 ELSE 0 END +
        CASE WHEN ABS((COALESCE(bs.total_assets, 0)) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) <= 1 THEN 1 ELSE 0 END +
        CASE WHEN ABS((COALESCE(cf.beginning_cash, 0) + COALESCE(cf.net_change_in_cash, 0)) - COALESCE(cf.ending_cash, 0)) <= 1 THEN 1 ELSE 0 END
    ) as critical_tieouts_passed,

    -- Audit Opinion
    CASE
        WHEN (
            CASE WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 1 ELSE 0 END +
            CASE WHEN ABS(COALESCE(mst.total_payment_due, 0) - COALESCE(cf.debt_service_payment, 0)) <= 10 THEN 1 ELSE 0 END +
            CASE WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 10 THEN 1 ELSE 0 END +
            CASE WHEN ABS((COALESCE(bs.total_assets, 0)) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) <= 1 THEN 1 ELSE 0 END +
            CASE WHEN ABS((COALESCE(cf.beginning_cash, 0) + COALESCE(cf.net_change_in_cash, 0)) - COALESCE(cf.ending_cash, 0)) <= 1 THEN 1 ELSE 0 END
        ) = 5 THEN 'CLEAN'
        WHEN (
            CASE WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 1 ELSE 0 END +
            CASE WHEN ABS(COALESCE(mst.total_payment_due, 0) - COALESCE(cf.debt_service_payment, 0)) <= 10 THEN 1 ELSE 0 END +
            CASE WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 10 THEN 1 ELSE 0 END +
            CASE WHEN ABS((COALESCE(bs.total_assets, 0)) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) <= 1 THEN 1 ELSE 0 END +
            CASE WHEN ABS((COALESCE(cf.beginning_cash, 0) + COALESCE(cf.net_change_in_cash, 0)) - COALESCE(cf.ending_cash, 0)) <= 1 THEN 1 ELSE 0 END
        ) >= 3 THEN 'QUALIFIED'
        ELSE 'ADVERSE'
    END as audit_opinion

FROM properties p
JOIN financial_periods fp ON fp.property_id = p.id
LEFT JOIN balance_sheet_summary bs ON bs.property_id = p.id AND bs.period_id = fp.id
LEFT JOIN income_statement_summary ist ON ist.property_id = p.id AND ist.period_id = fp.id
LEFT JOIN cash_flow_summary cf ON cf.property_id = p.id AND cf.period_id = fp.id
LEFT JOIN rent_roll_data rr ON rr.property_id = p.id AND rr.period_id = fp.id
LEFT JOIN mortgage_statement_data mst ON mst.property_id = p.id AND mst.period_id = fp.id;

CREATE UNIQUE INDEX idx_frm_property_period
    ON forensic_reconciliation_master(property_id, period_id);

CREATE INDEX idx_frm_period
    ON forensic_reconciliation_master(period_year, period_month);

CREATE INDEX idx_frm_audit_opinion
    ON forensic_reconciliation_master(audit_opinion);

CREATE INDEX idx_frm_dscr
    ON forensic_reconciliation_master(dscr_status);
