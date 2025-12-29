-- ============================================================================
-- Auto-Resolution Rules Implementation - CORRECTED for JSONB Schema
-- ============================================================================
-- This script creates auto-resolution rules for automatic fixes
-- Uses proper JSONB structure for condition_json and suggested_mapping
-- ============================================================================

BEGIN;

-- Auto-Resolution Rules with Proper JSONB Structure
-- These rules automatically fix common, predictable issues

INSERT INTO auto_resolution_rules (
    rule_name,
    pattern_type,
    condition_json,
    action_type,
    suggested_mapping,
    confidence_threshold,
    property_id,
    statement_type,
    description,
    priority,
    is_active
) VALUES

-- 1. Rounding Difference Auto-Fix (< $1)
('auto_fix_rounding_difference',
 'rounding_error',
 jsonb_build_object(
     'check_type', 'variance',
     'fields', jsonb_build_array('calculated_total', 'stated_total'),
     'max_difference', 1.00,
     'operator', 'absolute_difference'
 ),
 'adjust_value',
 jsonb_build_object(
     'target_field', 'stated_total',
     'adjustment_method', 'round_to_calculated',
     'log_adjustment', true
 ),
 0.99,
 NULL,
 NULL,
 'Automatically fix rounding differences less than $1',
 10,
 true),

-- 2. Auto-Populate Missing Calculations
('auto_calculate_missing_ytd',
 'missing_calculation',
 jsonb_build_object(
     'check_type', 'null_or_empty',
     'field', 'ytd_amount',
     'required_fields', jsonb_build_array('current_month', 'previous_ytd')
 ),
 'calculate_value',
 jsonb_build_object(
     'target_field', 'ytd_amount',
     'formula', 'current_month + previous_ytd',
     'validation_required', false
 ),
 1.00,
 NULL,
 NULL,
 'Auto-populate missing YTD calculations',
 9,
 true),

-- 3. Standardize Date Formats
('auto_standardize_date_format',
 'format_error',
 jsonb_build_object(
     'check_type', 'date_format',
     'field_type', 'date',
     'expected_format', 'YYYY-MM-DD',
     'common_formats', jsonb_build_array('MM/DD/YYYY', 'DD-MM-YYYY', 'YYYY/MM/DD')
 ),
 'reformat_value',
 jsonb_build_object(
     'conversion', 'parse_and_standardize',
     'target_format', 'YYYY-MM-DD',
     'handle_ambiguous', 'flag_for_review'
 ),
 0.95,
 NULL,
 NULL,
 'Standardize date formats to YYYY-MM-DD',
 8,
 true),

-- 4. Trim Whitespace and Standardize Case
('auto_clean_text_fields',
 'format_error',
 jsonb_build_object(
     'check_type', 'text_format',
     'issues', jsonb_build_array('leading_space', 'trailing_space', 'multiple_spaces', 'inconsistent_case'),
     'field_types', jsonb_build_array('text', 'varchar')
 ),
 'clean_text',
 jsonb_build_object(
     'trim', true,
     'collapse_spaces', true,
     'case_handling', 'title_case_names',
     'preserve_codes', true
 ),
 1.00,
 NULL,
 NULL,
 'Clean text fields: trim whitespace, standardize spacing',
 7,
 true),

-- 5. Auto-Map Common Account Code Variants
('auto_map_account_codes',
 'mapping_error',
 jsonb_build_object(
     'check_type', 'account_code_variant',
     'known_variants', jsonb_build_object(
         '4010-0000', '40000',
         '5010-0000', '50000',
         '6010-0000', '60000'
     )
 ),
 'map_value',
 jsonb_build_object(
     'mapping_type', 'account_code_rollup',
     'use_parent_code', true,
     'log_mapping', true
 ),
 0.98,
 NULL,
 'balance_sheet',
 'Auto-map detailed account codes to parent codes',
 9,
 true),

-- 6. Fix Small Reconciliation Differences (< $10)
('auto_reconcile_small_variance',
 'reconciliation_error',
 jsonb_build_object(
     'check_type', 'variance',
     'max_difference', 10.00,
     'comparison_type', 'cross_document',
     'documents', jsonb_build_array('income_statement', 'balance_sheet')
 ),
 'adjust_value',
 jsonb_build_object(
     'adjustment_target', 'determine_from_confidence',
     'create_adjustment_entry', true,
     'require_approval', false
 ),
 0.90,
 NULL,
 NULL,
 'Auto-reconcile small variances < $10 between documents',
 6,
 true),

-- 7. Auto-Calculate Monthly from Annual
('auto_calculate_monthly_from_annual',
 'missing_calculation',
 jsonb_build_object(
     'check_type', 'null_or_empty',
     'target_field', 'monthly_amount',
     'source_field', 'annual_amount',
     'verify_reverse', true
 ),
 'calculate_value',
 jsonb_build_object(
     'formula', 'annual_amount / 12',
     'round_to', 2,
     'validation', 'verify_annual_equals_monthly_times_12'
 ),
 1.00,
 NULL,
 'rent_roll',
 'Auto-calculate monthly rent from annual rent (÷ 12)',
 9,
 true),

-- 8. Auto-Fix Percentage Formatting
('auto_fix_percentage_format',
 'format_error',
 jsonb_build_object(
     'check_type', 'percentage_format',
     'field_type', 'percentage',
     'issues', jsonb_build_array('expressed_as_whole_number', 'missing_decimal')
 ),
 'reformat_value',
 jsonb_build_object(
     'conversion', 'detect_and_normalize',
     'range_check', jsonb_build_object('min', 0, 'max', 100),
     'output_format', 'decimal'
 ),
 0.95,
 NULL,
 NULL,
 'Auto-detect and fix percentage formatting (e.g., 95 vs 0.95)',
 8,
 true),

-- 9. Auto-Populate Default Values
('auto_populate_default_values',
 'missing_data',
 jsonb_build_object(
     'check_type', 'null_or_empty',
     'fields_with_defaults', jsonb_build_object(
         'payment_method', 'ACH',
         'currency', 'USD',
         'status', 'active'
     )
 ),
 'set_default',
 jsonb_build_object(
     'apply_defaults', true,
     'only_if_null', true,
     'log_defaults_applied', true
 ),
 0.99,
 NULL,
 NULL,
 'Auto-populate standard default values for empty fields',
 5,
 true),

-- 10. Auto-Fix Sign Errors (Obvious Cases)
('auto_fix_sign_errors',
 'data_error',
 jsonb_build_object(
     'check_type', 'sign_error',
     'fields', jsonb_build_object(
         'expenses', 'should_be_positive',
         'income', 'should_be_positive',
         'depreciation', 'should_be_positive'
     ),
     'confidence_indicators', jsonb_build_array('contradicts_label', 'breaks_calculation')
 ),
 'flip_sign',
 jsonb_build_object(
     'apply_absolute_value', true,
     'verify_calculations_after', true,
     'flag_if_uncertain', true
 ),
 0.85,
 NULL,
 'income_statement',
 'Auto-fix obvious sign errors (e.g., negative income)',
 7,
 true),

-- 11. Auto-Match Similar Descriptions
('auto_match_similar_descriptions',
 'mapping_error',
 jsonb_build_object(
     'check_type', 'fuzzy_match',
     'field', 'description',
     'similarity_threshold', 0.90,
     'known_mappings_table', 'common_descriptions'
 ),
 'standardize_value',
 jsonb_build_object(
     'use_most_common_variant', true,
     'create_mapping_rule', true,
     'require_approval_threshold', 0.85
 ),
 0.90,
 NULL,
 NULL,
 'Auto-match and standardize similar transaction descriptions',
 6,
 true),

-- 12. Auto-Fix Unit Number Formatting
('auto_fix_unit_number_format',
 'format_error',
 jsonb_build_object(
     'check_type', 'unit_number_format',
     'issues', jsonb_build_array('leading_zeros', 'mixed_case', 'special_chars'),
     'expected_pattern', '^[A-Z0-9-]+$'
 ),
 'reformat_value',
 jsonb_build_object(
     'uppercase', true,
     'remove_special_chars', jsonb_build_array(' ', '.', ','),
     'preserve_hyphens', true,
     'pad_numbers', false
 ),
 0.98,
 NULL,
 'rent_roll',
 'Standardize unit number formatting (uppercase, no special chars)',
 7,
 true),

-- 13. Auto-Calculate Square Footage Metrics
('auto_calculate_sf_metrics',
 'missing_calculation',
 jsonb_build_object(
     'check_type', 'null_or_empty',
     'target_field', 'rent_per_sf',
     'required_fields', jsonb_build_array('monthly_rent', 'square_footage'),
     'preconditions', jsonb_build_object('square_footage', jsonb_build_object('operator', '>', 'value', 0))
 ),
 'calculate_value',
 jsonb_build_object(
     'formula', 'monthly_rent / square_footage',
     'round_to', 2,
     'validation', 'reasonable_range_check'
 ),
 1.00,
 NULL,
 'rent_roll',
 'Auto-calculate rent per square foot from monthly rent and SF',
 8,
 true),

-- 14. Auto-Reconcile Principal Reduction
('auto_reconcile_principal_reduction',
 'calculation_error',
 jsonb_build_object(
     'check_type', 'calculation_mismatch',
     'formula', 'beginning_balance - principal_paid = ending_balance',
     'tolerance', 1.00,
     'fields', jsonb_build_array('beginning_balance', 'principal_paid', 'ending_balance')
 ),
 'adjust_value',
 jsonb_build_object(
     'recalculate', 'ending_balance',
     'formula', 'beginning_balance - principal_paid',
     'verify_with_lender_statement', false
 ),
 0.95,
 NULL,
 'mortgage_statement',
 'Auto-reconcile principal reduction calculation',
 8,
 true),

-- 15. Auto-Fix Decimal Placement Errors
('auto_fix_decimal_errors',
 'data_error',
 jsonb_build_object(
     'check_type', 'decimal_placement',
     'detection', jsonb_build_object(
         'method', 'compare_to_similar_fields',
         'magnitude_check', 'differs_by_power_of_10'
     ),
     'fields', jsonb_build_array('amounts', 'balances', 'rates')
 ),
 'adjust_value',
 jsonb_build_object(
     'correction_method', 'detect_power_of_10_error',
     'common_errors', jsonb_build_array('missing_decimal', 'extra_zeros'),
     'require_approval', true
 ),
 0.80,
 NULL,
 NULL,
 'Detect and fix decimal placement errors (e.g., 123456 vs 1234.56)',
 9,
 true);

-- Verify Auto-Resolution Rules
SELECT
    id,
    rule_name,
    pattern_type,
    action_type,
    confidence_threshold,
    priority,
    is_active
FROM auto_resolution_rules
ORDER BY priority DESC, id;

-- Summary
SELECT
    'Auto-Resolution Rules Deployed' as status,
    COUNT(*) as total_rules,
    COUNT(*) FILTER (WHERE confidence_threshold >= 0.95) as high_confidence,
    COUNT(*) FILTER (WHERE confidence_threshold >= 0.85 AND confidence_threshold < 0.95) as medium_confidence,
    COUNT(*) FILTER (WHERE priority >= 8) as high_priority
FROM auto_resolution_rules
WHERE is_active = true;

COMMIT;

-- ============================================================================
-- Expected Output:
-- - 15 auto_resolution_rules created with proper JSONB structure
-- - Rules cover: rounding, calculations, formatting, mapping, reconciliation
-- - All rules have confidence thresholds and priorities
-- - Ready for automatic application based on confidence levels
-- ============================================================================
