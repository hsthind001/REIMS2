# Anomaly Detection Logic - How Actual and Expected Values Are Calculated

## Overview
The anomaly detection system compares **current period values** against **historical baseline values** using statistical methods to identify unusual changes in financial data.

---

## 1. ACTUAL VALUE Calculation

### Source
- **Current Period Data**: The actual value comes from the **most recently uploaded document** for the property
- **Data Source**: Extracted from Income Statement or Balance Sheet line items
- **Aggregation**: All line items with the same account code are **summed together** for the current period

### Example
For account code `4010-0000` (Base Rental Income) in ESP 2024-12:
- If there are multiple line items with account `4010-0000` in the income statement
- **Actual Value** = Sum of all `period_amount` values for that account code
- Example: `$2,726,029.62` (sum of all 4010-0000 entries in 2024-12)

### Code Location
```python
# backend/app/services/extraction_orchestrator.py (lines 1514-1519)
current_totals = {}
for item in current_data:
    account_code = item.account_code
    if account_code not in current_totals:
        current_totals[account_code] = 0
    current_totals[account_code] += float(item.period_amount or 0)
```

---

## 2. EXPECTED VALUE Calculation

### Source
- **Historical Periods**: Data from previous periods (up to 12 months back)
- **Method**: **Arithmetic Mean** (average) of all historical values for the same account code
- **Period Selection**: 
  - Looks back up to 365 days from current period start date
  - Excludes the current period
  - Includes all available historical periods (minimum 1 required)

### Calculation Formula
```
Expected Value = Mean(Historical Values)
              = Sum(Historical Values) / Count(Historical Values)
```

### Example
For account code `4010-0000`:
- **2023-12**: `$229,422.31`
- **Expected Value** = `$229,422.31` (only one historical period available)
- If multiple periods: `Expected Value = ($229,422.31 + $250,000 + ...) / N`

### Code Location
```python
# backend/app/services/anomaly_detector.py (line 97)
recent_avg = statistics.mean(historical_values)

# backend/app/services/extraction_orchestrator.py (line 1568)
expected_value = str(statistics.mean(historical_values))
```

---

## 3. ANOMALY DETECTION METHODS

### Method 1: Percentage Change Detection (Primary Method)

**Formula:**
```
Percentage Change = |(Actual Value - Expected Value) / Expected Value| × 100
```

**Thresholds:**
- **Medium Severity**: > 15% change
- **High Severity**: > 25% change  
- **Critical Severity**: > 50% change

**Example:**
- Actual: `$6,586.90`
- Expected: `$745.62`
- Change: `|(6586.90 - 745.62) / 745.62| × 100 = 783.4%`
- **Result**: Critical anomaly (783.4% > 50%)

**Code Location:**
```python
# backend/app/services/anomaly_detector.py (lines 87-111)
pct_change = abs((value - recent_avg) / recent_avg)
if pct_change > self.percentage_change_threshold:  # 0.15 = 15%
    return {
        "type": "percentage_change",
        "percentage_change": round(pct_change * 100, 2),
        "severity": "critical" if pct_change > 0.5 else "high" if pct_change > 0.25 else "medium"
    }
```

---

### Method 2: Z-Score Detection (Secondary Method)

**When Used:** Only when 2+ historical periods are available (requires standard deviation)

**Formula:**
```
Z-Score = (Actual Value - Mean) / Standard Deviation
```

**Thresholds:**
- **High Severity**: |Z-Score| > 2.0 (2 standard deviations)
- **Critical Severity**: |Z-Score| > 4.0 (4 standard deviations)

**Example:**
- Historical values: `[$100, $110, $105, $120]`
- Mean: `$108.75`
- Standard Deviation: `$8.54`
- Actual: `$200`
- Z-Score: `(200 - 108.75) / 8.54 = 10.68`
- **Result**: Critical anomaly (10.68 > 4.0)

**Code Location:**
```python
# backend/app/services/anomaly_detector.py (lines 60-85)
mean = statistics.mean(historical_values)
stdev = statistics.stdev(historical_values)
z_score = (value - mean) / stdev
if abs(z_score) > self.z_score_threshold:  # 2.0
    return {
        "type": "z_score",
        "z_score": round(z_score, 4),
        "severity": "critical" if abs(z_score) > 4 else "high"
    }
```

---

## 4. DATA AGGREGATION PROCESS

### Step-by-Step Flow

1. **Get Current Period Data**
   - Query all income statement/balance sheet records for current period
   - Group by account code
   - Sum all amounts for each account code

2. **Get Historical Periods**
   - Find all periods within last 365 days
   - Exclude current period
   - Order by date (most recent first)

3. **Get Historical Data**
   - Query all records for historical periods
   - Group by period ID and account code
   - Sum amounts per period per account

4. **Build Comparison Groups**
   - For each account code:
     - Current: Sum of current period values
     - Historical: List of sums per historical period

5. **Filter Zero Values**
   - Remove zero values from historical data
   - Ensures meaningful comparisons

6. **Run Detection**
   - Calculate percentage change (always)
   - Calculate Z-score (if 2+ historical values)
   - Flag if thresholds exceeded

7. **Store Results**
   - Save to `anomaly_detections` table
   - Store: actual value, expected value, percentage change, Z-score, severity

---

## 5. CONFIDENCE SCORE

**Current Value:** `85%` (0.85)

**Meaning:** The system is 85% confident that the detected anomaly is genuine and not a false positive.

**Factors Considered:**
- Statistical significance of the deviation
- Number of historical data points available
- Consistency of historical data

---

## 6. EXAMPLE CALCULATION

### Scenario: ESP001 Account 4010-0000

**Current Period (2024-12):**
- Actual Value: `$2,726,029.62`

**Historical Period (2023-12):**
- Historical Value: `$229,422.31`

**Calculation:**
```
Expected Value = Mean([$229,422.31]) = $229,422.31

Percentage Change = |($2,726,029.62 - $229,422.31) / $229,422.31| × 100
                   = |$2,496,607.31 / $229,422.31| × 100
                   = 1,088.21%
```

**Result:**
- **Anomaly Detected**: ✅ Yes
- **Type**: Percentage Change
- **Severity**: Critical (1,088% > 50%)
- **Confidence**: 85%

---

## 7. LIMITATIONS & CONSIDERATIONS

### Current Limitations:
1. **Limited Historical Data**: Most properties only have 2 periods (2023-12 and 2024-12)
   - Z-score detection requires 2+ periods
   - Percentage change works with 1+ period

2. **No Seasonality Adjustment**: 
   - System doesn't account for seasonal variations
   - Year-over-year comparisons may flag normal seasonal changes

3. **No Business Rules Integration**:
   - Currently uses pure statistical methods
   - Doesn't incorporate property-specific business rules or thresholds

4. **Account Code Matching**:
   - Relies on exact account code matching
   - Doesn't handle account code changes or reclassifications

### Future Enhancements:
- Weighted averages (more recent periods weighted higher)
- Moving averages for trend analysis
- Seasonal adjustment factors
- Property-specific thresholds
- Account code mapping for historical changes

---

## 8. CONFIGURATION

### Current Thresholds (in `anomaly_detector.py`):

```python
z_score_threshold = 2.0          # 2 standard deviations
percentage_change_threshold = 0.15  # 15% change
```

### Severity Mapping:

**Percentage Change:**
- Medium: 15% - 25%
- High: 25% - 50%
- Critical: > 50%

**Z-Score:**
- High: 2.0 - 4.0
- Critical: > 4.0

---

## Summary

**Actual Value** = Sum of current period line items for an account code  
**Expected Value** = Average (mean) of historical period values for the same account code  
**Detection** = Compare actual vs expected using percentage change and/or Z-score  
**Threshold** = Flag if change exceeds 15% (percentage) or 2.0 (Z-score)

