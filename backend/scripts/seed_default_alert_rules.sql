-- Seed Default Alert Rules from Templates
-- Creates commonly used alert rules for risk management

-- DSCR Threshold Breach Rule
INSERT INTO alert_rules (
    rule_name, description, rule_type, field_name, condition, threshold_value, 
    severity, is_active, cooldown_period, property_specific, 
    severity_mapping, rule_expression, created_at
) VALUES (
    'DSCR Threshold Breach',
    'Alert when Debt Service Coverage Ratio falls below 1.25',
    'threshold',
    'dscr',
    'less_than',
    1.25,
    'critical',
    true,
    60,
    false,
    '{"critical_threshold": 0.2, "high_threshold": 0.1, "warning_threshold": 0.05}'::jsonb,
    '{"template_id": "dscr_threshold_breach", "alert_type": "DSCR_BREACH", "assigned_committee": "FINANCE_SUBCOMMITTEE"}'::jsonb,
    NOW()
) ON CONFLICT DO NOTHING;

-- Occupancy Rate Warning Rule
INSERT INTO alert_rules (
    rule_name, description, rule_type, field_name, condition, threshold_value, 
    severity, is_active, cooldown_period, property_specific,
    severity_mapping, rule_expression, created_at
) VALUES (
    'Occupancy Rate Warning',
    'Alert when occupancy rate drops below 85%',
    'threshold',
    'occupancy_rate',
    'less_than',
    85.0,
    'warning',
    true,
    60,
    false,
    '{"critical_threshold": 0.15, "high_threshold": 0.1, "warning_threshold": 0.05}'::jsonb,
    '{"template_id": "occupancy_rate_warning", "alert_type": "OCCUPANCY_WARNING", "assigned_committee": "OCCUPANCY_SUBCOMMITTEE"}'::jsonb,
    NOW()
) ON CONFLICT DO NOTHING;

-- LTV Breach Rule
INSERT INTO alert_rules (
    rule_name, description, rule_type, field_name, condition, threshold_value, 
    severity, is_active, cooldown_period, property_specific,
    severity_mapping, rule_expression, created_at
) VALUES (
    'LTV Ratio Breach',
    'Alert when Loan-to-Value ratio exceeds 75%',
    'threshold',
    'ltv',
    'greater_than',
    0.75,
    'high',
    true,
    60,
    false,
    '{"critical_threshold": 0.15, "high_threshold": 0.1, "warning_threshold": 0.05}'::jsonb,
    '{"template_id": "ltv_breach", "alert_type": "LTV_BREACH", "assigned_committee": "RISK_COMMITTEE"}'::jsonb,
    NOW()
) ON CONFLICT DO NOTHING;

-- Cash Flow Negative Rule
INSERT INTO alert_rules (
    rule_name, description, rule_type, field_name, condition, threshold_value, 
    severity, is_active, cooldown_period, property_specific,
    rule_expression, created_at
) VALUES (
    'Negative Cash Flow',
    'Alert when operating cash flow becomes negative',
    'threshold',
    'operating_cash_flow',
    'less_than',
    0.0,
    'critical',
    true,
    60,
    false,
    '{"template_id": "cash_flow_negative", "alert_type": "CASH_FLOW_NEGATIVE", "assigned_committee": "FINANCE_SUBCOMMITTEE"}'::jsonb,
    NOW()
) ON CONFLICT DO NOTHING;

-- Debt Yield Breach Rule
INSERT INTO alert_rules (
    rule_name, description, rule_type, field_name, condition, threshold_value, 
    severity, is_active, cooldown_period, property_specific,
    severity_mapping, rule_expression, created_at
) VALUES (
    'Debt Yield Breach',
    'Alert when debt yield falls below 8%',
    'threshold',
    'debt_yield',
    'less_than',
    0.08,
    'high',
    true,
    60,
    false,
    '{"critical_threshold": 0.25, "high_threshold": 0.15, "warning_threshold": 0.1}'::jsonb,
    '{"template_id": "debt_yield_breach", "alert_type": "DEBT_YIELD_BREACH", "assigned_committee": "FINANCE_SUBCOMMITTEE"}'::jsonb,
    NOW()
) ON CONFLICT DO NOTHING;

-- Interest Coverage Breach Rule
INSERT INTO alert_rules (
    rule_name, description, rule_type, field_name, condition, threshold_value, 
    severity, is_active, cooldown_period, property_specific,
    severity_mapping, rule_expression, created_at
) VALUES (
    'Interest Coverage Breach',
    'Alert when interest coverage ratio falls below 1.5',
    'threshold',
    'interest_coverage_ratio',
    'less_than',
    1.5,
    'critical',
    true,
    60,
    false,
    '{"critical_threshold": 0.3, "high_threshold": 0.2, "warning_threshold": 0.1}'::jsonb,
    '{"template_id": "interest_coverage_breach", "alert_type": "INTEREST_COVERAGE_BREACH", "assigned_committee": "FINANCE_SUBCOMMITTEE"}'::jsonb,
    NOW()
) ON CONFLICT DO NOTHING;

