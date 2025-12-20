# Mortgage Statement User Guide

## Overview

The REIMS2 system now supports mortgage statement uploads and analysis. This guide explains how to upload mortgage statements, view mortgage data, and understand the mortgage metrics.

## Uploading Mortgage Statements

### Step 1: Navigate to Document Upload
1. Go to the **Portfolio Hub** or **Documents** page
2. Click **"Upload Document"** button
3. Select **"Mortgage Statement"** from the document type dropdown

### Step 2: Provide Document Information
- **Property Code**: Select the property (e.g., ESP001)
- **Period**: Select the year and month for the statement
- **File**: Choose the mortgage statement PDF file

### Step 3: Upload
- Click **"Upload"** to submit the document
- The system will automatically:
  - Extract mortgage data from the PDF
  - Validate the extracted data
  - Calculate mortgage metrics
  - Link to existing lenders (if applicable)

## Viewing Mortgage Data

### Portfolio Hub - Financials Tab
1. Select a property from the property list
2. Click on the **"Financials"** tab
3. Scroll to the **"Mortgage Metrics"** section
4. View:
   - DSCR (Debt Service Coverage Ratio) gauge
   - LTV (Loan-to-Value) gauge
   - Total debt service (monthly/annual)
   - Total mortgage debt

### Financial Command Page
1. Navigate to **Financial Command**
2. Select a property
3. Click **"View Full Financial Data"**
4. Select **"Mortgage Statement"** from the statement type buttons
5. View:
   - Mortgage statements table
   - Mortgage metrics
   - Click on a mortgage to view details

### Mortgage Detail View
Click the **eye icon** on any mortgage in the table to view:
- **Loan Information**: Loan number, type, terms, maturity date
- **Current Balances**: Principal, escrow balances, total loan balance
- **Payment Breakdown**: Principal due, interest due, escrow due, total payment
- **Year-to-Date Totals**: Principal paid, interest paid, total paid
- **Payment History**: Historical payment records

## Understanding Mortgage Metrics

### DSCR (Debt Service Coverage Ratio)
- **Formula**: NOI / Annual Debt Service
- **Healthy**: ≥ 1.25 (green indicator)
- **Warning**: 1.10 - 1.25 (yellow indicator)
- **Critical**: < 1.10 (red indicator)
- **Threshold**: 1.20 (covenant minimum)

**What it means**: 
- DSCR of 1.25 means the property generates $1.25 for every $1.00 of debt service
- Values below 1.20 may violate loan covenants

### LTV (Loan-to-Value Ratio)
- **Formula**: Total Mortgage Debt / Property Value
- **Compliant**: ≤ 80% (green indicator)
- **Warning**: 80% - 90% (yellow indicator)
- **Breach**: > 90% (red indicator)
- **Maximum**: 80% (typical commercial loan limit)

**What it means**:
- LTV of 75% means the loan is 75% of the property value
- Higher LTV indicates higher leverage and risk

### Total Debt Service
- **Monthly**: Sum of all monthly principal + interest payments
- **Annual**: Monthly debt service × 12
- Used in DSCR calculation

### Total Mortgage Debt
- Sum of all principal balances across all mortgages
- Used in LTV calculation

### Weighted Average Interest Rate
- Average interest rate weighted by principal balance
- Formula: (Mortgage1 Balance × Rate1 + Mortgage2 Balance × Rate2) / Total Balance

### Interest Coverage Ratio
- **Formula**: EBIT / Interest Expense
- Measures ability to pay interest from operating income
- Higher is better (typically > 2.0x)

### Debt Yield
- **Formula**: NOI / Total Loan Amount × 100
- Expressed as a percentage
- Higher debt yield indicates better loan quality

### Break-Even Occupancy
- **Formula**: (Operating Expenses + Debt Service) / Gross Potential Rent × 100
- Minimum occupancy needed to cover all expenses
- Lower is better

## Mortgage Trends

### DSCR History
- View DSCR trend over the last 12 months
- Identify improving or declining trends
- Compare against 1.20 threshold line

### LTV History
- View LTV trend over time
- Track principal paydown
- Monitor against 80% maximum line

## Validation and Quality

### Extraction Confidence
- Percentage indicating extraction accuracy
- Higher confidence (≥ 90%) = more reliable
- Lower confidence (< 70%) = may need review

### Validation Status
- **OK** (green): All validations passed
- **Review** (yellow): Needs manual review
- **Errors** (red): Validation failures detected

### Common Validation Rules
1. **Principal Balance Reasonableness**: Between $0 and $100M
2. **Payment Calculation**: Total payment = sum of components
3. **Escrow Balance Total**: Escrow balances sum correctly
4. **Interest Rate Range**: Between 0% and 20%
5. **YTD Totals**: YTD payments match sum of components
6. **DSCR Minimum**: DSCR ≥ 1.20
7. **LTV Maximum**: LTV ≤ 80%

## Cross-Document Reconciliation

The system automatically validates mortgage data against other financial documents:

### Balance Sheet Reconciliation
- Mortgage principal balances should match "Mortgage Payable" on balance sheet
- Tolerance: ±$100

### Income Statement Reconciliation
- Mortgage interest should match "Interest Expense" on income statement
- Tolerance: ±$100

## Troubleshooting

### Mortgage Not Appearing
- Check that extraction completed successfully
- Verify property and period selection
- Review extraction confidence score

### Incorrect DSCR/LTV
- Verify mortgage data is complete
- Check that NOI is calculated correctly
- Ensure property value is set in balance sheet

### Validation Failures
- Review validation error messages
- Check cross-document reconciliation
- Verify data accuracy in source documents

## Best Practices

1. **Upload Promptly**: Upload mortgage statements as soon as received
2. **Review Extractions**: Check extraction confidence and review low-confidence items
3. **Monitor Metrics**: Regularly check DSCR and LTV trends
4. **Reconcile Monthly**: Verify mortgage data matches balance sheet and income statement
5. **Track Maturities**: Use maturity calendar to plan refinancing

## Support

For issues or questions:
- Check validation error messages for guidance
- Review extraction confidence scores
- Contact system administrator for assistance


