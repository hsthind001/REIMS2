-- ============================================================================
-- AUTO-RESOLUTION RULES - AUTOMATIC FIXES FOR MINOR ISSUES
-- ============================================================================
-- These rules automatically fix common data quality issues
-- Priority: MEDIUM - Reduces manual intervention
-- ============================================================================

INSERT INTO auto_resolution_rules (rule_name, description, trigger_condition, resolution_action, resolution_type, requires_approval, is_active)
VALUES
-- AUTO-001: Auto-fix Rounding Differences
('auto_fix_rounding_diff',
 'Automatically fix rounding differences less than $1.00',
 'ABS(calculated_value - entered_value) < 1.00 AND ABS(calculated_value - entered_value) > 0',
 'UPDATE {table} SET {field} = {calculated_value} WHERE id = {record_id}',
 'calculation_correction',
 false,
 true),

-- AUTO-002: Auto-calculate Missing Annual Rent
('auto_calc_annual_rent',
 'Automatically calculate annual rent from monthly rent',
 'monthly_rent IS NOT NULL AND annual_rent IS NULL',
 'UPDATE rent_roll SET annual_rent = monthly_rent * 12 WHERE id = {record_id}',
 'field_calculation',
 false,
 true),

-- AUTO-003: Auto-calculate Missing Monthly Rent
('auto_calc_monthly_rent',
 'Automatically calculate monthly rent from annual rent',
 'annual_rent IS NOT NULL AND monthly_rent IS NULL',
 'UPDATE rent_roll SET monthly_rent = annual_rent / 12 WHERE id = {record_id}',
 'field_calculation',
 false,
 true),

-- AUTO-004: Auto-populate Default Escrow Amounts
('auto_populate_escrow_defaults',
 'Automatically populate escrow amounts from prior month if missing',
 'current_tax_escrow_due IS NULL AND prior_month_tax_escrow_due IS NOT NULL',
 'UPDATE mortgage_statement SET current_tax_escrow_due = {prior_month_value} WHERE id = {record_id}',
 'default_value',
 false,
 true),

-- AUTO-005: Auto-fix Trailing/Leading Spaces
('auto_trim_tenant_names',
 'Automatically remove trailing and leading spaces from tenant names',
 'tenant_name != TRIM(tenant_name)',
 'UPDATE rent_roll SET tenant_name = TRIM(tenant_name) WHERE id = {record_id}',
 'data_cleaning',
 false,
 true),

-- AUTO-006: Auto-standardize Date Formats
('auto_standardize_dates',
 'Automatically convert dates to standard format',
 'date_field ~ irregular_date_pattern',
 'UPDATE {table} SET {date_field} = TO_DATE({date_field}, {detected_format}) WHERE id = {record_id}',
 'format_standardization',
 false,
 true),

-- AUTO-007: Auto-fix Percentage Calculations
('auto_fix_percentage_calc',
 'Automatically recalculate percentages when numerator/denominator change',
 'numerator_changed OR denominator_changed',
 'UPDATE {table} SET percentage = (numerator / denominator) * 100 WHERE id = {record_id}',
 'calculation_correction',
 false,
 true),

-- AUTO-008: Auto-reconcile Small Escrow Timing Differences
('auto_reconcile_escrow_timing',
 'Automatically reconcile escrow timing differences < $10',
 'ABS(bs_escrow_balance - ms_escrow_balance) < 10.00 AND ABS(bs_escrow_balance - ms_escrow_balance) > 0',
 'UPDATE balance_sheet SET escrow_{type} = mortgage_statement.{type}_escrow WHERE property_id = {property_id} AND period = {period}',
 'reconciliation',
 false,
 true),

-- AUTO-009: Auto-populate YTD from PTD
('auto_calc_ytd_from_ptd',
 'Automatically calculate YTD from PTD + Prior YTD',
 'ytd IS NULL AND ptd IS NOT NULL AND prior_ytd IS NOT NULL',
 'UPDATE {table} SET ytd = ptd + prior_ytd WHERE id = {record_id}',
 'field_calculation',
 false,
 true),

-- AUTO-010: Auto-calculate Total Cash
('auto_calc_total_cash',
 'Automatically calculate total cash from cash account components',
 'total_cash != (cash_operating + cash_depository + cash_operating_iv)',
 'UPDATE balance_sheet SET total_cash = cash_operating + cash_depository + cash_operating_iv WHERE id = {record_id}',
 'calculation_correction',
 false,
 true),

-- AUTO-011: Auto-fix Case Inconsistencies
('auto_fix_case_tenant_names',
 'Automatically fix case inconsistencies in tenant names (Title Case)',
 'tenant_name ~ irregular_case_pattern',
 'UPDATE rent_roll SET tenant_name = INITCAP(tenant_name) WHERE id = {record_id}',
 'data_cleaning',
 false,
 true),

-- AUTO-012: Auto-populate Missing Unit Types
('auto_populate_unit_type',
 'Automatically populate missing unit type based on square footage',
 'unit_type IS NULL AND square_footage IS NOT NULL',
 'UPDATE rent_roll SET unit_type = CASE WHEN square_footage < 1000 THEN ''Small'' WHEN square_footage < 5000 THEN ''Medium'' ELSE ''Large'' END WHERE id = {record_id}',
 'default_value',
 true,  -- Requires approval
 true),

-- AUTO-013: Auto-fix Negative Sign Errors
('auto_fix_negative_signs',
 'Automatically fix incorrect negative signs on expense accounts',
 'account_type = ''expense'' AND amount < 0',
 'UPDATE journal_entry SET amount = ABS(amount) WHERE id = {record_id}',
 'sign_correction',
 true,  -- Requires approval
 true),

-- AUTO-014: Auto-reconcile Missing Period Depreciation
('auto_add_missing_depreciation',
 'Automatically add expected depreciation if missing for a period',
 'depreciation_expense = 0 AND prior_month_depreciation > 0 AND no_depreciation_flag = false',
 'INSERT INTO income_statement_adjustments (property_id, period, account, amount, reason) VALUES ({property_id}, {period}, ''Depreciation'', {expected_amount}, ''Auto-added missing depreciation'')',
 'missing_entry',
 true,  -- Requires approval
 true),

-- AUTO-015: Auto-apply Standard Lease Escalations
('auto_apply_lease_escalation',
 'Automatically apply standard lease escalations based on lease terms',
 'escalation_due_date = CURRENT_DATE AND escalation_applied = false',
 'UPDATE rent_roll SET monthly_rent = monthly_rent * (1 + escalation_rate) WHERE id = {record_id}',
 'business_rule',
 true,  -- Requires approval
 true);

-- ============================================================================
-- Summary Query
-- ============================================================================

SELECT 'Auto-Resolution Rules Deployed' as status, COUNT(*) as total_rules
FROM auto_resolution_rules
WHERE is_active = true;
