# AUDIT-28: Constant Accounts Summary - Complete Explanation

**Date**: January 28, 2026  
**Rule ID**: `AUDIT-28`  
**Rule Name**: Constant Accounts Summary  
**Category**: Cross-Document Audit  
**Severity**: High

---

## 📋 Overview

**AUDIT-28** is a **period-over-period validation rule** that ensures certain balance sheet accounts designated as "constant" remain unchanged from their baseline values. This rule is critical for detecting unauthorized changes, data entry errors, or accounting irregularities in accounts that should remain stable.

---

## 🎯 What is "Constant Accounts Summary"?

**Constant Accounts** are balance sheet accounts that, by their nature, should **not change** from period to period unless there's a specific, documented business event (like a property sale, refinance, or capital contribution).

### **7 Account Categories Monitored:**

1. **CASH-OPERATING** (`%CASH%OPERATING%`)
   - Operating cash accounts that should remain constant
   - Example: Minimum operating cash balance

2. **LAND** (`%LAND%`)
   - Land value (should only change with purchase/sale)

3. **BUILDINGS** (`%BUILDINGS%`)
   - Building value (should only change with CapEx or sale)

4. **DEPOSITS** (`%DEPOSIT%`)
   - Security deposits, escrow deposits (should remain stable)

5. **LOAN-COSTS** (`%LOAN%COST%`)
   - Loan origination costs (should only change with refinance)

6. **PARTNERS-CONTRIBUTION** (`%PARTNER%CONTRIBUT%`)
   - Partner capital contributions (should remain stable)

7. **BEGINNING-EQUITY** (`%BEGINNING%EQUITY%`, `%RETAINED EARNINGS%`)
   - Beginning equity and retained earnings baseline

---

## 🔍 How AUDIT-28 Works

### **Step 1: Establish Baseline**
```python
baseline_period_id = self._get_earliest_period_id()
```
- Uses the **earliest available period** as the baseline
- This becomes the "reference point" for all future comparisons

### **Step 2: Compare Current Period**
For each of the 7 account categories:
```python
baseline_value = self._sum_bs_accounts(patterns, baseline_period_id)
current_value = self._sum_bs_accounts(patterns, current_period_id)
diff = current_value - baseline_value
```

### **Step 3: Calculate Tolerance**

The tolerance is **dynamic** and calculated as:
```python
tolerance = max(1.0, abs(baseline_value) * 0.001)
```

**Formula Breakdown:**
- **Minimum**: `$1.00` (absolute minimum tolerance)
- **Percentage**: `0.1%` of baseline value (0.001 = 0.1%)
- **Result**: Uses whichever is **larger**

**Examples:**
- Baseline = `$100,000` → Tolerance = `max($1.00, $100)` = **$100**
- Baseline = `$1,000,000` → Tolerance = `max($1.00, $1,000)` = **$1,000**
- Baseline = `$500` → Tolerance = `max($1.00, $0.50)` = **$1.00**

### **Step 4: Determine Status**

```python
if abs(baseline_value) <= 0.01 and abs(current_value) <= 0.01:
    status = "SKIP"  # Both values are essentially zero
else:
    status = "PASS" if abs(diff) <= tolerance else "WARNING"
```

**Status Logic:**
- **SKIP**: Both baseline and current are ≤ $0.01 (essentially zero)
- **PASS**: Difference ≤ tolerance (within acceptable range)
- **WARNING**: Difference > tolerance (outside tolerance)

---

## ⚠️ What Does "Outside Tolerance" Mean?

### **Definition:**
An account check is **"outside tolerance"** when:
```
|current_value - baseline_value| > tolerance
```

Where:
- `tolerance = max($1.00, baseline_value × 0.001)`

### **Example Scenarios:**

#### ✅ **Within Tolerance (PASS)**
- **Baseline**: $100,000
- **Current**: $100,050
- **Difference**: $50
- **Tolerance**: $100 (0.1% of $100,000)
- **Result**: ✅ **PASS** (|$50| ≤ $100)

#### ⚠️ **Outside Tolerance (WARNING)**
- **Baseline**: $100,000
- **Current**: $100,200
- **Difference**: $200
- **Tolerance**: $100 (0.1% of $100,000)
- **Result**: ⚠️ **WARNING** (|$200| > $100)

#### ⚠️ **Large Deviation (WARNING)**
- **Baseline**: $1,000,000
- **Current**: $1,002,000
- **Difference**: $2,000
- **Tolerance**: $1,000 (0.1% of $1,000,000)
- **Result**: ⚠️ **WARNING** (|$2,000| > $1,000)

---

## 📊 Summary Report

After checking all 7 account categories, AUDIT-28 generates a **summary result**:

```python
summary_status = "PASS" if failures == 0 else "WARNING"
details = f"{failures} constant account check(s) outside tolerance"
```

### **Summary Interpretation:**

| Failures | Status | Meaning |
|----------|--------|---------|
| **0** | ✅ PASS | All constant accounts within tolerance |
| **1-7** | ⚠️ WARNING | One or more accounts changed beyond tolerance |

**Example Message:**
- `"5 constant account check(s) outside tolerance"` means:
  - 5 out of 7 account categories had changes exceeding their tolerance
  - 2 categories passed (within tolerance)

---

## 🎛️ Editing Logic (Configuration)

### **What Can Be Edited?**

From the UI configuration screen, you can modify:

1. **Execution Formula**:
   - Default: `"All constant accounts should remain unchanged"`
   - **Warning**: Modifying the formula affects future evaluations only (not historical data)

2. **Variance Threshold (Absolute)**:
   - Default: `$0.01` (shown in UI)
   - **Note**: The actual tolerance calculation uses `max($1.00, baseline × 0.001)`
   - The UI threshold may be a display/configuration override

### **How Editing Works:**

```python
# The rule uses dynamic tolerance calculation:
tolerance = max(1.0, abs(baseline_value) * 0.001)

# But UI may allow configuration override:
# If configured threshold exists, use it instead
configured_threshold = get_config("AUDIT-28", "variance_threshold", default=0.01)
tolerance = max(configured_threshold, abs(baseline_value) * 0.001)
```

**Important**: 
- Changing the threshold affects **all future rule evaluations**
- Historical reconciliation results remain unchanged
- The formula change updates the rule's description/logic

---

## 🔧 Technical Implementation

### **Code Location:**
`backend/app/services/rules/audit_rules_mixin.py` (lines 2945-3049)

### **Key Methods:**
- `_rule_audit_28_constant_accounts_validation()` - Main rule execution
- `_get_earliest_period_id()` - Finds baseline period
- `_sum_bs_accounts(patterns, period_id)` - Sums matching accounts

### **Output Structure:**

**Individual Checks** (7 results):
```python
ReconciliationResult(
    rule_id="AUDIT-28-CASH-OPERATING",  # or LAND, BUILDINGS, etc.
    rule_name="Constant Account Validation (CASH-OPERATING)",
    status="PASS" | "WARNING" | "SKIP",
    source_value=current_value,
    target_value=baseline_value,
    difference=diff,
    tolerance=tolerance,
    details="Baseline $X (period Y) vs current $Z"
)
```

**Summary Result** (1 result):
```python
ReconciliationResult(
    rule_id="AUDIT-28",
    rule_name="Constant Accounts Summary",
    status="PASS" | "WARNING",
    source_value=failures,  # Count of failures (0-7)
    target_value=0.0,  # Expected failures
    difference=failures,  # Actual failures
    details="5 constant account check(s) outside tolerance"
)
```

---

## 📈 Business Value

### **Why This Rule Matters:**

1. **Fraud Detection**: Unauthorized changes to constant accounts
2. **Data Quality**: Catches data entry errors
3. **Accounting Integrity**: Ensures accounts remain stable as expected
4. **Audit Trail**: Provides clear documentation of changes

### **Common Scenarios:**

| Scenario | Expected Behavior | AUDIT-28 Result |
|----------|------------------|-----------------|
| **Normal Operations** | Accounts remain stable | ✅ PASS |
| **Data Entry Error** | Account accidentally changed | ⚠️ WARNING |
| **Unauthorized Change** | Account modified without documentation | ⚠️ WARNING |
| **Property Sale** | Land/Building accounts change | ⚠️ WARNING (expected, needs review) |
| **Refinance** | Loan costs change | ⚠️ WARNING (expected, needs review) |

---

## 🎯 Summary

### **AUDIT-28 Explained:**

1. **What**: Validates that 7 types of "constant" balance sheet accounts remain unchanged
2. **Baseline**: Uses earliest available period as reference
3. **Tolerance**: Dynamic (`max($1.00, 0.1% of baseline)`)
4. **Status**: PASS (within tolerance) or WARNING (outside tolerance)
5. **Summary**: Reports count of accounts outside tolerance

### **"Outside Tolerance" Means:**
- Change exceeds the calculated tolerance threshold
- Tolerance = `max($1.00, baseline_value × 0.001)`
- Example: $100,000 baseline → $100 tolerance → change > $100 = outside tolerance

### **"5 constant account check(s) outside tolerance":**
- 5 out of 7 account categories had changes exceeding their tolerance
- 2 categories passed validation
- Requires investigation to determine if changes are legitimate

---

**For questions or issues with AUDIT-28, refer to:**
- Implementation: `backend/app/services/rules/audit_rules_mixin.py`
- Rule Mapping: `backend/app/services/rules/RULES_MAPPING.md`
- Reconciliation Analysis: `RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md`
