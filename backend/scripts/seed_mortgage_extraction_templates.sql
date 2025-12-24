-- Seed Extraction Templates for Mortgage Statements
-- Defines structure and field patterns for PDF parsing

-- Clear existing templates (idempotent)
DELETE FROM extraction_templates WHERE template_name = 'standard_mortgage_statement';

-- MORTGAGE STATEMENT TEMPLATE
INSERT INTO extraction_templates (
    template_name,
    document_type,
    template_structure,
    keywords,
    extraction_rules,
    is_default
) VALUES (
    'standard_mortgage_statement',
    'mortgage_statement',
    '{
        "sections": [
            {"name": "LOAN_IDENTIFICATION", "fields": ["loan_number", "property_address", "borrower_name", "lender_name"]},
            {"name": "CURRENT_BALANCES", "fields": ["principal_balance", "tax_escrow_balance", "insurance_escrow_balance", "reserve_balance", "suspense_balance"]},
            {"name": "PAYMENT_DETAILS", "fields": ["principal_due", "interest_due", "tax_escrow_due", "insurance_escrow_due", "reserve_due", "late_fees", "total_payment_due"]},
            {"name": "YTD_TOTALS", "fields": ["ytd_principal_paid", "ytd_interest_paid", "ytd_taxes_disbursed", "ytd_insurance_disbursed", "ytd_reserve_disbursed"]},
            {"name": "LOAN_TERMS", "fields": ["original_loan_amount", "interest_rate", "maturity_date", "loan_term_months", "payment_frequency", "amortization_type"]}
        ],
        "required_fields": ["loan_number", "statement_date", "principal_balance", "total_payment_due"],
        "field_patterns": {
            "loan_number": {
                "patterns": [
                    "Loan\\s+Number[:\\s]+([0-9]{6,})",
                    "Loan\\s+#[:\\s]+([0-9]{6,})",
                    "LOAN\\s+INFORMATION.*?Loan\\s+Number[:\\s]+([0-9]{6,})",
                    "Account[:\\s#]+([A-Z0-9\\-]{4,})",
                    "Loan\\s+ID[:\\s]+([A-Z0-9\\-]+)"
                ],
                "field_type": "text",
                "required": true
            },
            "statement_date": {
                "patterns": [
                    "LOAN\\s+INFORMATION\\s+As\\s+of\\s+Date\\s+(\\d{1,2}/\\d{1,2}/\\d{4})",
                    "PAYMENT\\s+INFORMATION\\s+As\\s+of\\s+Date\\s+(\\d{1,2}/\\d{1,2}/\\d{4})",
                    "As\\s+of\\s+Date\\s+(\\d{1,2}/\\d{1,2}/\\d{4})",
                    "Statement\\s+Date[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})",
                    "Date[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})"
                ],
                "field_type": "date",
                "required": true
            },
            "principal_balance": {
                "patterns": [
                    "Principal\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "BALANCES.*?Principal\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Outstanding\\s+Principal[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Current\\s+Principal[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Unpaid\\s+Principal[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": true
            },
            "interest_rate": {
                "patterns": ["Interest Rate[:\\s]+(\\d+\\.\\d+)%", "Current Rate[:\\s]+(\\d+\\.\\d+)%", "Note Rate[:\\s]+(\\d+\\.\\d+)%"],
                "field_type": "percentage",
                "required": false
            },
            "total_payment_due": {
                "patterns": ["Total Payment Due[:\\s]+\\$?([0-9,]+\\\\.\\\\d{2})", "Amount Due[:\\s]+\\$?([0-9,]+\\\\.\\\\d{2})", "Payment Amount[:\\s]+\\$?([0-9,]+\\\\.\\\\d{2})"],
                "field_type": "currency",
                "required": true
            },
            "principal_due": {
                "patterns": [
                    "Current\\s+Principal\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "PAYMENT\\s+INFORMATION.*?Current\\s+Principal\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Principal\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Principal\\s+Payment[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "interest_due": {
                "patterns": [
                    "Current\\s+Interest\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "PAYMENT\\s+INFORMATION.*?Current\\s+Interest\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Interest\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Interest\\s+Payment[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "tax_escrow_balance": {
                "patterns": [
                    "Tax\\s+Escrow\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "BALANCES.*?Tax\\s+Escrow\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Escrow\\s+for\\s+Taxes[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "insurance_escrow_balance": {
                "patterns": [
                    "Insurance\\s+Escrow\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "BALANCES.*?Insurance\\s+Escrow\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Escrow\\s+for\\s+Insurance[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "reserve_balance": {
                "patterns": [
                    "Reserve\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "BALANCES.*?Reserve\\s+Balance[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Reserve[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "maturity_date": {
                "patterns": ["Maturity Date[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})", "Loan Maturity[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})", "Final Payment Date[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})"],
                "field_type": "date",
                "required": false
            },
            "ytd_principal_paid": {
                "patterns": [
                    "YEAR\\s+TO\\s+DATE.*?Principal\\s+Paid[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "YTD.*?Principal\\s+Paid[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Year\\s+to\\s+Date\\s+Principal[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "ytd_interest_paid": {
                "patterns": [
                    "YEAR\\s+TO\\s+DATE.*?Interest\\s+Paid[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "YTD.*?Interest\\s+Paid[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Year\\s+to\\s+Date\\s+Interest[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "payment_due_date": {
                "patterns": [
                    "Payment\\s+Due\\s+Date[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})",
                    "Due\\s+Date[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})"
                ],
                "field_type": "date",
                "required": false
            },
            "tax_escrow_due": {
                "patterns": [
                    "Current\\s+Tax\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "PAYMENT\\s+INFORMATION.*?Current\\s+Tax\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Tax\\s+Escrow\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "insurance_escrow_due": {
                "patterns": [
                    "Current\\s+Insurance\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "PAYMENT\\s+INFORMATION.*?Current\\s+Insurance\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Insurance\\s+Escrow\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            },
            "reserve_due": {
                "patterns": [
                    "Current\\s+Reserves\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "PAYMENT\\s+INFORMATION.*?Current\\s+Reserves\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)",
                    "Reserve\\s+Due[:\\s]+\\$?([\\d,]+\\.?\\d*)"
                ],
                "field_type": "currency",
                "required": false
            }
        }
    }'::jsonb,
    ARRAY[
        'mortgage',
        'loan statement',
        'escrow',
        'principal balance',
        'interest rate',
        'payment due',
        'maturity date',
        'debt service',
        'amortization'
    ],
    '{
        "amount_patterns": ["\\$?[\\d,]+\\.\\d{2}"],
        "date_patterns": ["\\d{1,2}/\\d{1,2}/\\d{4}", "As of Date[:\\s]*(\\d{1,2}/\\d{1,2}/\\d{4})"],
        "percentage_patterns": ["\\d+\\.\\d+%"],
        "fuzzy_match_threshold": 85,
        "confidence_weights": {
            "exact_match": 1.0,
            "fuzzy_match": 0.8,
            "amount_extracted": 0.9,
            "date_extracted": 0.9,
            "section_found": 0.7
        }
    }'::jsonb,
    TRUE
);


