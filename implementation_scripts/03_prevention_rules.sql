-- ============================================================================
-- PREVENTION RULES - DATA QUALITY AT ENTRY POINT
-- ============================================================================
-- These rules prevent bad data from entering the system
-- Priority: MEDIUM - Stops problems before they start
-- ============================================================================

-- Create prevention_rules entries

INSERT INTO prevention_rules (rule_name, description, entity_type, field_name, prevention_type, condition_expression, suggested_action, is_active)
VALUES
-- PREV-001: Prevent Negative Property Tax Payment
('prevent_negative_tax_payment',
 'Prevent negative property tax payment amounts',
 'property_tax_payment',
 'payment_amount',
 'value_range',
 'payment_amount >= 0',
 'Payment amount must be positive. Please correct the entry.',
 true),

-- PREV-002: Prevent Insurance Escrow Overdraft
('prevent_insurance_escrow_overdraft',
 'Prevent insurance disbursements exceeding escrow balance',
 'insurance_disbursement',
 'disbursement_amount',
 'balance_check',
 'disbursement_amount <= insurance_escrow_balance',
 'Disbursement exceeds available escrow balance. Please verify amount.',
 true),

-- PREV-003: Prevent Duplicate Tenant Entries
('prevent_duplicate_tenant',
 'Prevent duplicate tenant entries in rent roll',
 'rent_roll',
 'tenant_name',
 'uniqueness',
 'NOT EXISTS (SELECT 1 FROM rent_roll WHERE tenant_name = NEW.tenant_name AND unit_number = NEW.unit_number AND period = NEW.period)',
 'Duplicate tenant entry detected. This tenant already exists for this unit and period.',
 true),

-- PREV-004: Prevent Overlapping Lease Dates
('prevent_overlapping_leases',
 'Prevent overlapping lease dates for same unit',
 'rent_roll',
 'lease_dates',
 'date_overlap',
 'NOT EXISTS (SELECT 1 FROM rent_roll WHERE unit_number = NEW.unit_number AND ((NEW.lease_start BETWEEN lease_start AND lease_end) OR (NEW.lease_end BETWEEN lease_start AND lease_end)))',
 'Lease dates overlap with existing lease for this unit. Please verify dates.',
 true),

-- PREV-005: Prevent Excessive Rent
('prevent_excessive_rent',
 'Prevent rent exceeding market rate by >50%',
 'rent_roll',
 'monthly_rent',
 'market_rate',
 'monthly_rent <= (market_rent_per_sf * unit_sf * 1.50)',
 'Rent exceeds market rate by more than 50%. Please verify amount.',
 true),

-- PREV-006: Prevent Negative Cash Balance
('prevent_negative_cash',
 'Prevent transactions that would create negative cash balance',
 'cash_transaction',
 'amount',
 'balance_check',
 'cash_balance_after_transaction >= 0',
 'This transaction would result in negative cash balance. Please verify funds availability.',
 true),

-- PREV-007: Prevent DSCR Covenant Violation
('prevent_dscr_violation',
 'Prevent actions that would cause DSCR to fall below covenant',
 'financial_transaction',
 'amount',
 'covenant_check',
 'projected_dscr >= covenant_dscr_minimum',
 'This action would violate DSCR covenant. Please review with CFO.',
 true),

-- PREV-008: Prevent Data Entry Outside Period
('prevent_outside_period_entry',
 'Prevent data entry for closed or future periods',
 'financial_data',
 'period_date',
 'period_check',
 'period_date >= current_open_period AND period_date <= next_allowed_period',
 'Cannot enter data for closed or future periods. Current open period: {period}',
 true),

-- PREV-009: Prevent Missing Required Fields
('prevent_missing_required_fields',
 'Prevent saving records with missing required fields',
 'all_entities',
 'required_fields',
 'completeness',
 'ALL required_fields IS NOT NULL',
 'Required fields are missing: {field_list}. Please complete all required fields.',
 true),

-- PREV-010: Prevent Invalid Account Codes
('prevent_invalid_account_codes',
 'Prevent use of invalid or inactive account codes',
 'journal_entry',
 'account_code',
 'reference_check',
 'account_code IN (SELECT account_code FROM chart_of_accounts WHERE is_active = true)',
 'Invalid account code. Please select from active chart of accounts.',
 true),

-- PREV-011: Prevent Future-Dated Transactions
('prevent_future_transactions',
 'Prevent transactions dated in the future',
 'all_transactions',
 'transaction_date',
 'date_check',
 'transaction_date <= CURRENT_DATE',
 'Transaction date cannot be in the future. Please verify date.',
 true),

-- PREV-012: Prevent Unbalanced Journal Entries
('prevent_unbalanced_journal',
 'Prevent journal entries where debits ≠ credits',
 'journal_entry',
 'debit_credit_total',
 'balance_check',
 'SUM(debits) = SUM(credits)',
 'Journal entry is not balanced. Debits must equal Credits. Difference: {difference}',
 true),

-- PREV-013: Prevent Duplicate Invoice Numbers
('prevent_duplicate_invoice',
 'Prevent duplicate invoice/check numbers',
 'invoice',
 'invoice_number',
 'uniqueness',
 'NOT EXISTS (SELECT 1 FROM invoices WHERE invoice_number = NEW.invoice_number AND vendor_id = NEW.vendor_id)',
 'Duplicate invoice number detected for this vendor.',
 true),

-- PREV-014: Prevent Percentage Rent Without Sales Clause
('prevent_percentage_rent_no_clause',
 'Prevent percentage rent entry for tenants without sales clause',
 'rent_roll',
 'percentage_rent',
 'business_logic',
 'IF percentage_rent > 0 THEN has_sales_clause = true',
 'Cannot enter percentage rent for tenant without sales-based lease clause.',
 true),

-- PREV-015: Prevent Lease Expiration Without Notice Period
('prevent_lease_expiry_no_notice',
 'Prevent lease renewal/termination within notice period without approval',
 'rent_roll',
 'lease_action',
 'date_check',
 '(lease_end_date - CURRENT_DATE) >= required_notice_days OR override_approval_id IS NOT NULL',
 'Lease action within notice period requires approval. Notice period: {days} days',
 true);

-- ============================================================================
-- Summary Query
-- ============================================================================

SELECT 'Prevention Rules Deployed' as status, COUNT(*) as total_rules
FROM prevention_rules
WHERE is_active = true;
