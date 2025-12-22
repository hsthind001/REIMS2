# Why Detection Confidence is Not Always 100%

## Previous Issue
Previously, **all anomalies had a fixed 85% confidence**, regardless of:
- How large the deviation was (783% vs 15%)
- How many historical data points were available
- The statistical significance of the anomaly

This didn't make sense because:
- A **783% deviation** should have **higher confidence** than an 85% fixed value
- A **15% deviation** should have **lower confidence** than a massive deviation
- More historical data should increase confidence

---

## New Dynamic Confidence Calculation

Confidence is now calculated dynamically based on multiple factors:

### Base Confidence: 70%
Starting point for all anomalies

### Factor 1: Deviation Magnitude (Percentage Change)
**Larger deviations = Higher confidence**

| Percentage Change | Confidence Bonus | Reasoning |
|-------------------|------------------|-----------|
| **100%+ change** | +25% | Extremely large deviations are very unlikely to be false positives |
| **50-100% change** | +15% | Large deviations indicate genuine anomalies |
| **25-50% change** | +10% | Moderate deviations |
| **15-25% change** | +5% | Small deviations (just above threshold) |

**Example:**
- 783% change → Base (70%) + Large deviation bonus (25%) = **95% confidence**
- 18% change → Base (70%) + Small deviation bonus (5%) = **75% confidence**

### Factor 2: Z-Score (Statistical Significance)
**Higher Z-score = Higher confidence** (only if 2+ historical periods available)

| Z-Score | Confidence Bonus | Reasoning |
|---------|------------------|-----------|
| **|Z| ≥ 4.0** | +10% | Extremely statistically significant |
| **|Z| ≥ 3.0** | +5% | Highly statistically significant |
| **|Z| ≥ 2.0** | +2% | Moderately statistically significant |

### Factor 3: Historical Data Points
**More historical periods = More reliable baseline**

| Historical Periods | Confidence Bonus | Reasoning |
|---------------------|------------------|-----------|
| **5+ periods** | +5% | Very reliable baseline |
| **3-4 periods** | +3% | Good baseline |
| **2 periods** | +1% | Acceptable baseline |
| **1 period** | +0% | Limited baseline (less reliable) |

### Factor 4: Severity Level
**Critical anomalies = Higher confidence**

| Severity | Confidence Bonus | Reasoning |
|----------|------------------|-----------|
| **Critical** | +3% | Critical anomalies are more certain |
| **High** | +2% | High severity anomalies |
| **Medium** | +0% | Medium severity (baseline) |

---

## Example Calculations

### Example 1: Large Deviation (783% change)
```
Base: 70%
+ Large deviation (783% > 100%): +25%
+ Critical severity: +3%
+ 1 historical period: +0%
= 98% confidence ✅
```

### Example 2: Very Large Deviation (1088% change)
```
Base: 70%
+ Very large deviation (1088% > 100%): +25%
+ Critical severity: +3%
+ 1 historical period: +0%
= 98% confidence ✅
```

### Example 3: Medium Deviation with Multiple Periods
```
Base: 70%
+ Medium deviation (25.5%): +10%
+ High severity: +2%
+ Z-score 2.5: +5%
+ 5 historical periods: +5%
= 92% confidence ✅
```

### Example 4: Small Deviation
```
Base: 70%
+ Small deviation (18%): +5%
+ Medium severity: +0%
+ 1 historical period: +0%
= 75% confidence ✅
```

---

## Why Not 100%?

Even with very large deviations, confidence is capped at **98-99%** (not 100%) because:

1. **Data Quality Uncertainty**: 
   - Historical data might have errors
   - Account code matching might be incorrect
   - Extraction errors could affect both current and historical values

2. **Business Context Unknown**:
   - Large changes might be legitimate (e.g., property expansion, new tenants)
   - System doesn't know business context or planned changes
   - Requires human review to confirm if anomaly is genuine issue

3. **Statistical Limitations**:
   - Limited historical data (most properties only have 1-2 periods)
   - No seasonality adjustment
   - No account code change handling

4. **False Positive Risk**:
   - Even 98% confidence leaves 2% chance of false positive
   - This is appropriate for financial anomaly detection
   - Human review is still recommended for critical anomalies

---

## Confidence Ranges

| Confidence | Meaning | Action Required |
|------------|---------|-----------------|
| **95-100%** | Very high confidence - almost certainly an anomaly | Immediate review recommended |
| **85-94%** | High confidence - likely an anomaly | Review recommended |
| **75-84%** | Moderate confidence - possible anomaly | Review if time permits |
| **< 75%** | Low confidence - may be false positive | Review with caution |

---

## Summary

**Before:** All anomalies = 85% confidence (fixed)  
**After:** Confidence = 70% base + dynamic bonuses based on:
- Deviation magnitude (larger = higher confidence)
- Statistical significance (Z-score)
- Historical data quality (more periods = higher confidence)
- Severity level (critical = higher confidence)

**Result:** Large deviations (like 783%) now show **98% confidence** instead of fixed 85%, which makes much more sense!

