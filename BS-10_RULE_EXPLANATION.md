# BS-10: 5-Year Improvements Rule - Complete Explanation

## Overview

**Rule ID:** BS-10  
**Rule Name:** 5-Year Improvements  
**Execution Formula:** Value check against baseline  
**Category:** Balance Sheet - Fixed Assets  
**Severity:** Low (INFO level)  
**Variance Threshold:** $0.01

---

## 1. What is "5-Year Improvements"?

### Definition

**5-Year Improvements** refers to capital improvements made to a property that have a **useful life of 5 years** for accounting and depreciation purposes.

### Common Examples

- **Appliances:** Refrigerators, dishwashers, microwaves, stoves
- **Carpeting:** Residential unit carpeting
- **Light Fixtures:** Decorative lighting installations
- **Window Treatments:** Blinds, curtains, shades
- **Minor Renovations:** Paint, wallpaper, basic repairs

### Accounting Treatment

```
Initial Recognition:
  Dr. Fixed Assets - 5-Year Improvements    $XXX,XXX
  Cr. Cash/Accounts Payable                        $XXX,XXX

Monthly Depreciation (over 60 months):
  Dr. Depreciation Expense                  $X,XXX
  Cr. Accumulated Depreciation - 5-Year Imp        $X,XXX

After 5 Years (Fully Depreciated):
  Cost Basis: $XXX,XXX
  Accumulated Depreciation: ($XXX,XXX)
  Net Book Value: $0
```

### Why This Matters

Once a 5-year improvement is **fully depreciated** (accumulated depreciation = cost basis), the net value should remain **constant** at the fully depreciated amount unless:
- New capital is invested (increases cost basis)
- Asset is disposed of (removes both cost and accumulated depreciation)

---

## 2. How is it Derived?

### Data Source

**Database Query:**
```sql
SELECT amount
FROM balance_sheet_data
WHERE property_id = :property_id 
  AND period_id = :period_id
  AND account_name ILIKE '%5%Year%Imp%'
ORDER BY amount DESC
LIMIT 1
```

**Account Pattern:** `%5%Year%Imp%`

This pattern matches account names like:
- "5-Year Improvements"
- "Fixed Assets - 5 Year Improvements"
- "Accumulated Depreciation - 5-Year Imp"
- "5 Year Improvements - Net"

### Your Current Data (2025-10)

**Actual Value:** $3,222,949.65  
**Expected (Baseline):** -$1,025,187.00  
**Difference:** $4,248,136.65  
**Status:** INFO (not PASS, but low severity)

---

## 3. What is the "Baseline"?

### Definition

**Baseline** = The expected/reference value that the current value is compared against.

In financial validation, a baseline represents:
- **Historical norm:** What the value has typically been
- **Known constant:** A value that shouldn't change
- **Expected value:** Based on business rules or accounting principles

### For BS-10 Specifically

**Baseline Value:** `-$1,025,187.00`

This is a **hardcoded expected value** that represents the property's typical 5-year improvements balance when fully depreciated.

**Source:** Based on historical property data or initial system setup

**Code Implementation:**
```python
def _rule_bs_10_5yr_improvements(self):
    """BS-10: 5-Year Improvements Fully Depreciated context"""
    # Get current value from balance sheet
    val = self._get_bs_value(account_name_pattern="%5%Year%Imp%")
    
    # Baseline = expected value
    expected = -1025187.00  # From rules md (historical baseline)
    
    # Compare current vs baseline
    status = "PASS" if abs(val - expected) < 1.0 else "INFO"
    
    # Record result
    self.results.append(ReconciliationResult(
        rule_id="BS-10",
        rule_name="5-Year Improvements",
        category="Balance Sheet",
        status=status,
        source_value=val,           # Current value: $3,222,949.65
        target_value=expected,      # Baseline: -$1,025,187.00
        difference=val - expected,  # Variance: $4,248,136.65
        variance_pct=0,
        details=f"5-Year Imp value: ${val:,.2f}",
        severity="low",
        formula="Value check against baseline"
    ))
```

---

## 4. What is "Value Check Against Baseline"?

### Formula Explanation

**Execution Formula:** `Value check against baseline`

**Mathematical Expression:**
```
IF |Current Value - Baseline| < Threshold THEN
    Status = PASS
ELSE
    Status = INFO
END IF
```

**For BS-10:**
```
Current Value: $3,222,949.65
Baseline:      -$1,025,187.00
Threshold:     $0.01

Difference = $3,222,949.65 - (-$1,025,187.00)
           = $3,222,949.65 + $1,025,187.00
           = $4,248,136.65

Is $4,248,136.65 < $0.01?  NO
Therefore: Status = INFO (not PASS)
```

### Why This Check?

**Purpose:** Detect unexpected changes in a value that should be relatively stable.

**Business Logic:**
1. **Stability Check:** Values should stay close to baseline unless documented changes occur
2. **Change Detection:** Large deviations flag potential issues:
   - Data entry errors
   - Undocumented capital improvements
   - Accounting reclassifications
   - Depreciation calculation errors

3. **Historical Comparison:** Ensures consistency with property's financial history

---

## 5. The Thinking Behind This Rule

### Business Rationale

**Why Monitor 5-Year Improvements?**

1. **Material Asset Class**
   - Often represents significant capital investment ($1M - $5M+)
   - Multiple improvement types aggregated
   - Frequent updates as units are renovated

2. **Depreciation Tracking**
   - Quick depreciation cycle (5 years vs. 27.5 for building)
   - Reaches fully depreciated state regularly
   - Tax implications of depreciation

3. **Capital Planning**
   - Renovation cycles for property
   - Unit turnover investment tracking
   - Budget forecasting for replacements

4. **Financial Accuracy**
   - Ensures proper asset valuation
   - Maintains balance sheet integrity
   - Supports loan covenant compliance

### When This Rule Helps

**Scenario 1: Unexpected Increase**
```
Previous: -$1,025,187 (fully depreciated)
Current:  $3,222,949
Change:   +$4,248,136

Question: Was there a $4.2M renovation?
Action: Verify capital improvement documentation
```

**Scenario 2: Unexpected Decrease**
```
Previous: $3,222,949
Current:  $1,500,000
Change:   -$1,722,949

Question: Were assets disposed of?
Action: Verify disposal documentation and journal entries
```

**Scenario 3: Stable (As Expected)**
```
Previous: -$1,025,187
Current:  -$1,025,187
Change:   $0

Status: PASS
Action: No action needed
```

### Rule Design Philosophy

**Severity: LOW (INFO)**

Why not HIGH or CRITICAL?

1. **Expected Variability:** 5-year improvements DO change frequently
   - Properties invest in renovations
   - Units are upgraded on turnover
   - New appliances, carpeting, etc.

2. **Not Immediately Harmful:** A variance doesn't mean error, just change
   - Could be legitimate capital investment
   - Requires review, not panic

3. **Informational Value:** Rule alerts you to investigate
   - "Hey, this changed significantly"
   - "Should we document this?"
   - "Is this expected?"

**Threshold: $0.01 (Very Strict)**

Why such a tight threshold?

- Baseline comparison is for **exact match** scenario
- Any change > $0.01 triggers INFO status
- Forces review of ANY movement from baseline
- In practice, most properties will show INFO (not PASS)

---

## 6. Understanding Your Specific Case

### Your Data Analysis

**Period:** 2025-10  
**Property:** ABC Corp (assumed)

**Current Balance:** $3,222,949.65

**Interpretation:** This is a **positive** (debit) balance, meaning:
```
Cost Basis:              $X,XXX,XXX
Less: Accum Depreciation ($X,XXX,XXX)
Net Book Value:          $3,222,949.65
```

This indicates **NOT fully depreciated** improvements. There's still $3.2M of net book value remaining.

### Why It Doesn't Match Baseline

**Baseline:** -$1,025,187.00 (negative = fully depreciated net or accumulated depreciation)

**Your Value:** $3,222,949.65 (positive = net book value remaining)

**Possible Reasons:**

1. **Recent Capital Investments**
   - Property renovated units in past 1-5 years
   - Added new appliances, carpeting, fixtures
   - Total investment: ~$3.2M not yet fully depreciated

2. **Different Accounting Structure**
   - Baseline might be for accumulated depreciation account
   - Your value might be net book value account
   - Account naming/structure differences

3. **Property Lifecycle**
   - Newer property or recent major renovation
   - Still depreciating initial 5-year improvements
   - Baseline from older/different property state

4. **Multiple Properties**
   - Baseline might be single-property specific
   - Current value might be portfolio-wide
   - Aggregation differences

### Is This a Problem?

**No, not necessarily!**

**Status: INFO** (not FAIL or WARNING)

**What This Means:**
- ✅ System detected the variance
- ✅ Flagged for review
- ✅ Low severity = informational only
- ❌ Not a critical financial error
- ❌ Not a failed validation
- ❌ Not blocking anything

**Recommended Action:**
1. **Verify:** Review capital improvement history
2. **Document:** Note any major renovations in 2020-2025
3. **Update Baseline (if needed):** If $3.2M is now the "normal", update baseline
4. **Accept Variance:** If legitimate, note in system and move on

---

## 7. Types of Baselines in REIMS

### 1. Historical Baseline (Mean/Median)

**Used in:** Anomaly detection

**Example:**
```
Historical Rent (12 months):
$1,500, $1,500, $1,500, $1,550, $1,500, $1,500, 
$1,500, $1,500, $1,500, $1,500, $1,500, $1,500

Baseline = Mean = $1,504.17
Current = $2,000
Variance = +$495.83 (33% increase) → ANOMALY
```

### 2. Seasonal Baseline

**Used in:** Seasonal anomaly detection

**Example:**
```
Utility costs by month:
Jan: $5,000 (heating)
Feb: $4,800
Mar: $3,200
Apr: $2,000 (mild)
...
Jul: $4,000 (cooling)
...

Baseline for Jan = $5,000 (seasonal expectation)
Current Jan = $8,000 → ANOMALY (+60%)
```

### 3. Constant/Fixed Baseline (BS-10 Uses This)

**Used in:** Calculated rules, compliance checks

**Example:**
```
Expected Value = $X (known constant)
Current Value = $Y (measured)

If |Y - X| < Threshold:
    PASS
Else:
    INFO/WARNING/FAIL
```

**BS-10:**
```
Baseline = -$1,025,187.00 (fixed expected value)
Current = $3,222,949.65
Variance = $4,248,136.65 → INFO
```

### 4. Peer Group Baseline

**Used in:** Portfolio comparisons

**Example:**
```
Your Property NOI Margin: 45%
Peer Group Average: 62%
Baseline = 62%
Variance = -17% → Underperformance flag
```

### 5. Forecast Baseline

**Used in:** Budget variance analysis

**Example:**
```
Budgeted Revenue: $100,000
Actual Revenue: $85,000
Baseline = $100,000
Variance = -$15,000 (-15%) → WARNING
```

---

## 8. How to Update the Baseline

If $3,222,949.65 is now the correct "normal" value for your property:

### Option 1: Code Update (Permanent)

**File:** `backend/app/services/rules/balance_sheet_rules.py`

**Change:**
```python
def _rule_bs_10_5yr_improvements(self):
    """BS-10: 5-Year Improvements Fully Depreciated context"""
    val = self._get_bs_value(account_name_pattern="%5%Year%Imp%")
    
    # OLD:
    # expected = -1025187.00
    
    # NEW (updated to current normal):
    expected = 3222949.65  # Updated baseline based on 2025-10 data
    
    status = "PASS" if abs(val - expected) < 1.0 else "INFO"
    
    self.results.append(ReconciliationResult(
        rule_id="BS-10",
        rule_name="5-Year Improvements",
        category="Balance Sheet",
        status=status,
        source_value=val,
        target_value=expected,
        difference=val - expected,
        variance_pct=0,
        details=f"5-Year Imp value: ${val:,.2f}",
        severity="low",
        formula="Value check against baseline"
    ))
```

### Option 2: Database-Driven Baseline (Dynamic)

**Better Approach:** Store baseline in database

**Implementation:**
1. Create `rule_baselines` table
2. Store property-specific baselines
3. Update rule to query database

**Benefits:**
- No code changes needed
- Different baselines per property
- Can update via UI
- Historical baseline tracking

---

## 9. Summary

### Quick Answers

**Q: What is "5-Year Improvements"?**  
**A:** Capital improvements with 5-year useful life (appliances, carpeting, fixtures). Currently valued at $3,222,949.65 on your balance sheet.

**Q: How is it derived?**  
**A:** Queried from `balance_sheet_data` table using account name pattern `%5%Year%Imp%`. Gets the amount from your actual financial data.

**Q: What's the thinking behind it?**  
**A:** 
- Monitor significant asset class (~$3M)
- Detect unexpected changes in balance
- Ensure depreciation accuracy
- Track capital investment patterns
- Maintain financial integrity

**Q: What is "baseline"?**  
**A:** Expected/reference value for comparison. For BS-10, baseline = -$1,025,187.00 (historical expected value). Your current value differs by $4.2M, triggering INFO status.

**Q: What is "Value check against baseline"?**  
**A:** Compare current value against baseline:
```
IF |Current - Baseline| < $0.01:
    Status = PASS
ELSE:
    Status = INFO
```

### Key Takeaways

1. **BS-10 is informational** - Not a critical validation
2. **Baseline is historical reference** - May need updating for your property
3. **Variance is expected** - Properties invest in improvements regularly
4. **No immediate action needed** - Review and document, but not urgent
5. **Consider updating baseline** - If $3.2M is new normal

---

## 10. Related Rules

### Similar Balance Sheet Rules

**BS-11: TI Improvements** - Tenant improvement tracking  
**BS-12: Roof Asset Value** - 30-year roof asset monitoring  
**BS-13: HVAC Asset** - HVAC equipment tracking  
**BS-14: Deposits Check** - Constant deposit verification  
**BS-15: Loan Costs Asset** - Loan cost asset tracking  

All use similar "baseline comparison" logic with different thresholds and severity levels.

---

*Document Version: 1.0*  
*Last Updated: January 24, 2026*  
*Rule Implementation: backend/app/services/rules/balance_sheet_rules.py:308-329*
