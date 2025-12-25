-- Fine-Tuned Master Forensic Reconciliation View
-- Integrates Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage
-- Based on actual data patterns from October 2023 ESP001

-- Drop existing view
DROP MATERIALIZED VIEW IF EXISTS forensic_reconciliation_master CASCADE;

-- ============================================================================
-- Master Reconciliation View
-- ============================================================================
-- Performs all 12 critical tie-outs using actual account codes

CREATE MATERIALIZED VIEW forensic_reconciliation_master AS
SELECT
    -- Property & Period Info
    p.id as property_id,
    p.property_code,
    p.property_name,
    fp.id as period_id,
    fp.period_year,
    fp.period_month,
    (fp.period_year || '-' || LPAD(fp.period_month::text, 2, '0')) as period_label,

    -- ========================================================================
    -- BALANCE SHEET DATA
    -- ========================================================================
    bs.total_assets,
    bs.total_current_assets,
    bs.cash,
    bs.total_liabilities,
    bs.total_current_liabilities,
    bs.long_term_debt as bs_long_term_debt,
    bs.total_equity,
    bs.retained_earnings,
    bs.tenant_deposits as bs_tenant_deposits,
    bs.escrow_accounts as bs_escrow_accounts,
    bs.avg_extraction_confidence as bs_confidence,
    bs.line_item_count as bs_line_count,

    -- Balance Sheet Equation Check
    (bs.total_assets - bs.total_liabilities - bs.total_equity) as balance_check_variance,

    -- ========================================================================
    -- INCOME STATEMENT DATA
    -- ========================================================================
    ist.total_income as is_total_income,
    ist.rental_income as is_rental_income,
    ist.other_income as is_other_income,
    ist.total_operating_expenses as is_operating_expenses,
    ist.noi as is_noi,
    ist.interest_expense as is_interest_expense,
    ist.depreciation_expense as is_depreciation,
    ist.net_income as is_net_income,
    ist.avg_extraction_confidence as is_confidence,
    ist.line_item_count as is_line_count,

    -- ========================================================================
    -- CASH FLOW DATA
    -- ========================================================================
    cf.beginning_cash as cf_beginning_cash,
    cf.operating_cash_flow as cf_operating,
    cf.investing_cash_flow as cf_investing,
    cf.financing_cash_flow as cf_financing,
    cf.debt_service_payment as cf_debt_service,
    cf.net_change_in_cash as cf_net_change,
    cf.ending_cash as cf_ending_cash,
    cf.avg_extraction_confidence as cf_confidence,
    cf.line_item_count as cf_line_count,

    -- ========================================================================
    -- RENT ROLL DATA (Aggregated from line items)
    -- ========================================================================
    rr_agg.total_units as rr_total_units,
    rr_agg.occupied_units as rr_occupied_units,
    (rr_agg.total_units - rr_agg.occupied_units) as rr_vacant_units,
    rr_agg.occupancy_rate as rr_occupancy_rate,
    rr_agg.total_monthly_rent as rr_monthly_rent,
    rr_agg.rr_annual_rent as rr_annual_rent,
    rr_agg.total_square_footage as rr_square_footage,
    rr_agg.rr_confidence,

    -- ========================================================================
    -- MORTGAGE STATEMENT DATA
    -- ========================================================================
    mst.loan_number as mst_loan_number,
    mst.principal_balance as mst_principal_balance,
    mst.interest_rate as mst_interest_rate,
    mst.total_payment_due as mst_monthly_payment,
    mst.principal_due as mst_principal_due,
    mst.interest_due as mst_interest_due,
    mst.tax_escrow_due as mst_tax_escrow,
    mst.insurance_escrow_due as mst_insurance_escrow,
    (mst.total_payment_due * 12) as mst_annual_debt_service,
    mst.ytd_interest_paid as mst_ytd_interest,
    mst.extraction_confidence as mst_confidence,

    -- ========================================================================
    -- TIE-OUT #1: Mortgage Principal = Balance Sheet Long-Term Debt
    -- ========================================================================
    -- CRITICAL: Validates mortgage balance matches BS liability
    ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) as tieout_1_variance,
    CASE
        WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 'PASS'
        WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 1000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_1_status,

    -- ========================================================================
    -- TIE-OUT #2: Annual Rent Roll = Income Statement Rental Income
    -- ========================================================================
    -- CRITICAL: Validates rent roll matches rental revenue
    -- Convert monthly IS rental income to annual
    ABS(COALESCE(rr_agg.rr_annual_rent, 0) - (COALESCE(ist.rental_income, 0) * 12)) as tieout_2_variance,
    CASE
        WHEN ABS(COALESCE(rr_agg.rr_annual_rent, 0) - (COALESCE(ist.rental_income, 0) * 12)) <= 1000 THEN 'PASS'
        WHEN ABS(COALESCE(rr_agg.rr_annual_rent, 0) - (COALESCE(ist.rental_income, 0) * 12)) <= 5000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_2_status,

    -- ========================================================================
    -- TIE-OUT #3: Monthly Mortgage Interest = IS Interest Expense
    -- ========================================================================
    -- CRITICAL: Validates mortgage interest matches IS expense
    ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) as tieout_3_variance,
    CASE
        WHEN ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) <= 100 THEN 'PASS'
        WHEN ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) <= 1000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_3_status,

    -- ========================================================================
    -- TIE-OUT #4: Cash Flow Ending Cash = Balance Sheet Cash
    -- ========================================================================
    -- CRITICAL: Validates CF ending cash matches BS cash
    ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) as tieout_4_variance,
    CASE
        WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 100 THEN 'PASS'
        WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 1000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_4_status,

    -- ========================================================================
    -- TIE-OUT #5: IS Net Income = BS Retained Earnings Movement
    -- ========================================================================
    -- CRITICAL: Validates net income flows to equity
    ABS(COALESCE(ist.net_income, 0) - COALESCE(bs.retained_earnings, 0)) as tieout_5_variance,
    CASE
        WHEN ABS(COALESCE(ist.net_income, 0) - COALESCE(bs.retained_earnings, 0)) <= 1000 THEN 'PASS'
        WHEN ABS(COALESCE(ist.net_income, 0) - COALESCE(bs.retained_earnings, 0)) <= 5000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_5_status,

    -- ========================================================================
    -- TIE-OUT #6: Mortgage Escrow (Tax) = BS Escrow
    -- ========================================================================
    -- WARNING: Tax escrow on mortgage matches BS escrow account
    ABS(COALESCE(mst.tax_escrow_due, 0) - COALESCE(bs.escrow_accounts, 0)) as tieout_6_variance,
    CASE
        WHEN ABS(COALESCE(mst.tax_escrow_due, 0) - COALESCE(bs.escrow_accounts, 0)) <= 500 THEN 'PASS'
        WHEN ABS(COALESCE(mst.tax_escrow_due, 0) - COALESCE(bs.escrow_accounts, 0)) <= 2000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_6_status,

    -- ========================================================================
    -- TIE-OUT #7: CF Debt Service = Mortgage Monthly Payment
    -- ========================================================================
    -- WARNING: Cash flow debt payment matches mortgage payment
    ABS(COALESCE(cf.debt_service_payment, 0) - COALESCE(mst.total_payment_due, 0)) as tieout_7_variance,
    CASE
        WHEN ABS(COALESCE(cf.debt_service_payment, 0) - COALESCE(mst.total_payment_due, 0)) <= 500 THEN 'PASS'
        WHEN ABS(COALESCE(cf.debt_service_payment, 0) - COALESCE(mst.total_payment_due, 0)) <= 2000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_7_status,

    -- ========================================================================
    -- TIE-OUT #8: CF Operating = IS NOI (after adjustments)
    -- ========================================================================
    -- INFO: Operating cash flow approximates NOI
    ABS(COALESCE(cf.operating, 0) - COALESCE(ist.noi, 0)) as tieout_8_variance,
    CASE
        WHEN ABS(COALESCE(cf.operating, 0) - COALESCE(ist.noi, 0)) <= 5000 THEN 'PASS'
        WHEN ABS(COALESCE(cf.operating, 0) - COALESCE(ist.noi, 0)) <= 20000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_8_status,

    -- ========================================================================
    -- TIE-OUT #9: Total Income - Operating Expenses = NOI
    -- ========================================================================
    -- INFO: Mathematical check of NOI calculation
    ABS((COALESCE(ist.total_income, 0) - COALESCE(ist.total_operating_expenses, 0)) - COALESCE(ist.noi, 0)) as tieout_9_variance,
    CASE
        WHEN ABS((COALESCE(ist.total_income, 0) - COALESCE(ist.total_operating_expenses, 0)) - COALESCE(ist.noi, 0)) <= 100 THEN 'PASS'
        WHEN ABS((COALESCE(ist.total_income, 0) - COALESCE(ist.total_operating_expenses, 0)) - COALESCE(ist.noi, 0)) <= 1000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_9_status,

    -- ========================================================================
    -- TIE-OUT #10: BS Assets = Liabilities + Equity
    -- ========================================================================
    -- INFO: Balance Sheet equation must balance
    ABS(COALESCE(bs.total_assets, 0) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) as tieout_10_variance,
    CASE
        WHEN ABS(COALESCE(bs.total_assets, 0) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) <= 100 THEN 'PASS'
        WHEN ABS(COALESCE(bs.total_assets, 0) - (COALESCE(bs.total_liabilities, 0) + COALESCE(bs.total_equity, 0))) <= 1000 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_10_status,

    -- ========================================================================
    -- TIE-OUT #11: Occupancy Rate >= 85%
    -- ========================================================================
    -- INFO: Business metric - healthy occupancy
    (100 - COALESCE(rr_agg.occupancy_rate, 0)) as tieout_11_variance,
    CASE
        WHEN COALESCE(rr_agg.occupancy_rate, 0) >= 85 THEN 'PASS'
        WHEN COALESCE(rr_agg.occupancy_rate, 0) >= 75 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_11_status,

    -- ========================================================================
    -- TIE-OUT #12: DSCR >= 1.25x
    -- ========================================================================
    -- INFO: Debt service coverage ratio (loan covenant)
    -- DSCR = NOI / Annual Debt Service
    CASE
        WHEN COALESCE(mst.total_payment_due, 0) * 12 > 0
        THEN COALESCE(ist.noi, 0) / (COALESCE(mst.total_payment_due, 0) * 12)
        ELSE NULL
    END as dscr,
    CASE
        WHEN (COALESCE(ist.noi, 0) / NULLIF(COALESCE(mst.total_payment_due, 0) * 12, 0)) >= 1.25 THEN 'PASS'
        WHEN (COALESCE(ist.noi, 0) / NULLIF(COALESCE(mst.total_payment_due, 0) * 12, 0)) >= 1.10 THEN 'WARNING'
        ELSE 'FAIL'
    END as tieout_12_status,

    -- ========================================================================
    -- SUMMARY METRICS
    -- ========================================================================
    -- Count how many critical tie-outs passed
    (CASE WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 1 ELSE 0 END +
     CASE WHEN ABS(COALESCE(rr_agg.rr_annual_rent, 0) - (COALESCE(ist.rental_income, 0) * 12)) <= 1000 THEN 1 ELSE 0 END +
     CASE WHEN ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) <= 100 THEN 1 ELSE 0 END +
     CASE WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 100 THEN 1 ELSE 0 END +
     CASE WHEN ABS(COALESCE(ist.net_income, 0) - COALESCE(bs.retained_earnings, 0)) <= 1000 THEN 1 ELSE 0 END
    ) as critical_tieouts_passed,

    -- Overall quality score (average of all extraction confidences)
    ROUND(
        (COALESCE(bs.avg_extraction_confidence, 0) +
         COALESCE(ist.avg_extraction_confidence, 0) +
         COALESCE(cf.avg_extraction_confidence, 0) +
         COALESCE(rr_agg.rr_confidence, 0) +
         COALESCE(mst.extraction_confidence, 0)) / 5.0,
        2
    ) as overall_quality_score,

    -- Document completeness
    (CASE WHEN bs.line_item_count > 0 THEN 1 ELSE 0 END +
     CASE WHEN ist.line_item_count > 0 THEN 1 ELSE 0 END +
     CASE WHEN cf.line_item_count > 0 THEN 1 ELSE 0 END +
     CASE WHEN rr_agg.total_units > 0 THEN 1 ELSE 0 END +
     CASE WHEN mst.loan_number IS NOT NULL THEN 1 ELSE 0 END
    ) as documents_present,

    -- Audit opinion
    CASE
        WHEN (CASE WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(rr_agg.rr_annual_rent, 0) - (COALESCE(ist.rental_income, 0) * 12)) <= 1000 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) <= 100 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 100 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(ist.net_income, 0) - COALESCE(bs.retained_earnings, 0)) <= 1000 THEN 1 ELSE 0 END
             ) = 5 THEN 'CLEAN'
        WHEN (CASE WHEN ABS(COALESCE(mst.principal_balance, 0) - COALESCE(bs.long_term_debt, 0)) <= 100 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(rr_agg.rr_annual_rent, 0) - (COALESCE(ist.rental_income, 0) * 12)) <= 1000 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(mst.interest_due, 0) - COALESCE(ist.interest_expense, 0)) <= 100 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(cf.ending_cash, 0) - COALESCE(bs.cash, 0)) <= 100 THEN 1 ELSE 0 END +
              CASE WHEN ABS(COALESCE(ist.net_income, 0) - COALESCE(bs.retained_earnings, 0)) <= 1000 THEN 1 ELSE 0 END
             ) >= 3 THEN 'QUALIFIED'
        ELSE 'ADVERSE'
    END as audit_opinion,

    -- Timestamps
    GREATEST(bs.last_updated, ist.last_updated, cf.last_updated) as last_data_update,
    NOW() as view_created_at

FROM properties p
CROSS JOIN financial_periods fp
LEFT JOIN balance_sheet_summary bs ON bs.property_id = p.id AND bs.period_id = fp.id
LEFT JOIN income_statement_summary ist ON ist.property_id = p.id AND ist.period_id = fp.id
LEFT JOIN cash_flow_summary cf ON cf.property_id = p.id AND cf.period_id = fp.id

-- Rent Roll Aggregation (tenant-by-tenant to summary)
LEFT JOIN (
    SELECT
        property_id,
        period_id,
        COUNT(DISTINCT unit_number) as total_units,
        COUNT(DISTINCT CASE
            WHEN tenant_name IS NOT NULL AND tenant_name != '' AND tenant_name NOT ILIKE '%vacant%'
            THEN unit_number
        END) as occupied_units,
        SUM(monthly_rent) as total_monthly_rent,
        SUM(monthly_rent) * 12 as rr_annual_rent,
        SUM(unit_area_sqft) as total_square_footage,
        ROUND(
            (COUNT(DISTINCT CASE WHEN tenant_name IS NOT NULL AND tenant_name != '' AND tenant_name NOT ILIKE '%vacant%'
                   THEN unit_number END)::numeric /
             NULLIF(COUNT(DISTINCT unit_number), 0) * 100)::numeric,
            2
        ) as occupancy_rate,
        AVG(extraction_confidence) as rr_confidence
    FROM rent_roll_data
    GROUP BY property_id, period_id
) rr_agg ON rr_agg.property_id = p.id AND rr_agg.period_id = fp.id

-- Mortgage Statement (one row per property-period)
LEFT JOIN mortgage_statement_data mst ON mst.property_id = p.id AND mst.period_id = fp.id

-- Only include periods where we have at least one document
WHERE bs.line_item_count > 0
   OR ist.line_item_count > 0
   OR cf.line_item_count > 0
   OR rr_agg.total_units > 0
   OR mst.loan_number IS NOT NULL;

-- Create indexes for performance
CREATE UNIQUE INDEX idx_forensic_master_property_period
    ON forensic_reconciliation_master(property_id, period_id);

CREATE INDEX idx_forensic_master_period
    ON forensic_reconciliation_master(period_year, period_month);

CREATE INDEX idx_forensic_master_audit_opinion
    ON forensic_reconciliation_master(audit_opinion);

CREATE INDEX idx_forensic_master_critical_tieouts
    ON forensic_reconciliation_master(critical_tieouts_passed);
