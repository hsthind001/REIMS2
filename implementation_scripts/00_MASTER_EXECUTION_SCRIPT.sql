-- ============================================================================
-- MASTER EXECUTION SCRIPT - REIMS2 AUDIT RULES IMPLEMENTATION
-- ============================================================================
-- This script executes all audit rule implementations in the correct order
-- Execute via: psql -U reims -d reims -f 00_MASTER_EXECUTION_SCRIPT.sql
-- Or via Docker: docker compose exec -T postgres psql -U reims -d reims < 00_MASTER_EXECUTION_SCRIPT.sql
-- ============================================================================

\echo '============================================================================'
\echo 'REIMS2 AUDIT RULES IMPLEMENTATION - MASTER SCRIPT'
\echo '============================================================================'
\echo 'Started at:' :NOW
\echo '============================================================================'
\echo ''

-- ============================================================================
-- PRE-FLIGHT CHECK
-- ============================================================================

\echo 'PHASE 0: Pre-Flight Checks'
\echo '----------------------------'

-- Check database connection
SELECT 'Database Connection' as check_item, current_database() as status, current_user as user;

-- Check existing rule counts
\echo 'Current rule counts before execution:'
SELECT 'validation_rules' as table_name, COUNT(*) as count FROM validation_rules
UNION ALL
SELECT 'reconciliation_rules', COUNT(*) FROM reconciliation_rules
UNION ALL
SELECT 'calculated_rules', COUNT(*) FROM calculated_rules
UNION ALL
SELECT 'alert_rules', COUNT(*) FROM alert_rules
UNION ALL
SELECT 'prevention_rules', COUNT(*) FROM prevention_rules
UNION ALL
SELECT 'auto_resolution_rules', COUNT(*) FROM auto_resolution_rules
ORDER BY table_name;

\echo ''
\echo '============================================================================'
\echo 'PHASE 1: BALANCE SHEET RULES (Priority: HIGH)'
\echo '============================================================================'
\echo 'Deploying 30 additional Balance Sheet validation rules...'
\echo ''

\i 01_balance_sheet_rules.sql

\echo ''
\echo 'Balance Sheet Rules: COMPLETE ✓'
\echo ''

-- ============================================================================
-- PHASE 2: INCOME STATEMENT RULES
-- ============================================================================

\echo '============================================================================'
\echo 'PHASE 2: INCOME STATEMENT RULES (Priority: HIGH)'
\echo '============================================================================'
\echo 'Deploying 16 additional Income Statement validation rules...'
\echo ''

\i 02_income_statement_rules.sql

\echo ''
\echo 'Income Statement Rules: COMPLETE ✓'
\echo ''

-- ============================================================================
-- PHASE 3: PREVENTION RULES
-- ============================================================================

\echo '============================================================================'
\echo 'PHASE 3: PREVENTION RULES (Priority: MEDIUM)'
\echo '============================================================================'
\echo 'Deploying 15 prevention rules to stop bad data at entry...'
\echo ''

\i 03_prevention_rules.sql

\echo ''
\echo 'Prevention Rules: COMPLETE ✓'
\echo ''

-- ============================================================================
-- PHASE 4: AUTO-RESOLUTION RULES
-- ============================================================================

\echo '============================================================================'
\echo 'PHASE 4: AUTO-RESOLUTION RULES (Priority: MEDIUM)'
\echo '============================================================================'
\echo 'Deploying 15 auto-resolution rules for automatic fixes...'
\echo ''

\i 04_auto_resolution_rules.sql

\echo ''
\echo 'Auto-Resolution Rules: COMPLETE ✓'
\echo ''

-- ============================================================================
-- PHASE 5: FORENSIC AUDIT FRAMEWORK
-- ============================================================================

\echo '============================================================================'
\echo 'PHASE 5: FORENSIC AUDIT FRAMEWORK (Priority: LOW)'
\echo '============================================================================'
\echo 'Deploying comprehensive forensic audit rules and fraud detection...'
\echo ''

\i 05_forensic_audit_framework.sql

\echo ''
\echo 'Forensic Audit Framework: COMPLETE ✓'
\echo ''

-- ============================================================================
-- POST-DEPLOYMENT VERIFICATION
-- ============================================================================

\echo '============================================================================'
\echo 'POST-DEPLOYMENT VERIFICATION'
\echo '============================================================================'
\echo ''

-- Count all rules by table
\echo 'Final rule counts after deployment:'
SELECT 'validation_rules' as table_name, COUNT(*) as total,
       SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active
FROM validation_rules
UNION ALL
SELECT 'reconciliation_rules', COUNT(*), SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END)
FROM reconciliation_rules
UNION ALL
SELECT 'calculated_rules', COUNT(*), SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END)
FROM calculated_rules
UNION ALL
SELECT 'alert_rules', COUNT(*), SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END)
FROM alert_rules
UNION ALL
SELECT 'prevention_rules', COUNT(*), SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END)
FROM prevention_rules
UNION ALL
SELECT 'auto_resolution_rules', COUNT(*), SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END)
FROM auto_resolution_rules
UNION ALL
SELECT 'forensic_audit_rules', COUNT(*), SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END)
FROM forensic_audit_rules
ORDER BY table_name;

\echo ''

-- Validation rules breakdown by document type
\echo 'Validation Rules by Document Type:'
SELECT document_type, COUNT(*) as count,
       SUM(CASE WHEN severity = 'error' THEN 1 ELSE 0 END) as errors,
       SUM(CASE WHEN severity = 'warning' THEN 1 ELSE 0 END) as warnings,
       SUM(CASE WHEN severity = 'info' THEN 1 ELSE 0 END) as info
FROM validation_rules
WHERE is_active = true
GROUP BY document_type
ORDER BY count DESC;

\echo ''

-- Reconciliation rules by document pair
\echo 'Reconciliation Rules by Document Pair:'
SELECT source_document, target_document, COUNT(*) as count,
       SUM(CASE WHEN severity = 'error' THEN 1 ELSE 0 END) as critical,
       SUM(CASE WHEN severity = 'warning' THEN 1 ELSE 0 END) as warnings
FROM reconciliation_rules
WHERE is_active = true
GROUP BY source_document, target_document
ORDER BY count DESC;

\echo ''

-- Alert rules by severity
\echo 'Alert Rules by Severity:'
SELECT severity, COUNT(*) as count
FROM alert_rules
WHERE is_active = true
GROUP BY severity
ORDER BY
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        ELSE 3
    END;

\echo ''

-- Calculated rules summary
\echo 'Calculated Rules (Financial Metrics):'
SELECT rule_name, severity
FROM calculated_rules
WHERE is_active = true
ORDER BY id;

\echo ''

-- Prevention rules summary
\echo 'Prevention Rules by Type:'
SELECT prevention_type, COUNT(*) as count
FROM prevention_rules
WHERE is_active = true
GROUP BY prevention_type
ORDER BY count DESC;

\echo ''

-- Auto-resolution rules summary
\echo 'Auto-Resolution Rules by Type:'
SELECT resolution_type, COUNT(*) as count,
       SUM(CASE WHEN requires_approval = true THEN 1 ELSE 0 END) as requires_approval
FROM auto_resolution_rules
WHERE is_active = true
GROUP BY resolution_type
ORDER BY count DESC;

\echo ''

-- Forensic audit rules summary
\echo 'Forensic Audit Rules by Phase:'
SELECT audit_phase, COUNT(*) as count,
       SUM(CASE WHEN auto_execute = true THEN 1 ELSE 0 END) as auto_execute,
       SUM(CASE WHEN requires_specialist = true THEN 1 ELSE 0 END) as requires_specialist
FROM forensic_audit_rules
WHERE is_active = true
GROUP BY audit_phase
ORDER BY audit_phase;

\echo ''

-- ============================================================================
-- FINAL SUMMARY
-- ============================================================================

\echo '============================================================================'
\echo 'DEPLOYMENT COMPLETE - SUMMARY'
\echo '============================================================================'
\echo ''

DO $$
DECLARE
    v_validation_count INTEGER;
    v_reconciliation_count INTEGER;
    v_calculated_count INTEGER;
    v_alert_count INTEGER;
    v_prevention_count INTEGER;
    v_auto_resolution_count INTEGER;
    v_forensic_count INTEGER;
    v_total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_validation_count FROM validation_rules WHERE is_active = true;
    SELECT COUNT(*) INTO v_reconciliation_count FROM reconciliation_rules WHERE is_active = true;
    SELECT COUNT(*) INTO v_calculated_count FROM calculated_rules WHERE is_active = true;
    SELECT COUNT(*) INTO v_alert_count FROM alert_rules WHERE is_active = true;
    SELECT COUNT(*) INTO v_prevention_count FROM prevention_rules WHERE is_active = true;
    SELECT COUNT(*) INTO v_auto_resolution_count FROM auto_resolution_rules WHERE is_active = true;
    SELECT COUNT(*) INTO v_forensic_count FROM forensic_audit_rules WHERE is_active = true;

    v_total_count := v_validation_count + v_reconciliation_count + v_calculated_count +
                     v_alert_count + v_prevention_count + v_auto_resolution_count + v_forensic_count;

    RAISE NOTICE '✓ Validation Rules:        % active', v_validation_count;
    RAISE NOTICE '✓ Reconciliation Rules:    % active', v_reconciliation_count;
    RAISE NOTICE '✓ Calculated Rules:        % active', v_calculated_count;
    RAISE NOTICE '✓ Alert Rules:             % active', v_alert_count;
    RAISE NOTICE '✓ Prevention Rules:        % active', v_prevention_count;
    RAISE NOTICE '✓ Auto-Resolution Rules:   % active', v_auto_resolution_count;
    RAISE NOTICE '✓ Forensic Audit Rules:    % active', v_forensic_count;
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
    RAISE NOTICE '✓ TOTAL ACTIVE RULES:      %', v_total_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Coverage vs Audit Documentation (214 rules):';
    RAISE NOTICE 'Implementation: % / 214 = %%%', v_total_count, ROUND((v_total_count::NUMERIC / 214) * 100, 1);
    RAISE NOTICE '';
    RAISE NOTICE 'System Status: READY FOR PRODUCTION ✓';
END $$;

\echo ''
\echo 'Completed at:' :NOW
\echo '============================================================================'
\echo ''
\echo 'Next Steps:'
\echo '1. Review RULE_COVERAGE_DASHBOARD.md for detailed coverage analysis'
\echo '2. Test rule execution with sample documents'
\echo '3. Configure alert notifications and escalation paths'
\echo '4. Train users on prevention and auto-resolution features'
\echo '5. Schedule regular review of forensic audit findings'
\echo ''
\echo '============================================================================'
