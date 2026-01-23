-- Seed file for verified reconciliation results (Property 11, Period 169)
-- Generated automatically for persistence

DELETE FROM cross_document_reconciliations WHERE property_id = 11 AND period_id = 169;

INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Accounting Equation', 'BS-1', 'PASS',
    'Balance Sheet', 'N/A', 23976748.54, 23976748.54,
    0.00, 0.00, FALSE, 'Total Assets must equal Total Liabilities & Capital', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Accumulated Depr Trend', 'BS-7', 'PASS',
    'Balance Sheet', 'N/A', 0.00, 0.00,
    0.00, 0.00, FALSE, 'Accum Depr changed by $0.00 (Prior: $0.00, Curr: $0.00)', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Annual vs Monthly Rent', 'RR-1', 'PASS',
    'Rent Roll', 'N/A', 2761921.20, 2761921.20,
    0.00, 0.00, FALSE, 'Annual $2,761,921 vs Monthly*12 $2,761,921', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Cash Balance Check', '3S-1', 'FAIL',
    'Three-Statement', 'N/A', 479864.30, 0.00,
    479864.30, 0.00, TRUE, 'BS Cash $479,864.30 vs CF Ending $0.00', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Cash Flow Recon (BS Delta)', '3S-8', 'FAIL',
    'Three-Statement', 'N/A', 0.00, 214254.33,
    -214254.33, 0.00, TRUE, 'CF Net Change $0.00 vs BS Cash Change $214,254.33', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Cash Operating Check', 'BS-2', 'PASS',
    'Balance Sheet', 'N/A', 3375.45, 3375.45,
    0.00, 0.00, FALSE, 'Cash Operating account verified against expected baseline', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Cash Reconciliation', 'CF-2', 'PASS',
    'Cash Flow', 'N/A', 0.00, 0.00,
    0.00, 0.00, FALSE, 'Beg(0) + Net(0) = End(0)', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'CF Category Sum', 'CF-1', 'FAIL',
    'Cash Flow', 'N/A', 2306143.46, 0.00,
    2306143.46, 0.00, TRUE, 'Op(1,959,730) + Inv(178,928) + Fin(167,486) = 2,306,143', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Current Assets Integrity', 'BS-3', 'PASS',
    'Balance Sheet', 'N/A', 628295.98, 628295.98,
    0.00, 0.00, FALSE, 'Total Current Assets: $628,295.98', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Current Ratio Liquidity', 'BS-4', 'FAIL',
    'Balance Sheet', 'N/A', 0.27, 1.00,
    -0.73, 0.00, TRUE, 'Current Ratio is 0.27 (Target >= 1.0)', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Debt to Assets Ratio', 'BS-9', 'FAIL',
    'Balance Sheet', 'N/A', 0.98, 0.85,
    0.13, 0.00, TRUE, 'Debt/Assets Ratio is 0.98 (Target <= 0.85)', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Depr (IS vs BS Delta)', '3S-5b', 'WARNING',
    'Three-Statement', 'N/A', 129625.24, 85.48,
    129539.76, 0.00, TRUE, 'IS $129,625 vs BS Delta $85', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Depr (IS vs CF)', '3S-5a', 'PASS',
    'Three-Statement', 'N/A', 129625.24, 129625.24,
    0.00, 0.00, FALSE, 'IS $129,625 vs CF $129,625', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Escrow Positive Balances', 'MST-4', 'PASS',
    'Mortgage', 'N/A', 21181117.40, 0.00,
    0.00, 0.00, FALSE, 'Tax Escrow: $21,181,117.40, Ins Escrow: $0.00', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Expense Ratio Check', 'IS-RATIO-1', 'PASS',
    'Income Statement', 'N/A', 0.40, 0.50,
    -0.10, 0.00, FALSE, 'Expense Ratio is 40.1%', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Land Asset Verification', 'BS-6', 'PASS',
    'Balance Sheet', 'N/A', 3100438.76, 0.00,
    0.00, 0.00, FALSE, 'Land value reported as $3,100,438.76', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Net Income Logic', '3S-3', 'FAIL',
    'Three-Statement', 'N/A', 32721.08, 717150.78,
    684429.70, 0.00, TRUE, 'IS Net Income $32,721.08 vs BS Earnings $717,150.78', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Net Income Verification', 'IS-1', 'PASS',
    'Income Statement', 'N/A', 32721.08, 32721.08,
    0.00, 0.00, FALSE, 'Net Income verified at $32,721.08', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'NOI Calculation', 'IS-NOI', 'PASS',
    'Income Statement', 'N/A', 338869.47, 0.00,
    0.00, 0.00, FALSE, 'NOI $338,869.47 (Implied OpEx: $226,780.01)', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Offsite Management Fee (4%)', 'IS-12', 'FAIL',
    'Income Statement', 'N/A', 5656.05, 22625.98,
    -16969.93, 0.00, TRUE, 'Mgmt Fee $5,656.05 vs Target $22,625.98 (4% of Revenue)', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Operating Margin', 'IS-MARGIN', 'PASS',
    'Income Statement', 'N/A', 0.60, 0.50,
    0.10, 0.00, FALSE, 'Operating Margin is 59.9%', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Payment Components', 'MST-1', 'FAIL',
    'Mortgage', 'N/A', 206734.24, 0.00,
    206734.24, 0.00, TRUE, 'Total $206,734.24 vs Sum $0.00', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Positive Ending Cash', 'CF-3', 'PASS',
    'Cash Flow', 'N/A', 0.00, 0.00,
    0.00, 0.00, FALSE, 'Ending Cash is $0.00', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Principal Rollforward', 'MST-2', 'PASS',
    'Mortgage', 'N/A', 0.00, 0.00,
    0.00, 0.00, FALSE, 'Principal Balance rolled correctly (Paid matching Due)', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Profit Margin Non-Negative', 'IS-PROFIT', 'PASS',
    'Income Statement', 'N/A', 0.06, 0.00,
    0.06, 0.00, FALSE, 'Profit Margin is 5.8%', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'Working Capital Positive', 'BS-5', 'FAIL',
    'Balance Sheet', 'N/A', -1741748.87, 0.00,
    -1741748.87, 0.00, TRUE, 'Working Capital is $-1,741,748.87', NULL,
    NOW(), NOW()
);
INSERT INTO cross_document_reconciliations (
    property_id, period_id, reconciliation_type, rule_code, status,
    source_document, target_document, source_value, target_value, 
    difference, materiality_threshold, is_material, explanation, recommendation, 
    created_at, updated_at
) VALUES (
    11, 169, 'YTD Interest Roll', 'MST-3', 'WARNING',
    'Mortgage', 'N/A', 38445.88, 41094.57,
    -2648.69, 0.00, TRUE, 'YTD Interest $38,445.88 vs Expected $41,094.57', NULL,
    NOW(), NOW()
);
