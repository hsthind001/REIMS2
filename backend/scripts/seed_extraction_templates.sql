-- Seed Extraction Templates for Financial Documents
-- Defines structure and keywords for PDF parsing

-- Clear existing templates (idempotent)
DELETE FROM extraction_templates WHERE template_name IN (
    'standard_balance_sheet',
    'standard_income_statement',
    'standard_cash_flow',
    'standard_rent_roll'
);

-- 1. BALANCE SHEET TEMPLATE
INSERT INTO extraction_templates (
    template_name,
    document_type,
    template_structure,
    keywords,
    extraction_rules,
    is_default
) VALUES (
    'standard_balance_sheet',
    'balance_sheet',
    '{
        "sections": [
            {"name": "ASSETS", "subsections": ["Current Assets", "Property & Equipment", "Other Assets"]},
            {"name": "LIABILITIES", "subsections": ["Current Liabilities", "Long Term Liabilities"]},
            {"name": "CAPITAL", "subsections": ["Partners Contribution", "Beginning Equity", "Distribution", "Current Period Earnings"]}
        ],
        "required_fields": ["total_assets", "total_liabilities", "total_capital"],
        "validation": "total_assets = total_liabilities + total_capital",
        "account_code_pattern": "####-####",
        "typical_accounts": {
            "assets": ["0122-0000", "0305-0000", "0510-0000", "0610-0000"],
            "liabilities": ["2110-0000", "2612-0000"],
            "equity": ["3050-0000", "3910-0000", "3995-0000"]
        }
    }'::jsonb,
    ARRAY[
        'balance sheet',
        'statement of financial position',
        'assets',
        'liabilities',
        'equity',
        'shareholders equity',
        'total assets',
        'total liabilities',
        'current assets',
        'property and equipment',
        'accumulated depreciation'
    ],
    '{
        "amount_patterns": ["\\$?[\\d,]+\\.\\d{2}", "\\([\\d,]+\\.\\d{2}\\)"],
        "date_patterns": ["as of [A-Za-z]+ \\d{1,2},? \\d{4}", "\\d{1,2}/\\d{1,2}/\\d{4}"],
        "section_detection": {
            "assets": ["ASSETS", "TOTAL ASSETS"],
            "liabilities": ["LIABILITIES", "TOTAL LIABILITIES"],
            "equity": ["CAPITAL", "EQUITY", "TOTAL CAPITAL"]
        },
        "fuzzy_match_threshold": 80,
        "confidence_weights": {
            "exact_account_match": 1.0,
            "fuzzy_account_match": 0.8,
            "amount_extracted": 0.9,
            "section_found": 0.7
        }
    }'::jsonb,
    TRUE
);

-- 2. INCOME STATEMENT TEMPLATE
INSERT INTO extraction_templates (
    template_name,
    document_type,
    template_structure,
    keywords,
    extraction_rules,
    is_default
) VALUES (
    'standard_income_statement',
    'income_statement',
    '{
        "sections": [
            {"name": "INCOME", "subsections": ["Base Rentals", "Reimbursements", "Other Income"]},
            {"name": "OPERATING EXPENSES", "subsections": ["Utilities", "Contracted", "R&M", "Administration"]},
            {"name": "ADDITIONAL EXPENSES", "subsections": ["Management Fees", "Professional Fees", "LL Expenses"]},
            {"name": "OTHER EXPENSES", "subsections": ["Mortgage Interest", "Depreciation", "Amortization"]}
        ],
        "required_fields": ["total_income", "total_expenses", "net_operating_income", "net_income"],
        "columns": ["period_amount", "ytd_amount", "period_percentage", "ytd_percentage"],
        "validation": "net_income = total_income - total_expenses - interest - depreciation - amortization",
        "account_code_pattern": "####-####",
        "typical_accounts": {
            "income": ["4010-0000", "4020-0000", "4030-0000", "4040-0000"],
            "operating_expenses": ["5010-0000", "5105-0000", "5200-0000", "5300-0000"],
            "additional_expenses": ["6010-0000", "6014-0000", "6020-0000"],
            "other_expenses": ["7010-0000", "7020-0000", "7030-0000"]
        }
    }'::jsonb,
    ARRAY[
        'income statement',
        'profit and loss',
        'p&l',
        'statement of operations',
        'revenue',
        'expenses',
        'net income',
        'operating income',
        'gross profit',
        'net operating income',
        'period to date',
        'year to date'
    ],
    '{
        "amount_patterns": ["\\$?[\\d,]+\\.\\d{2}", "\\([\\d,]+\\.\\d{2}\\)"],
        "percentage_patterns": ["\\d+\\.\\d+%", "\\d+%"],
        "multi_column_support": true,
        "column_headers": ["Period", "YTD", "%", "% YTD"],
        "section_detection": {
            "income": ["INCOME", "REVENUE", "TOTAL INCOME"],
            "operating_expenses": ["OPERATING EXPENSES", "TOTAL OPERATING EXPENSES"],
            "noi": ["NET OPERATING INCOME", "NOI"],
            "net_income": ["NET INCOME", "NET LOSS"]
        },
        "fuzzy_match_threshold": 80,
        "confidence_weights": {
            "exact_match": 1.0,
            "fuzzy_match": 0.8,
            "period_amount": 1.0,
            "ytd_amount": 0.9,
            "percentages": 0.7
        }
    }'::jsonb,
    TRUE
);

-- 3. CASH FLOW STATEMENT TEMPLATE
INSERT INTO extraction_templates (
    template_name,
    document_type,
    template_structure,
    keywords,
    extraction_rules,
    is_default
) VALUES (
    'standard_cash_flow',
    'cash_flow',
    '{
        "sections": [
            {"name": "OPERATING ACTIVITIES", "subsections": ["Cash from operations", "Changes in working capital"]},
            {"name": "INVESTING ACTIVITIES", "subsections": ["Capital expenditures", "Asset sales"]},
            {"name": "FINANCING ACTIVITIES", "subsections": ["Loan proceeds", "Debt payments", "Distributions"]}
        ],
        "required_fields": ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow", "net_cash_flow", "beginning_cash", "ending_cash"],
        "validation": "net_cash_flow = operating + investing + financing AND ending_cash = beginning_cash + net_cash_flow",
        "cash_flow_categories": ["operating", "investing", "financing"],
        "typical_line_items": {
            "operating": ["Net income", "Depreciation", "Amortization", "Changes in AR", "Changes in AP"],
            "investing": ["Purchase of equipment", "Sale of assets", "Capital improvements"],
            "financing": ["Loan proceeds", "Debt repayment", "Partner distributions", "Capital contributions"]
        }
    }'::jsonb,
    ARRAY[
        'cash flow',
        'statement of cash flows',
        'cash flows from operating',
        'cash flows from investing',
        'cash flows from financing',
        'net increase in cash',
        'net decrease in cash',
        'beginning cash balance',
        'ending cash balance'
    ],
    '{
        "amount_patterns": ["\\$?[\\d,]+\\.\\d{2}", "\\([\\d,]+\\.\\d{2}\\)"],
        "category_detection": {
            "operating": ["operating activities", "cash from operations"],
            "investing": ["investing activities", "capital expenditure"],
            "financing": ["financing activities", "loan proceeds", "distributions"]
        },
        "inflow_keywords": ["proceeds", "collections", "income", "receipts"],
        "outflow_keywords": ["payments", "expenditures", "distributions", "repayment"],
        "fuzzy_match_threshold": 80
    }'::jsonb,
    TRUE
);

-- 4. RENT ROLL TEMPLATE
INSERT INTO extraction_templates (
    template_name,
    document_type,
    template_structure,
    keywords,
    extraction_rules,
    is_default
) VALUES (
    'standard_rent_roll',
    'rent_roll',
    '{
        "columns": [
            "unit_number",
            "tenant_name",
            "lease_type",
            "lease_start_date",
            "lease_end_date",
            "unit_area_sqft",
            "monthly_rent",
            "annual_rent",
            "rent_per_sqft",
            "security_deposit",
            "occupancy_status"
        ],
        "required_fields": ["unit_number", "tenant_name", "monthly_rent", "annual_rent"],
        "validation": "total_annual_rent = SUM(tenant_annual_rents) AND occupancy_rate = (occupied_units / total_units) * 100",
        "occupancy_statuses": ["occupied", "vacant", "notice"],
        "lease_types": ["NNN", "Gross", "Modified Gross", "Percentage"],
        "calculations": {
            "monthly_rent_per_sqft": "monthly_rent / unit_area_sqft",
            "annual_rent": "monthly_rent * 12",
            "annual_rent_per_sqft": "annual_rent / unit_area_sqft"
        }
    }'::jsonb,
    ARRAY[
        'rent roll',
        'tenant',
        'lease',
        'unit',
        'sq ft',
        'square feet',
        'monthly rent',
        'annual rent',
        'lease expiration',
        'occupancy',
        'vacant',
        'security deposit'
    ],
    '{
        "table_detection": true,
        "multi_row_extraction": true,
        "unit_number_pattern": "[A-Z]-?\\d+",
        "date_patterns": ["\\d{1,2}/\\d{1,2}/\\d{2,4}", "[A-Za-z]+ \\d{1,2},? \\d{4}"],
        "amount_patterns": ["\\$?[\\d,]+\\.\\d{2}", "\\$?[\\d,]+"],
        "sqft_pattern": "[\\d,]+\\.?\\d*",
        "percentage_pattern": "\\d+\\.\\d+%",
        "fuzzy_match_threshold": 75,
        "require_tenant_name": true,
        "minimum_rows": 1
    }'::jsonb,
    TRUE
);

-- Display seeded templates
SELECT 'Extraction Templates Seeded' as status, COUNT(*) as total_templates FROM extraction_templates WHERE is_default = TRUE;
SELECT template_name, document_type, array_length(keywords, 1) as keyword_count FROM extraction_templates WHERE is_default = TRUE ORDER BY document_type;

