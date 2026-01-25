-- REIMS2 Financial Database Views
-- These views provide convenient access to commonly queried data

-- =============================================================================
-- 1. Property Financial Summary View
-- =============================================================================
-- Consolidated view of all financial metrics for each property/period
CREATE OR REPLACE VIEW v_property_financial_summary AS
SELECT
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    p.property_type,
    p.city,
    p.state,
    fp.period_year,
    fp.period_month,
    fp.period_start_date,
    fp.period_end_date,
    -- Balance Sheet
    fm.total_assets,
    fm.total_liabilities,
    fm.total_equity,
    fm.current_ratio,
    fm.debt_to_equity_ratio,
    -- Income Statement
    fm.total_revenue,
    fm.total_expenses,
    fm.net_operating_income,
    fm.net_income,
    fm.operating_margin,
    fm.profit_margin,
    -- Cash Flow
    fm.operating_cash_flow,
    fm.investing_cash_flow,
    fm.financing_cash_flow,
    fm.net_cash_flow,
    fm.ending_cash_balance,
    -- Rent Roll
    fm.total_units,
    fm.occupied_units,
    fm.vacant_units,
    fm.occupancy_rate,
    fm.total_annual_rent,
    fm.avg_rent_per_sqft,
    -- Performance
    fm.noi_per_sqft,
    fm.revenue_per_sqft,
    fm.expense_ratio,
    -- Metadata
    fm.calculated_at
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
LEFT JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE p.status = 'active'
ORDER BY p.property_code, fp.period_year DESC, fp.period_month DESC;


-- =============================================================================
-- 2. Monthly Comparison View
-- =============================================================================
-- Month-over-month comparison for income statement
CREATE OR REPLACE VIEW v_monthly_comparison AS
SELECT
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    isd.account_code,
    isd.account_name,
    fp.period_year,
    fp.period_month,
    isd.period_amount AS current_month,
    LAG(isd.period_amount) OVER (
        PARTITION BY isd.property_id, isd.account_code 
        ORDER BY fp.period_year, fp.period_month
    ) AS previous_month,
    isd.period_amount - LAG(isd.period_amount) OVER (
        PARTITION BY isd.property_id, isd.account_code 
        ORDER BY fp.period_year, fp.period_month
    ) AS month_variance,
    ROUND(
        ((isd.period_amount - LAG(isd.period_amount) OVER (
            PARTITION BY isd.property_id, isd.account_code 
            ORDER BY fp.period_year, fp.period_month
        )) / NULLIF(LAG(isd.period_amount) OVER (
            PARTITION BY isd.property_id, isd.account_code 
            ORDER BY fp.period_year, fp.period_month
        ), 0) * 100), 2
    ) AS variance_percentage,
    isd.ytd_amount,
    isd.is_income
FROM income_statement_data isd
JOIN financial_periods fp ON isd.period_id = fp.id
JOIN properties p ON isd.property_id = p.id
WHERE p.status = 'active'
ORDER BY p.property_code, fp.period_year DESC, fp.period_month DESC, isd.account_code;


-- =============================================================================
-- 3. Year-to-Date Rollup View
-- =============================================================================
-- YTD aggregated financials for current fiscal year
CREATE OR REPLACE VIEW v_ytd_rollup AS
SELECT
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    fp.fiscal_year,
    SUM(fm.total_revenue) AS ytd_revenue,
    SUM(fm.total_expenses) AS ytd_expenses,
    SUM(fm.net_operating_income) AS ytd_noi,
    SUM(fm.net_income) AS ytd_net_income,
    AVG(fm.occupancy_rate) AS avg_occupancy_rate,
    MAX(fm.ending_cash_balance) AS latest_cash_balance,
    COUNT(DISTINCT fp.id) AS periods_reported
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
LEFT JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE p.status = 'active'
GROUP BY p.id, p.organization_id, p.property_code, p.property_name, fp.fiscal_year
ORDER BY p.property_code, fp.fiscal_year DESC;


-- =============================================================================
-- 4. Multi-Property Comparison View
-- =============================================================================
-- Compare key metrics across all properties for same period
CREATE OR REPLACE VIEW v_multi_property_comparison AS
SELECT
    fp.period_year,
    fp.period_month,
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    p.property_type,
    p.total_area_sqft,
    fm.total_revenue,
    fm.net_operating_income,
    fm.net_income,
    fm.occupancy_rate,
    fm.noi_per_sqft,
    fm.revenue_per_sqft,
    fm.expense_ratio,
    fm.operating_margin,
    RANK() OVER (
        PARTITION BY fp.period_year, fp.period_month 
        ORDER BY fm.net_operating_income DESC
    ) AS noi_rank,
    RANK() OVER (
        PARTITION BY fp.period_year, fp.period_month 
        ORDER BY fm.occupancy_rate DESC
    ) AS occupancy_rank
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
LEFT JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE p.status = 'active'
ORDER BY fp.period_year DESC, fp.period_month DESC, fm.net_operating_income DESC;


-- =============================================================================
-- 5. Extraction Quality Dashboard View
-- =============================================================================
-- Monitor extraction quality across all uploads
CREATE OR REPLACE VIEW v_extraction_quality_dashboard AS
SELECT
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,
    du.document_type,
    du.file_name,
    du.extraction_status,
    el.confidence_score,
    el.quality_level,
    el.passed_checks,
    el.total_checks,
    el.needs_review,
    du.upload_date,
    du.extraction_completed_at,
    EXTRACT(EPOCH FROM (du.extraction_completed_at - du.extraction_started_at)) AS processing_seconds
FROM document_uploads du
JOIN properties p ON du.property_id = p.id
JOIN financial_periods fp ON du.period_id = fp.id
LEFT JOIN extraction_logs el ON du.extraction_id = el.id
WHERE du.is_active = TRUE
ORDER BY du.upload_date DESC;


-- =============================================================================
-- 6. Validation Issues View
-- =============================================================================
-- All validation failures that need attention
CREATE OR REPLACE VIEW v_validation_issues AS
SELECT
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,
    du.document_type,
    vr.rule_name,
    vr.rule_description,
    vres.passed,
    vres.expected_value,
    vres.actual_value,
    vres.difference,
    vres.difference_percentage,
    vres.error_message,
    vres.severity,
    vres.created_at
FROM validation_results vres
JOIN validation_rules vr ON vres.rule_id = vr.id
JOIN document_uploads du ON vres.upload_id = du.id
JOIN properties p ON du.property_id = p.id
JOIN financial_periods fp ON du.period_id = fp.id
WHERE vres.passed = FALSE
  AND vr.is_active = TRUE
ORDER BY vres.severity DESC, vres.created_at DESC;


-- =============================================================================
-- 7. Lease Expiration Pipeline View
-- =============================================================================
-- Upcoming lease expirations for proactive management
CREATE OR REPLACE VIEW v_lease_expiration_pipeline AS
SELECT
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    rr.unit_number,
    rr.tenant_name,
    rr.lease_end_date,
    rr.remaining_lease_years,
    rr.annual_rent,
    rr.unit_area_sqft,
    rr.lease_status,
    rr.occupancy_status,
    fp.period_year,
    fp.period_month,
    EXTRACT(DAY FROM (rr.lease_end_date - CURRENT_DATE)) AS days_until_expiration,
    CASE
        WHEN rr.lease_end_date < CURRENT_DATE THEN 'EXPIRED'
        WHEN rr.lease_end_date < CURRENT_DATE + INTERVAL '90 days' THEN 'EXPIRING_SOON'
        WHEN rr.lease_end_date < CURRENT_DATE + INTERVAL '180 days' THEN 'EXPIRING_6MO'
        ELSE 'ACTIVE'
    END AS expiration_status
FROM rent_roll_data rr
JOIN properties p ON rr.property_id = p.id
JOIN financial_periods fp ON rr.period_id = fp.id
WHERE rr.occupancy_status = 'occupied'
  AND p.status = 'active'
  -- Get latest period only
  AND (fp.period_year, fp.period_month) = (
      SELECT period_year, period_month
      FROM financial_periods
      WHERE property_id = p.id
      ORDER BY period_year DESC, period_month DESC
      LIMIT 1
  )
ORDER BY rr.lease_end_date ASC;


-- =============================================================================
-- 8. Annual Trends View
-- =============================================================================
-- 12-month trend analysis for specific accounts
CREATE OR REPLACE VIEW v_annual_trends AS
SELECT
    p.id AS property_id,
    p.organization_id,
    p.property_code,
    p.property_name,
    isd.account_code,
    isd.account_name,
    fp.period_year AS year,
    ARRAY_AGG(isd.period_amount ORDER BY fp.period_month) AS monthly_amounts,
    ARRAY_AGG(isd.ytd_amount ORDER BY fp.period_month) AS monthly_ytd,
    ARRAY_AGG(fp.period_month ORDER BY fp.period_month) AS months,
    SUM(isd.period_amount) AS annual_total,
    AVG(isd.period_amount) AS monthly_average,
    MIN(isd.period_amount) AS min_month,
    MAX(isd.period_amount) AS max_month,
    STDDEV(isd.period_amount) AS std_deviation
FROM income_statement_data isd
JOIN financial_periods fp ON isd.period_id = fp.id
JOIN properties p ON isd.property_id = p.id
WHERE p.status = 'active'
  AND isd.is_calculated = FALSE  -- Only actual accounts, not calculated totals
GROUP BY p.id, p.organization_id, p.property_code, p.property_name, isd.account_code, isd.account_name, fp.period_year
ORDER BY p.property_code, fp.period_year DESC, isd.account_code;


-- =============================================================================
-- 9. Portfolio Summary View
-- =============================================================================
-- High-level portfolio metrics
CREATE OR REPLACE VIEW v_portfolio_summary AS
SELECT
    p.organization_id,
    fp.period_year,
    fp.period_month,
    COUNT(DISTINCT p.id) AS total_properties,
    SUM(p.total_area_sqft) AS total_sqft,
    SUM(fm.total_assets) AS portfolio_total_assets,
    SUM(fm.total_liabilities) AS portfolio_total_liabilities,
    SUM(fm.total_equity) AS portfolio_total_equity,
    SUM(fm.total_revenue) AS portfolio_total_revenue,
    SUM(fm.net_operating_income) AS portfolio_noi,
    SUM(fm.net_income) AS portfolio_net_income,
    AVG(fm.occupancy_rate) AS avg_occupancy_rate,
    AVG(fm.operating_margin) AS avg_operating_margin,
    AVG(fm.current_ratio) AS avg_current_ratio,
    SUM(fm.total_annual_rent) AS portfolio_annual_rent
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
LEFT JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE p.status = 'active'
GROUP BY p.organization_id, fp.period_year, fp.period_month
ORDER BY fp.period_year DESC, fp.period_month DESC;
