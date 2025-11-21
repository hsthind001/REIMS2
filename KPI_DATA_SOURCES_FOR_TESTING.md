# KPI Data Sources for Testing

This document identifies all the files and database tables that provide the KPI values displayed in the Command Center dashboard.

## Data Flow Overview

```
PDF Documents (Uploaded)
    ↓
Extraction Process (AI/ML)
    ↓
Raw Data Tables (balance_sheet_data, income_statement_data, rent_roll_data)
    ↓
Metrics Calculation (MetricsService)
    ↓
FinancialMetrics Table (Pre-calculated KPIs)
    ↓
API Endpoint (/api/v1/metrics/summary)
    ↓
Frontend Dashboard (CommandCenter.tsx)
```

---

## KPI Values and Their Sources

### 1. **Property Value** (`total_assets`)

**Displayed As:** $22.9M (in millions)

**Source Database Table:**
- `financial_metrics.total_assets` (pre-calculated)
- **Original Source:** `balance_sheet_data` table

**Calculation:**
- **File:** `backend/app/services/metrics_service.py`
- **Method:** `_calculate_balance_sheet_totals()` → Line 120
- **Formula:** Reads account code `'1999-0000'` (Total Assets) from balance sheet
- **Source Query:** `_get_balance_sheet_account(property_id, period_id, '1999-0000')`

**Database Tables:**
```sql
-- Pre-calculated (what dashboard uses)
SELECT property_id, period_id, total_assets 
FROM financial_metrics 
WHERE property_id = ? AND period_id = ?;

-- Raw source data
SELECT account_code, account_name, period_amount 
FROM balance_sheet_data 
WHERE property_id = ? 
  AND period_id = ? 
  AND account_code = '1999-0000';
```

**Model File:** `backend/app/models/balance_sheet_data.py`

---

### 2. **Property NOI** (`net_operating_income`)

**Displayed As:** $1.9M (in millions)

**Source Database Table:**
- `financial_metrics.net_operating_income` (pre-calculated)
- **Original Source:** `income_statement_data` table

**Calculation:**
- **File:** `backend/app/services/metrics_service.py`
- **Method:** `calculate_income_statement_metrics()` → Lines 350-407
- **Formula:** 
  - Reads from `income_statement_header.net_operating_income`
  - Or calculates: `total_revenue - total_expenses`
- **Source Query:** Gets NOI from Income Statement Header table

**Database Tables:**
```sql
-- Pre-calculated (what dashboard uses)
SELECT property_id, period_id, net_operating_income 
FROM financial_metrics 
WHERE property_id = ? AND period_id = ?;

-- Raw source data (Income Statement Header)
SELECT net_operating_income, total_income, total_expenses 
FROM income_statement_header 
WHERE property_id = ? AND period_id = ?;

-- Raw source data (Line items)
SELECT line_category, line_subcategory, period_amount 
FROM income_statement_data 
WHERE property_id = ? 
  AND period_id = ? 
  AND (line_subcategory LIKE '%Net Operating Income%' OR line_subcategory = 'NOI');
```

**Model Files:**
- `backend/app/models/income_statement_data.py`
- `backend/app/models/income_statement_header.py`

---

### 3. **Occupancy Rate** (`occupancy_rate`)

**Displayed As:** 93.8% (percentage)

**Source Database Table:**
- `financial_metrics.occupancy_rate` (pre-calculated)
- **Original Source:** `rent_roll_data` table

**Calculation:**
- **File:** `backend/app/services/metrics_service.py`
- **Method:** `calculate_rent_roll_metrics()` → Lines 464-500
- **Formula:** `(occupied_units / total_units) * 100`
- **Source Query:** Aggregates from rent roll data

**Database Tables:**
```sql
-- Pre-calculated (what dashboard uses)
SELECT property_id, period_id, occupancy_rate, occupied_units, total_units 
FROM financial_metrics 
WHERE property_id = ? AND period_id = ?;

-- Raw source data
SELECT 
    COUNT(*) as total_units,
    SUM(CASE WHEN unit_status = 'Occupied' THEN 1 ELSE 0 END) as occupied_units,
    SUM(CASE WHEN unit_status = 'Vacant' THEN 1 ELSE 0 END) as vacant_units
FROM rent_roll_data 
WHERE property_id = ? AND period_id = ?;
```

**Model File:** `backend/app/models/rent_roll_data.py`

---

### 4. **Property IRR** (`portfolioIRR`)

**Displayed As:** 14.2% (percentage)

**Source:**
- **API Endpoint:** `/api/v1/exit-strategy/portfolio-irr`
- **File:** `backend/app/api/v1/exit_strategy.py` (if exists)
- **Note:** Currently uses a fallback value of 14.2% if API unavailable
- **Calculation:** Complex calculation based on cash flows and property values over time

**Frontend Code:**
- **File:** `src/pages/CommandCenter.tsx` → Lines 176-194

---

## Key Files for Testing

### Backend API Endpoint
**File:** `backend/app/api/v1/metrics.py`
- **Endpoint:** `GET /api/v1/metrics/summary`
- **Lines:** 307-423
- **Returns:** List of `MetricsSummaryItem` with all KPI values

### Metrics Calculation Service
**File:** `backend/app/services/metrics_service.py`
- **Class:** `MetricsService`
- **Key Methods:**
  - `calculate_all_metrics()` - Main entry point (Line 34)
  - `calculate_balance_sheet_metrics()` - Property Value (Line 81)
  - `calculate_income_statement_metrics()` - NOI (Line 350)
  - `calculate_rent_roll_metrics()` - Occupancy Rate (Line 464)

### Database Models

1. **FinancialMetrics** (Pre-calculated KPIs)
   - **File:** `backend/app/models/financial_metrics.py`
   - **Table:** `financial_metrics`
   - **Key Columns:** `total_assets`, `net_operating_income`, `occupancy_rate`

2. **BalanceSheetData** (Raw Balance Sheet Data)
   - **File:** `backend/app/models/balance_sheet_data.py`
   - **Table:** `balance_sheet_data`
   - **Key Columns:** `account_code`, `account_name`, `period_amount`

3. **IncomeStatementData** (Raw Income Statement Data)
   - **File:** `backend/app/models/income_statement_data.py`
   - **Table:** `income_statement_data`
   - **Key Columns:** `line_category`, `line_subcategory`, `period_amount`

4. **IncomeStatementHeader** (Income Statement Totals)
   - **File:** `backend/app/models/income_statement_header.py`
   - **Table:** `income_statement_header`
   - **Key Columns:** `net_operating_income`, `total_income`, `total_expenses`

5. **RentRollData** (Raw Rent Roll Data)
   - **File:** `backend/app/models/rent_roll_data.py`
   - **Table:** `rent_roll_data`
   - **Key Columns:** `unit_status`, `unit_number`, `tenant_name`

### Frontend Component
**File:** `src/pages/CommandCenter.tsx`
- **Function:** `loadPortfolioHealth()` - Lines 124-223
- **API Call:** Fetches from `/api/v1/metrics/summary`
- **Display:** Lines 902-938 (KPI Cards)

---

## SQL Queries for Testing

### Get All KPI Values for a Property
```sql
SELECT 
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,
    fm.total_assets,
    fm.net_operating_income,
    fm.occupancy_rate,
    fm.total_revenue,
    fm.net_income
FROM financial_metrics fm
JOIN properties p ON fm.property_id = p.id
JOIN financial_periods fp ON fm.period_id = fp.id
WHERE p.property_code = 'WEND001'  -- Replace with your property code
ORDER BY fp.period_year DESC, fp.period_month DESC
LIMIT 1;
```

### Get Raw Balance Sheet Data (Property Value Source)
```sql
SELECT 
    account_code,
    account_name,
    period_amount,
    account_level
FROM balance_sheet_data
WHERE property_id = (
    SELECT id FROM properties WHERE property_code = 'WEND001'
)
AND period_id = (
    SELECT id FROM financial_periods 
    ORDER BY period_year DESC, period_month DESC 
    LIMIT 1
)
AND account_code = '1999-0000';  -- Total Assets
```

### Get Raw Income Statement Data (NOI Source)
```sql
SELECT 
    ish.net_operating_income,
    ish.total_income,
    ish.total_expenses,
    fp.period_year,
    fp.period_month
FROM income_statement_header ish
JOIN financial_periods fp ON ish.period_id = fp.id
WHERE ish.property_id = (
    SELECT id FROM properties WHERE property_code = 'WEND001'
)
ORDER BY fp.period_year DESC, fp.period_month DESC
LIMIT 1;
```

### Get Raw Rent Roll Data (Occupancy Rate Source)
```sql
SELECT 
    COUNT(*) as total_units,
    SUM(CASE WHEN unit_status = 'Occupied' THEN 1 ELSE 0 END) as occupied_units,
    SUM(CASE WHEN unit_status = 'Vacant' THEN 1 ELSE 0 END) as vacant_units,
    ROUND(
        (SUM(CASE WHEN unit_status = 'Occupied' THEN 1 ELSE 0 END)::DECIMAL / COUNT(*)::DECIMAL) * 100, 
        2
    ) as occupancy_rate
FROM rent_roll_data
WHERE property_id = (
    SELECT id FROM properties WHERE property_code = 'WEND001'
)
AND period_id = (
    SELECT id FROM financial_periods 
    ORDER BY period_year DESC, period_month DESC 
    LIMIT 1
);
```

---

## Testing Workflow

### 1. Check Current Database Values
```bash
# Connect to PostgreSQL
docker exec -it reims-postgres psql -U reims -d reims

# Run the queries above to see current values
```

### 2. Verify API Response
```bash
# Test the metrics summary endpoint
curl http://localhost:8000/api/v1/metrics/summary | jq '.[] | select(.property_code == "WEND001")'
```

### 3. Check Frontend Display
- Open browser: `http://localhost:5173`
- Navigate to Command Center
- Select property "WEND001 - Wendover Commons"
- Compare displayed values with database queries

### 4. Recalculate Metrics (if needed)
```bash
# Trigger metrics recalculation via API
curl -X POST http://localhost:8000/api/v1/metrics/WEND001/2024/12/recalculate
```

---

## Database Connection Details

**PostgreSQL Connection:**
- **Host:** localhost
- **Port:** 5433
- **Database:** reims
- **User:** reims
- **Password:** reims

**Docker Container:**
```bash
docker exec -it reims-postgres psql -U reims -d reims
```

**pgAdmin (Web UI):**
- URL: http://localhost:5050
- Email: admin@pgadmin.com
- Password: admin

---

## Notes

1. **Period Selection:** The dashboard shows the **latest period** (most recent year/month) for each property, not cumulative values.

2. **Metrics Calculation:** Metrics are automatically calculated when:
   - A document is uploaded and extracted
   - Metrics are manually recalculated via API
   - Background job runs (if configured)

3. **Data Flow:** Raw extracted data → Metrics calculation → FinancialMetrics table → API → Frontend

4. **Testing:** To test with different values:
   - Update raw data tables (`balance_sheet_data`, `income_statement_data`, `rent_roll_data`)
   - Recalculate metrics via API
   - Refresh dashboard

