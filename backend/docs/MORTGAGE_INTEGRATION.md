# Mortgage Statement Integration - Technical Documentation

## Overview

This document describes the technical implementation of mortgage statement integration into the REIMS2 system. Mortgage statements are now treated as a first-class document type alongside balance sheets, income statements, cash flow statements, and rent rolls.

## Architecture

### Database Schema

#### Core Tables

1. **mortgage_statement_data**
   - Stores extracted mortgage statement information
   - Key fields: loan_number, principal_balance, interest_rate, payment_due, escrow balances
   - Includes calculated fields: total_loan_balance, remaining_term_months
   - Links to: properties, financial_periods, document_uploads, lenders

2. **mortgage_payment_history**
   - Tracks individual payment transactions
   - Fields: payment_date, principal_paid, interest_paid, total_payment
   - Links to: mortgage_statement_data, properties

3. **financial_metrics** (Extended)
   - Added 8 new mortgage-specific columns:
     - `total_mortgage_debt`
     - `weighted_avg_interest_rate`
     - `total_monthly_debt_service`
     - `total_annual_debt_service`
     - `dscr` (Debt Service Coverage Ratio)
     - `interest_coverage_ratio`
     - `debt_yield`
     - `break_even_occupancy`

### Extraction Pipeline

1. **Document Upload**
   - Mortgage statements uploaded via standard document upload endpoint
   - Stored in MinIO at: `{property_code}/{period}/mortgage-statement/`
   - Document type: `mortgage_statement`

2. **Extraction Service**
   - `MortgageExtractionService` handles mortgage-specific extraction
   - Uses field patterns from `extraction_templates` table
   - Matches lenders to `lenders` master table
   - Calculates derived fields (total_loan_balance, remaining_term_months)
   - Stores extraction coordinates for review

3. **Validation**
   - 10 mortgage-specific validation rules
   - Cross-document validation:
     - Mortgage principal vs. Balance Sheet mortgage payable
     - Mortgage interest vs. Income Statement interest expense
   - Validation results stored in `validation_results` table

### Financial Calculations

#### DSCR (Debt Service Coverage Ratio)
```
DSCR = Net Operating Income / Annual Debt Service
```
- Uses actual mortgage statement data for debt service
- Falls back to income statement estimates if mortgage data unavailable
- Threshold: 1.20 (configurable)

#### LTV (Loan-to-Value Ratio)
```
LTV = Total Mortgage Debt / Property Value
```
- Uses principal balances from mortgage statements
- Property value from balance sheet (Total Property & Equipment)

#### Additional Metrics
- **Debt Yield**: NOI / Total Loan Amount * 100
- **Interest Coverage Ratio**: EBIT / Interest Expense
- **Break-Even Occupancy**: (Operating Expenses + Debt Service) / Gross Potential Rent * 100
- **Weighted Average Interest Rate**: Calculated across all mortgages

## API Endpoints

### Mortgage Management
- `GET /api/v1/mortgage/properties/{property_id}/periods/{period_id}` - Get mortgages for property/period
- `GET /api/v1/mortgage/{mortgage_id}` - Get mortgage detail with payment history
- `PUT /api/v1/mortgage/{mortgage_id}` - Update mortgage statement
- `DELETE /api/v1/mortgage/{mortgage_id}` - Delete mortgage statement

### Analytics
- `GET /api/v1/mortgage/properties/{property_id}/dscr-history` - DSCR trend over time
- `GET /api/v1/mortgage/properties/{property_id}/ltv-history` - LTV trend over time
- `GET /api/v1/mortgage/properties/{property_id}/periods/{period_id}/debt-summary` - Comprehensive debt summary
- `GET /api/v1/mortgage/covenant-monitoring` - Covenant compliance dashboard
- `GET /api/v1/mortgage/maturity-calendar` - Loan maturity calendar

## Services

### MortgageExtractionService
- Extracts mortgage data from PDF text
- Pattern matching using regex from extraction templates
- Lender matching (fuzzy matching against lenders table)
- Confidence score calculation
- Derived field calculation

### ValidationService
- Mortgage-specific validation rules
- Cross-document reconciliation
- Validation result storage

### MetricsService
- `calculate_mortgage_metrics()` - Calculates all 8 mortgage KPIs
- Integrates with existing metrics calculation pipeline

### DSCRMonitoringService
- Updated `_get_total_debt_service()` to prioritize mortgage statement data
- Falls back to income statement estimates if needed

## Seed Data

### Extraction Templates
- File: `backend/scripts/seed_mortgage_extraction_templates.sql`
- Template: "Standard Mortgage Statement"
- Field patterns for: loan_number, statement_date, principal_balance, interest_rate, payment_due, escrow_balance

### Validation Rules
- File: `backend/scripts/seed_mortgage_validation_rules.sql`
- 10 validation rules:
  1. Principal balance reasonableness
  2. Payment calculation
  3. Escrow balance total
  4. Interest rate range
  5. YTD totals
  6. Principal reduction
  7. DSCR minimum threshold
  8. LTV maximum threshold
  9. Balance sheet reconciliation
  10. Income statement reconciliation

## Frontend Components

### Components
- `MortgageDataTable` - Table view of mortgage statements
- `MortgageMetrics` - DSCR/LTV gauges and debt service summary
- `MortgageDetail` - Detailed mortgage view with payment history
- `MortgageTrends` - DSCR/LTV trend charts
- `MortgageMetricsWidget` - Wrapper for PortfolioHub integration

### Integration Points
- **PortfolioHub**: Mortgage metrics widget in financials tab
- **FinancialCommand**: Mortgage statement viewing capability
- **DocumentUpload**: Mortgage statement upload option

## Testing

### Unit Tests
- `test_mortgage_extraction.py` - Extraction logic, pattern matching
- `test_mortgage_validation.py` - All 10 validation rules
- `test_mortgage_formulas.py` - DSCR, LTV, debt yield calculations

### Integration Tests
- `test_mortgage_api.py` - API endpoint tests
- `test_mortgage_cross_document.py` - Cross-document validation

## Migration

### Alembic Migration
- File: `backend/alembic/versions/20251219_1901_add_mortgage_statement_tables.py`
- Creates `mortgage_statement_data` and `mortgage_payment_history` tables
- Adds 8 columns to `financial_metrics`
- Updates `document_uploads` constraint to include `mortgage_statement`

## Configuration

### MinIO Storage
- Folder: `mortgage-statement`
- Path pattern: `{property_code}/{period}/mortgage-statement/{filename}`

### Document Type Enum
- Added `mortgage_statement` to `DocumentTypeEnum` in `backend/app/schemas/document.py`
- Added to frontend `DocumentType` in `src/types/api.ts`

## Future Enhancements

1. **Amortization Schedule Generation**
   - Auto-generate amortization tables from mortgage data

2. **Loan Covenant Tracking**
   - Monitor all loan covenants (not just DSCR/LTV)

3. **Refinancing Analysis**
   - Compare current loan vs. market rates

4. **Prepayment Scenarios**
   - Model impact of principal prepayments

5. **Loan Servicing Integration**
   - API integration with loan servicers

6. **Automated Alerts**
   - Email alerts for upcoming payments, covenant breaches

## Troubleshooting

### Common Issues

1. **Extraction Fails**
   - Check extraction template patterns match document format
   - Verify lender matching logic
   - Review extraction confidence scores

2. **Validation Failures**
   - Check cross-document reconciliation
   - Verify balance sheet and income statement data
   - Review validation rule thresholds

3. **DSCR Calculation Issues**
   - Ensure mortgage data is loaded for the period
   - Check NOI calculation from income statement
   - Verify debt service calculation

## References

- Database Schema: See Alembic migration file
- API Documentation: See FastAPI auto-generated docs at `/docs`
- Frontend Types: `src/types/mortgage.ts`
- Service Implementation: `backend/app/services/mortgage_extraction_service.py`


