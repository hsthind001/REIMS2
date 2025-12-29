-- ============================================================================
-- Prevention Rules Implementation - CORRECTED for JSONB Schema
-- ============================================================================
-- This script creates prevention rules that stop bad data at entry
-- Uses proper JSONB structure for rule_condition and rule_action
-- Requires issue_knowledge_base entries as foreign keys
-- ============================================================================

BEGIN;

-- Step 1: Create Issue Knowledge Base Entries for Prevention Rules
-- These entries document the types of issues being prevented

INSERT INTO issue_knowledge_base (
    issue_type,
    issue_category,
    error_pattern,
    prevention_strategy,
    status,
    confidence_score
) VALUES
-- 1. Negative Payment Prevention
('negative_payment_amount', 'data_validation',
 'Payment amount is negative',
 '{"validation_type": "range_check", "field": "payment_amount", "min": 0}'::jsonb,
 'active', 1.0),

-- 2. Escrow Overdraft Prevention
('escrow_balance_negative', 'data_validation',
 'Escrow balance would become negative',
 '{"validation_type": "balance_check", "fields": ["tax_escrow", "insurance_escrow", "reserve_escrow"]}'::jsonb,
 'active', 1.0),

-- 3. Duplicate Entry Prevention
('duplicate_transaction', 'data_integrity',
 'Transaction with same details already exists',
 '{"validation_type": "uniqueness_check", "fields": ["date", "amount", "description"]}'::jsonb,
 'active', 0.95),

-- 4. Future Date Prevention
('future_dated_transaction', 'data_validation',
 'Transaction date is in the future',
 '{"validation_type": "date_check", "field": "transaction_date", "max": "today"}'::jsonb,
 'active', 1.0),

-- 5. Overlapping Lease Prevention
('overlapping_lease_dates', 'business_rule',
 'Lease periods overlap for same unit',
 '{"validation_type": "overlap_check", "entity": "lease", "fields": ["unit_id", "start_date", "end_date"]}'::jsonb,
 'active', 1.0),

-- 6. Invalid Account Code Prevention
('invalid_account_code', 'data_validation',
 'Account code not in chart of accounts',
 '{"validation_type": "reference_check", "field": "account_code", "reference_table": "chart_of_accounts"}'::jsonb,
 'active', 1.0),

-- 7. Negative Balance Sheet Values
('negative_asset_value', 'data_validation',
 'Asset values cannot be negative',
 '{"validation_type": "range_check", "fields": ["total_assets", "current_assets", "property_equipment"], "min": 0}'::jsonb,
 'active', 1.0),

-- 8. Missing Required Fields
('missing_required_field', 'data_validation',
 'Required field is empty or null',
 '{"validation_type": "completeness_check", "required_fields": ["property_id", "statement_date", "document_type"]}'::jsonb,
 'active', 1.0),

-- 9. Unrealistic Rent Amount
('unrealistic_rent_amount', 'business_rule',
 'Rent amount outside reasonable range',
 '{"validation_type": "range_check", "field": "monthly_rent", "min": 100, "max": 50000}'::jsonb,
 'active', 0.90),

-- 10. Invalid Occupancy Rate
('invalid_occupancy_rate', 'data_validation',
 'Occupancy rate outside 0-100% range',
 '{"validation_type": "range_check", "field": "occupancy_rate", "min": 0, "max": 100}'::jsonb,
 'active', 1.0),

-- 11. Negative Interest Rate
('negative_interest_rate', 'data_validation',
 'Interest rate is negative',
 '{"validation_type": "range_check", "field": "interest_rate", "min": 0, "max": 20}'::jsonb,
 'active', 1.0),

-- 12. Principal Greater Than Loan Amount
('principal_exceeds_loan', 'business_rule',
 'Principal balance exceeds original loan amount',
 '{"validation_type": "comparison_check", "field1": "principal_balance", "field2": "original_loan_amount", "operator": "<="}'::jsonb,
 'active', 1.0),

-- 13. Invalid DSCR Calculation
('invalid_dscr_components', 'calculation',
 'DSCR components are invalid or missing',
 '{"validation_type": "calculation_check", "formula": "dscr = noi / debt_service", "required_fields": ["noi", "debt_service"]}'::jsonb,
 'active', 1.0),

-- 14. Duplicate Unit Number
('duplicate_unit_number', 'data_integrity',
 'Unit number already exists for this property',
 '{"validation_type": "uniqueness_check", "entity": "unit", "fields": ["property_id", "unit_number"]}'::jsonb,
 'active', 1.0),

-- 15. Invalid Statement Period
('invalid_statement_period', 'data_validation',
 'Statement period spans more than 12 months',
 '{"validation_type": "date_range_check", "start_field": "period_start", "end_field": "period_end", "max_months": 12}'::jsonb,
 'active', 1.0);

-- Step 2: Create Prevention Rules with JSONB Structure
-- Links to issue_knowledge_base and uses JSONB for conditions/actions

INSERT INTO prevention_rules (
    issue_kb_id,
    rule_type,
    rule_condition,
    rule_action,
    description,
    priority,
    is_active
)
SELECT
    ikb.id,
    CASE ikb.issue_category
        WHEN 'data_validation' THEN 'field_validation'
        WHEN 'business_rule' THEN 'business_logic'
        WHEN 'data_integrity' THEN 'integrity_check'
        WHEN 'calculation' THEN 'calculation_validation'
    END,
    -- Build rule_condition JSONB based on prevention_strategy
    jsonb_build_object(
        'validation_type', ikb.prevention_strategy->>'validation_type',
        'criteria', ikb.prevention_strategy,
        'error_pattern', ikb.error_pattern
    ),
    -- Build rule_action JSONB
    jsonb_build_object(
        'action', 'block',
        'message', ikb.error_pattern,
        'severity', 'error',
        'suggest_fix', true
    ),
    'Prevent: ' || ikb.issue_type,
    CASE ikb.confidence_score
        WHEN 1.0 THEN 10  -- Highest priority for certain validations
        WHEN 0.95 THEN 8
        ELSE 5
    END,
    true
FROM issue_knowledge_base ikb
WHERE ikb.status = 'active'
ORDER BY ikb.id;

-- Step 3: Verify Prevention Rules
SELECT
    pr.id,
    pr.rule_type,
    ikb.issue_type,
    pr.priority,
    pr.is_active
FROM prevention_rules pr
JOIN issue_knowledge_base ikb ON pr.issue_kb_id = ikb.id
ORDER BY pr.priority DESC, pr.id;

-- Summary
SELECT
    'Prevention Rules Deployed' as status,
    COUNT(*) as total_rules,
    COUNT(*) FILTER (WHERE priority >= 10) as critical_priority,
    COUNT(*) FILTER (WHERE priority >= 5 AND priority < 10) as high_priority
FROM prevention_rules
WHERE is_active = true;

COMMIT;

-- ============================================================================
-- Expected Output:
-- - 15 issue_knowledge_base entries created
-- - 15 prevention_rules created with proper JSONB structure
-- - All rules active and linked to knowledge base
-- ============================================================================
