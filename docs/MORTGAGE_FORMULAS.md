# Mortgage Financial Formulas

This document describes all financial formulas that use mortgage statement data in the REIMS2 system.

## Core Formulas

### 1. Debt Service Coverage Ratio (DSCR)

**Formula:**
```
DSCR = Net Operating Income (NOI) / Annual Debt Service
```

**Components:**
- **NOI**: From Income Statement (account code 5999-0000)
- **Annual Debt Service**: Sum of (Principal + Interest) payments from all mortgage statements for the period, annualized

**Calculation:**
```python
# Get NOI from income statement
noi = income_statement.get_account('5999-0000').amount

# Get total annual debt service from mortgage statements
mortgages = get_mortgages(property_id, period_id)
total_annual_debt_service = sum(
    mortgage.annual_debt_service or (mortgage.monthly_debt_service * 12)
    for mortgage in mortgages
)

dscr = noi / total_annual_debt_service
```

**Interpretation:**
- **≥ 1.25**: Healthy (green)
- **1.10 - 1.25**: Warning (yellow)
- **< 1.10**: Critical (red)
- **Threshold**: 1.20 (typical covenant minimum)

**Example:**
- NOI: $1,500,000
- Annual Debt Service: $1,080,000
- DSCR: 1,500,000 / 1,080,000 = **1.39**

---

### 2. Loan-to-Value Ratio (LTV)

**Formula:**
```
LTV = Total Mortgage Debt / Property Value
```

**Components:**
- **Total Mortgage Debt**: Sum of principal balances from all mortgage statements
- **Property Value**: From Balance Sheet (Total Property & Equipment, account code 1999-0000)

**Calculation:**
```python
# Get total mortgage balances
mortgages = get_mortgages(property_id, period_id)
total_mortgage_debt = sum(mortgage.principal_balance for mortgage in mortgages)

# Get property value from balance sheet
property_value = balance_sheet.get_account('1999-0000').amount

ltv = total_mortgage_debt / property_value
```

**Interpretation:**
- **≤ 80%**: Compliant (green)
- **80% - 90%**: Warning (yellow)
- **> 90%**: Breach (red)
- **Maximum**: 80% (typical commercial loan limit)

**Example:**
- Total Mortgage Debt: $10,000,000
- Property Value: $15,000,000
- LTV: 10,000,000 / 15,000,000 = **66.67%**

---

### 3. Debt Yield

**Formula:**
```
Debt Yield = (NOI / Total Loan Amount) × 100
```

**Components:**
- **NOI**: Net Operating Income
- **Total Loan Amount**: Sum of original loan amounts (or current principal balances)

**Calculation:**
```python
noi = income_statement.get_account('5999-0000').amount
total_loan_amount = sum(mortgage.original_loan_amount or mortgage.principal_balance 
                       for mortgage in mortgages)

debt_yield = (noi / total_loan_amount) * 100
```

**Interpretation:**
- Higher is better
- Typical range: 8% - 15%
- Indicates loan quality and risk

**Example:**
- NOI: $1,500,000
- Total Loan Amount: $10,000,000
- Debt Yield: (1,500,000 / 10,000,000) × 100 = **15%**

---

### 4. Interest Coverage Ratio

**Formula:**
```
Interest Coverage Ratio = EBIT / Interest Expense
```

**Components:**
- **EBIT**: Earnings Before Interest and Taxes (typically NOI as proxy)
- **Interest Expense**: Total annual interest from mortgage statements

**Calculation:**
```python
ebit = noi  # Using NOI as EBIT proxy
total_annual_interest = sum(
    mortgage.interest_due * 12  # Monthly to annual
    for mortgage in mortgages
)

interest_coverage = ebit / total_annual_interest
```

**Interpretation:**
- **≥ 2.0x**: Healthy
- **1.5x - 2.0x**: Acceptable
- **< 1.5x**: Risky
- Measures ability to pay interest from operating income

**Example:**
- EBIT (NOI): $1,500,000
- Annual Interest: $480,000
- Interest Coverage: 1,500,000 / 480,000 = **3.125x**

---

### 5. Break-Even Occupancy

**Formula:**
```
Break-Even Occupancy = ((Operating Expenses + Debt Service) / Gross Potential Rent) × 100
```

**Components:**
- **Operating Expenses**: From Income Statement
- **Debt Service**: Annual debt service from mortgage statements
- **Gross Potential Rent**: Total potential rental income

**Calculation:**
```python
operating_expenses = income_statement.get_total_expenses()
annual_debt_service = sum(mortgage.annual_debt_service for mortgage in mortgages)
gross_potential_rent = income_statement.get_account('4000-0000').amount  # Rental Income

break_even = ((operating_expenses + annual_debt_service) / gross_potential_rent) * 100
```

**Interpretation:**
- Lower is better
- Typical range: 60% - 80%
- Minimum occupancy needed to cover all expenses

**Example:**
- Operating Expenses: $500,000
- Debt Service: $1,080,000
- Gross Potential Rent: $2,000,000
- Break-Even: ((500,000 + 1,080,000) / 2,000,000) × 100 = **79%**

---

### 6. Weighted Average Interest Rate

**Formula:**
```
Weighted Avg Rate = Σ(Mortgage Balance × Interest Rate) / Σ(Mortgage Balances)
```

**Calculation:**
```python
total_weighted = sum(
    mortgage.principal_balance * mortgage.interest_rate
    for mortgage in mortgages
)
total_principal = sum(mortgage.principal_balance for mortgage in mortgages)

weighted_avg_rate = total_weighted / total_principal
```

**Example:**
- Mortgage 1: $8,000,000 at 5.0% = $400,000
- Mortgage 2: $2,000,000 at 6.0% = $120,000
- Total: $10,000,000
- Weighted Avg: (400,000 + 120,000) / 10,000,000 = **5.2%**

---

### 7. Total Loan Balance (Generated Column)

**Formula:**
```
Total Loan Balance = Principal Balance + Tax Escrow + Insurance Escrow + Reserve Balance + Other Escrow
```

**Database Implementation:**
```sql
total_loan_balance DECIMAL(15, 2) GENERATED ALWAYS AS (
  principal_balance + 
  tax_escrow_balance + 
  insurance_escrow_balance + 
  reserve_balance + 
  other_escrow_balance
) STORED
```

---

### 8. Remaining Term Months (Generated Column)

**Formula:**
```
Remaining Term = (Maturity Date - Statement Date) in months
```

**Database Implementation:**
```sql
remaining_term_months INTEGER GENERATED ALWAYS AS (
  EXTRACT(YEAR FROM AGE(maturity_date, statement_date)) * 12 + 
  EXTRACT(MONTH FROM AGE(maturity_date, statement_date))
) STORED
```

---

## Derived Calculations

### Monthly Debt Service
```python
monthly_debt_service = principal_due + interest_due
```

### Annual Debt Service
```python
annual_debt_service = monthly_debt_service * 12
# OR
annual_debt_service = (principal_due + interest_due) * 12
```

### YTD Total Paid
```python
ytd_total_paid = ytd_principal_paid + ytd_interest_paid
```

---

## Data Sources

### Mortgage Statement Data
- **Source**: `mortgage_statement_data` table
- **Key Fields**: `principal_balance`, `interest_rate`, `principal_due`, `interest_due`, `annual_debt_service`, `monthly_debt_service`

### Income Statement Data
- **Source**: `income_statement_data` table
- **Key Fields**: NOI (account 5999-0000), Interest Expense (account 6000-0000), Operating Expenses

### Balance Sheet Data
- **Source**: `balance_sheet_data` table
- **Key Fields**: Property Value (account 1999-0000), Mortgage Payable (account 2000-0000)

---

## Validation Thresholds

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| DSCR | ≥ 1.25 | 1.10 - 1.25 | < 1.10 |
| LTV | ≤ 80% | 80% - 90% | > 90% |
| Interest Coverage | ≥ 2.0x | 1.5x - 2.0x | < 1.5x |
| Debt Yield | ≥ 10% | 8% - 10% | < 8% |
| Break-Even Occupancy | ≤ 70% | 70% - 80% | > 80% |

---

## Notes

1. **Multiple Mortgages**: All formulas handle multiple mortgages per property by summing values
2. **Period Matching**: Calculations use data from the same financial period
3. **Fallback Logic**: If mortgage data unavailable, system falls back to income statement estimates
4. **Tolerance**: Cross-document reconciliation uses ±$100 tolerance for rounding differences


