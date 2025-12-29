-- ============================================================================
-- FORENSIC AUDIT FRAMEWORK - FRAUD DETECTION & ANALYSIS
-- ============================================================================
-- These rules implement Big 4 forensic audit methodology
-- Priority: LOW - Advanced fraud detection and risk analysis
-- ============================================================================

-- Create forensic_audit_rules table if not exists
CREATE TABLE IF NOT EXISTS forensic_audit_rules (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(20) UNIQUE NOT NULL,
    rule_name VARCHAR(200) NOT NULL,
    description TEXT,
    audit_phase VARCHAR(50) NOT NULL,
    test_type VARCHAR(50) NOT NULL,
    statistical_method VARCHAR(100),
    threshold_value DECIMAL(15,4),
    severity VARCHAR(20) DEFAULT 'medium',
    auto_execute BOOLEAN DEFAULT false,
    requires_specialist BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- PHASE 1: DOCUMENT COMPLETENESS & QUALITY (Rules A-1.1 through A-1.3)
-- ============================================================================

INSERT INTO forensic_audit_rules (rule_code, rule_name, description, audit_phase, test_type, threshold_value, severity, auto_execute, is_active)
VALUES
('A-1.1', 'Document Completeness Matrix',
 'Ensure all required documents present for each property and period',
 'completeness', 'inventory_check', 95.0, 'critical', true, true),

('A-1.2', 'Period Consistency Check',
 'Verify all documents cover the same periods with no gaps or overlaps',
 'completeness', 'date_validation', 100.0, 'critical', true, true),

('A-1.3', 'Version Control Verification',
 'Ensure final audited versions with proper approval trail',
 'completeness', 'version_check', 100.0, 'critical', false, true);

-- ============================================================================
-- PHASE 2: MATHEMATICAL INTEGRITY (Rules A-2.1 through A-2.6)
-- ============================================================================

INSERT INTO forensic_audit_rules (rule_code, rule_name, description, audit_phase, test_type, threshold_value, severity, auto_execute, is_active)
VALUES
('A-2.1', 'Balance Sheet Equation Test',
 'Assets = Liabilities + Equity (absolute precision required)',
 'integrity', 'equation_test', 0.00, 'critical', true, true),

('A-2.2', 'Income Statement Equation Test',
 'Net Income = Total Income - Total Expenses (absolute precision)',
 'integrity', 'equation_test', 0.00, 'critical', true, true),

('A-2.3', 'Cash Flow Equation Test',
 'Cash Flow = Net Income + Total Adjustments',
 'integrity', 'equation_test', 0.00, 'critical', true, true),

('A-2.4', 'Cash Flow to Balance Sheet Test',
 'Cash Flow = Ending Cash - Beginning Cash',
 'integrity', 'equation_test', 0.00, 'critical', true, true),

('A-2.5', 'Rent Roll Calculation Test',
 'Annual Rent = Monthly Rent × 12',
 'integrity', 'calculation_test', 1.00, 'error', true, true),

('A-2.6', 'Mortgage Statement Calculation Test',
 'Total Payment = Principal + Interest + Escrows',
 'integrity', 'calculation_test', 1.00, 'error', true, true);

-- ============================================================================
-- PHASE 3: CROSS-DOCUMENT RECONCILIATION (Already implemented as reconciliation_rules)
-- ============================================================================

-- These are already in reconciliation_rules table
-- A-3.1 through A-3.8 covered by existing reconciliation rules

-- ============================================================================
-- PHASE 4: FRAUD DETECTION (Rules A-6.1 through A-6.8)
-- ============================================================================

INSERT INTO forensic_audit_rules (rule_code, rule_name, description, audit_phase, test_type, statistical_method, threshold_value, severity, auto_execute, requires_specialist, is_active)
VALUES
('A-6.1', 'Benfords Law Analysis',
 'Statistical analysis of first digit distribution to detect manipulation',
 'fraud_detection', 'statistical_test', 'chi_square_benford', 0.05, 'critical', true, true, true),

('A-6.2', 'Round Number Analysis',
 'Detect excessive round numbers suggesting fabrication',
 'fraud_detection', 'pattern_analysis', 'round_number_frequency', 10.0, 'warning', true, false, true),

('A-6.3', 'Duplicate Payment Detection',
 'Identify same amounts paid multiple times',
 'fraud_detection', 'duplicate_analysis', 'exact_match', 2.0, 'warning', true, false, true),

('A-6.4', 'Variance Analysis - Period over Period',
 'Flag unusual variances >25% without explanation',
 'fraud_detection', 'variance_analysis', 'percentage_change', 25.0, 'warning', true, false, true),

('A-6.5', 'Related Party Transaction Analysis',
 'Identify and test related party transactions',
 'fraud_detection', 'relationship_analysis', 'address_phone_match', NULL, 'critical', false, true, true),

('A-6.6', 'Sequential Gap Analysis',
 'Detect missing invoice/check numbers',
 'fraud_detection', 'sequence_analysis', 'gap_detection', NULL, 'warning', true, false, true),

('A-6.7', 'Journal Entry Testing',
 'Flag manual entries with high fraud risk characteristics',
 'fraud_detection', 'pattern_analysis', 'manual_entry_flags', NULL, 'critical', false, true, true),

('A-6.8', 'Cash Ratio Analysis',
 'Cash generation alignment with profitability',
 'fraud_detection', 'ratio_analysis', 'cash_conversion', 0.5, 'warning', true, false, true);

-- ============================================================================
-- PHASE 5: A/R & COLLECTIONS ANALYSIS (Rules A-5.1 through A-5.3)
-- ============================================================================

INSERT INTO forensic_audit_rules (rule_code, rule_name, description, audit_phase, test_type, statistical_method, threshold_value, severity, auto_execute, is_active)
VALUES
('A-5.1', 'A/R Aging Analysis',
 'Days Sales Outstanding and aging bucket analysis',
 'collections', 'aging_analysis', 'dso_calculation', 60.0, 'critical', true, true),

('A-5.2', 'Cash Collections Verification',
 'Reconcile CF A/R adjustments to BS A/R changes',
 'collections', 'reconciliation', 'variance_analysis', 10.0, 'warning', true, true),

('A-5.3', 'Revenue Quality Score',
 'Composite score (0-100) for revenue quality',
 'collections', 'scoring_model', 'weighted_average', 70.0, 'warning', true, true);

-- ============================================================================
-- PHASE 6: DEBT SERVICE & LIQUIDITY (Rules A-7.1 through A-7.5)
-- ============================================================================

INSERT INTO forensic_audit_rules (rule_code, rule_name, description, audit_phase, test_type, statistical_method, threshold_value, severity, auto_execute, is_active)
VALUES
('A-7.1', 'DSCR Calculation & Covenant Test',
 'Debt Service Coverage Ratio ≥ 1.25 (typical covenant)',
 'liquidity', 'ratio_calculation', 'noi_debt_service', 1.25, 'critical', true, true),

('A-7.2', 'LTV Ratio Calculation',
 'Loan-to-Value Ratio ≤ 75% (typical covenant)',
 'liquidity', 'ratio_calculation', 'loan_value', 75.0, 'critical', true, true),

('A-7.3', 'Interest Coverage Ratio',
 'ICR = NOI / Interest Expense ≥ 3.0 (strong)',
 'liquidity', 'ratio_calculation', 'noi_interest', 3.0, 'warning', true, true),

('A-7.4', 'Liquidity Ratios',
 'Current Ratio and Quick Ratio assessment',
 'liquidity', 'ratio_calculation', 'current_quick', 1.0, 'critical', true, true),

('A-7.5', 'Cash Burn Rate Analysis',
 'Runway in months if operations deteriorate',
 'liquidity', 'projection', 'cash_runway', 6.0, 'critical', true, true);

-- ============================================================================
-- PHASE 7: PERFORMANCE METRICS (Rules A-8.1 through A-8.4)
-- ============================================================================

INSERT INTO forensic_audit_rules (rule_code, rule_name, description, audit_phase, test_type, statistical_method, threshold_value, severity, auto_execute, is_active)
VALUES
('A-8.1', 'Same-Store Sales Growth',
 'Year-over-year revenue growth for properties held >12 months',
 'performance', 'growth_analysis', 'yoy_comparison', 0.0, 'info', true, true),

('A-8.2', 'NOI Margin Analysis',
 'NOI Margin = NOI / Total Revenue (target 55-70% for retail NNN)',
 'performance', 'margin_analysis', 'noi_revenue', 55.0, 'warning', true, true),

('A-8.3', 'Operating Expense Ratio',
 'OpEx Ratio = OpEx / Revenue (target 30-40% for NNN)',
 'performance', 'efficiency_ratio', 'opex_revenue', 40.0, 'warning', true, true),

('A-8.4', 'CapEx as % of Revenue',
 'Capital Expenditure / Revenue (healthy 5-10%)',
 'performance', 'capex_analysis', 'capex_revenue', 10.0, 'info', true, true);

-- ============================================================================
-- PHASE 8: TENANT & LEASE ANALYSIS (Rules A-4.1 through A-4.7)
-- ============================================================================

INSERT INTO forensic_audit_rules (rule_code, rule_name, description, audit_phase, test_type, statistical_method, threshold_value, severity, auto_execute, is_active)
VALUES
('A-4.1', 'Monthly Rent to IS Base Rentals',
 'Rent Roll monthly rent reconciles to Income Statement (±5%)',
 'revenue_verification', 'reconciliation', 'variance_analysis', 5.0, 'warning', true, true),

('A-4.2', 'Rent Roll Trend Analysis',
 'Month-to-month changes documented and logical',
 'revenue_verification', 'trend_analysis', 'change_tracking', NULL, 'warning', true, true),

('A-4.3', 'Occupancy Rate Verification',
 'Occupancy = (Occupied SF / Total SF) × 100',
 'revenue_verification', 'calculation_test', 'occupancy_calc', 0.01, 'error', true, true),

('A-4.4', 'Tenant Concentration Risk',
 'Flag tenants >20% of rent (high risk), >50% top 3 (moderate)',
 'risk_management', 'concentration_analysis', 'percentage_calculation', 20.0, 'warning', true, true),

('A-4.5', 'Lease Expiration Analysis',
 'Flag >25% of rent expiring in 12 months (high risk)',
 'risk_management', 'expiration_analysis', 'rollover_calculation', 25.0, 'critical', true, true),

('A-4.6', 'Rent Per Square Foot Analysis',
 'Identify >20% deviation from market rates',
 'revenue_verification', 'market_comparison', 'variance_analysis', 20.0, 'warning', true, true),

('A-4.7', 'Vacant Space Analysis',
 'Track vacancy trends and lost revenue potential',
 'revenue_verification', 'vacancy_tracking', 'revenue_loss_calc', NULL, 'info', true, true);

-- ============================================================================
-- MATERIALITY THRESHOLDS (Rule A-10)
-- ============================================================================

CREATE TABLE IF NOT EXISTS materiality_thresholds (
    id SERIAL PRIMARY KEY,
    property_id INTEGER,
    threshold_type VARCHAR(50) NOT NULL,
    calculation_basis VARCHAR(100) NOT NULL,
    percentage DECIMAL(5,2),
    fixed_amount DECIMAL(15,2),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO materiality_thresholds (threshold_type, calculation_basis, percentage, description, is_active)
VALUES
('overall_materiality', 'total_assets', 0.50, '0.5% of Total Assets', true),
('overall_materiality', 'total_revenue', 1.50, '1.5% of Total Revenue', true),
('overall_materiality', 'net_income', 5.00, '5% of Net Income', true),
('line_item_materiality', 'overall_materiality', 10.00, '10% of overall materiality for significant accounts', true),
('trivial_threshold', 'overall_materiality', 5.00, '5% of overall materiality (clearly trivial)', true),
('fraud_threshold', NULL, NULL, 'ANY irregularity suggesting fraud', true);

-- ============================================================================
-- Summary Queries
-- ============================================================================

SELECT
    audit_phase,
    COUNT(*) as rules_count,
    SUM(CASE WHEN auto_execute = true THEN 1 ELSE 0 END) as auto_executable,
    SUM(CASE WHEN requires_specialist = true THEN 1 ELSE 0 END) as requires_specialist
FROM forensic_audit_rules
WHERE is_active = true
GROUP BY audit_phase
ORDER BY audit_phase;

SELECT 'Forensic Audit Rules Deployed' as status, COUNT(*) as total_rules
FROM forensic_audit_rules
WHERE is_active = true;
