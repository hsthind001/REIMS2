-- Create Master Reconciliation View (CORRECTED for Rent Roll)
-- Drop if exists
DROP MATERIALIZED VIEW IF EXISTS forensic_reconciliation_master CASCADE;

-- Create with rent roll aggregation
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

    -- Rent Roll Aggregated Summary
    rr_agg.total_units,
    rr_agg.occupied_units,
    rr_agg.total_monthly_rent,
    rr_agg.rr_annual_rent,
    rr_agg.total_square_footage,
    rr_agg.occupancy_rate,
    rr_agg.rr_confidence,

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
    (COALESCE(mst.tax_escrow_balance, 0) + COALESCE(mst.insurance_escrow_balance, 0)) as mst_total_escrow,
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
    ABS(COALESCE(rr_agg.rr_annual_rent, 0) - COALESCE(ist.rental_income, 0)) as tieout_6_variance,
    CASE
        WHEN ABS(COALESCE(rr_agg.rr_annual_rent, 0) - COALESCE(ist.rental_income, 0)) <= 1000 THEN 'PASS'
        WHEN ABS(COALESCE(rr_agg.rr_annual_rent, 0) - COALESCE(ist.rental_income, 0)) <= 10000 THEN 'WARNING'
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
        WHEN COALESCE(rr_agg.occupancy_rate, 0) >= 80 THEN 'PASS'
        WHEN COALESCE(rr_agg.occupancy_rate, 0) >= 70 THEN 'WARNING'
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
        COALESCE(rr_agg.rr_confidence, 0) * 0.2 +
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
LEFT JOIN (
    -- Aggregate Rent Roll data
    SELECT
        property_id,
        period_id,
        COUNT(DISTINCT unit_number) as total_units,
        COUNT(DISTINCT CASE WHEN tenant_name IS NOT NULL AND tenant_name != '' THEN unit_number END) as occupied_units,
        SUM(monthly_rent) as total_monthly_rent,
        SUM(monthly_rent) * 12 as rr_annual_rent,
        SUM(unit_area_sqft) as total_square_footage,
        ROUND((COUNT(DISTINCT CASE WHEN tenant_name IS NOT NULL AND tenant_name != '' THEN unit_number END)::numeric /
               NULLIF(COUNT(DISTINCT unit_number), 0) * 100)::numeric, 2) as occupancy_rate,
        AVG(extraction_confidence) as rr_confidence
    FROM rent_roll_data
    GROUP BY property_id, period_id
) rr_agg ON rr_agg.property_id = p.id AND rr_agg.period_id = fp.id
LEFT JOIN mortgage_statement_data mst ON mst.property_id = p.id AND mst.period_id = fp.id;

-- Create indexes
CREATE UNIQUE INDEX idx_frm_property_period
    ON forensic_reconciliation_master(property_id, period_id);

CREATE INDEX idx_frm_period
    ON forensic_reconciliation_master(period_year, period_month);

CREATE INDEX idx_frm_audit_opinion
    ON forensic_reconciliation_master(audit_opinion);

CREATE INDEX idx_frm_dscr
    ON forensic_reconciliation_master(dscr_status);
