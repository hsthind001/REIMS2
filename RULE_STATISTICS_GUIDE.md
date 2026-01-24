# Rule Statistics Guide

## Quick Answer

**Where to find rule statistics:**
Go to **Financial Integrity Hub** → **By Rule tab** → Statistics cards at the top

## What You'll See

### Statistics Dashboard (4 Cards)

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Total Rules │   Passed    │  Variance   │  Pass Rate  │
│     📊      │     ✅      │     ⚠️      │     📈      │
│      7      │      4      │      3      │     57%     │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### Card Details

#### 1. Total Rules (Blue)
- **Shows:** Total number of rules evaluated
- **Icon:** Calculator 📊
- **Color:** Blue gradient
- **Example:** 7 rules

#### 2. Passed (Green)
- **Shows:** Number of rules that passed validation
- **Icon:** Checkmark ✅
- **Color:** Green gradient
- **Status:** These rules met their expected values within tolerance
- **Example:** 4 passed

#### 3. Variance (Amber)
- **Shows:** Number of rules with variance/discrepancies
- **Icon:** Warning Triangle ⚠️
- **Color:** Amber gradient
- **Status:** These rules exceeded their tolerance threshold
- **Example:** 3 with variance

#### 4. Pass Rate (Purple)
- **Shows:** Percentage of rules that passed
- **Icon:** Checkmark 📈
- **Color:** Purple gradient
- **Calculation:** (Passed / Total) × 100
- **Example:** 57% (4 out of 7)

## Navigation Path

```
Financial Integrity Hub
  http://localhost:5173/#forensic-reconciliation
    ↓
  1. Select Property (dropdown)
  2. Select Period (dropdown)
  3. Click "Run Reconciliation" button
  4. Click "Validate" button
  5. Click "By Rule" tab
    ↓
  📊 Statistics Cards Display Here
    ↓
  (Below: List of individual rules)
```

## Real Example (From Your Screenshot)

Based on the visible rules:

### Passed Rules (4) ✅
1. **Accounting Equation BS-1**
   - Expected: 23976748.54 | Actual: 23976748.54
   - Formula: `Total Assets - (Total Liabilities & Capital)`

2. **Cash Operating Check BS-2**
   - Expected: 3375.45 | Actual: 3375.45
   - Formula: `[0122-0000] Cash Operating - 3375.45`

3. **Land Asset Verification BS-6**
   - Expected: 0 | Actual: 3100438.76
   - Formula: `[0510-0000] Land > 0`

4. **Current Assets Integrity BS-3**
   - Expected: 628295.98 | Actual: 628295.98
   - Formula: `Total Current Assets > 0`

### Variance Rules (3) ⚠️
1. **Current Ratio Liquidity BS-4**
   - Expected: 1 | Actual: 0.27
   - Formula: `Total Current Assets / Total Current Liabilities >= 1.0`

2. **Working Capital Positive BS-5**
   - Expected: 0 | Actual: -1741748.87
   - Formula: `Total Current Assets - Total Current Liabilities > 0`

3. **Debt to Assets Ratio BS-9**
   - Expected: 0.85 | Actual: 0.98
   - Formula: `Debt/Assets Ratio is 0.98 (Target <= 0.85)`

### Summary Statistics
- **Total:** 7 rules
- **Passed:** 4 rules (57%)
- **Variance:** 3 rules (43%)
- **Pass Rate:** 57%

## Understanding the Colors

### 🟢 Green (Passed)
- Rule validation successful
- Actual value matches expected value (within tolerance)
- No action needed
- Example: Accounting Equation balanced

### 🟡 Amber (Variance)
- Rule validation found discrepancy
- Actual value differs from expected
- Requires review or action
- Example: Current Ratio below target

## What Pass Rate Means

### High Pass Rate (90%+)
- ✅ Excellent financial integrity
- ✅ Most validations passing
- ✅ Low risk

### Medium Pass Rate (70-89%)
- ⚠️ Some concerns
- ⚠️ Several rules failing
- ⚠️ Medium risk

### Low Pass Rate (<70%)
- 🚨 Significant issues
- 🚨 Many rules failing
- 🚨 High risk
- Action required

## How Statistics Update

### Automatic Updates
Statistics refresh when you:
1. Run Reconciliation
2. Validate Session
3. Change Property/Period
4. Modify Rule Thresholds

### Manual Refresh
If statistics seem stale:
1. Click "Validate" button again
2. Or refresh the browser page

## Using Statistics for Decision Making

### Daily Monitoring
- Check pass rate daily
- Target: 90%+ pass rate
- Investigate if below 80%

### Trend Analysis
- Compare pass rates over time
- Identify declining trends
- Proactive issue detection

### Priority Setting
- Focus on variance rules first
- High-variance items = high priority
- Passed rules = low priority

## Common Questions

### Q: Why do I see 0 rules?
**A:** You need to:
1. Select property and period
2. Run Reconciliation
3. Click Validate
4. Rules will appear after validation

### Q: Why is my pass rate low?
**A:** Common reasons:
- Incorrect rule thresholds
- Data entry errors
- Missing documents
- Period-specific issues
- Rule configuration needs adjustment

### Q: Can I filter by passed/variance?
**A:** Currently showing all rules. Future enhancement: filter buttons.

### Q: How often should I validate?
**A:** Recommended:
- After uploading new documents
- After data changes
- Daily for active properties
- Before month-end close

### Q: What's a good target pass rate?
**A:** Targets by property type:
- Commercial: 95%+
- Residential: 90%+
- Mixed-use: 92%+

## Location in UI

```
┌────────────────────────────────────────────────────┐
│  Financial Integrity Hub                           │
│  ┌─────────┬─────────┬─────────┬─────────┬───────┐│
│  │Overview │Document │By Rule  │Exception│Insight││
│  └─────────┴─────────┴────▼────┴─────────┴───────┘│
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │  📊 Statistics Cards (NEW!)                  │ │
│  │  ┌───────┬───────┬───────┬───────┐          │ │
│  │  │ Total │Passed │Varia- │Pass   │          │ │
│  │  │   7   │   4   │nce 3  │Rate   │          │ │
│  │  │       │       │       │57%    │          │ │
│  │  └───────┴───────┴───────┴───────┘          │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  🔍 Search rules...                               │
│                                                    │
│  📋 Rules List                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │ ✅ Accounting Equation BS-1         Passed   │ │
│  ├──────────────────────────────────────────────┤ │
│  │ ✅ Cash Operating Check BS-2        Passed   │ │
│  ├──────────────────────────────────────────────┤ │
│  │ ⚠️  Current Ratio Liquidity BS-4   Variance │ │
│  └──────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

## Visual Design

### Card Layout
- Responsive grid (4 columns on desktop, stacks on mobile)
- Gradient backgrounds with matching border colors
- Large numbers (3xl font) for quick scanning
- Icons in rounded containers
- Hover effects (future enhancement)

### Color Scheme
- **Blue:** Informational (Total)
- **Green:** Success (Passed)
- **Amber:** Warning (Variance)
- **Purple:** Analysis (Pass Rate)

## Technical Details

### Data Source
- Live data from `useForensicCalculatedRules` hook
- Filtered by selected property and period
- Updated after validation runs

### Calculation Logic
```typescript
const stats = {
  total: rules.length,
  passed: rules.filter(r => r.status === 'PASS').length,
  variance: rules.filter(r => r.status !== 'PASS').length,
  passRate: Math.round((passedCount / total) * 100)
};
```

### Performance
- Calculated in real-time (no API call)
- Instant updates
- No performance impact
- Cached by React Query

## Future Enhancements

### Planned Features
- [ ] Click card to filter rules
- [ ] Historical trend charts
- [ ] Export statistics to CSV
- [ ] Email alerts for low pass rates
- [ ] Comparison with previous periods
- [ ] Rule category breakdown
- [ ] Severity-based grouping

### Requested By Users
- [ ] Custom pass rate targets
- [ ] Rule importance weighting
- [ ] Multi-property comparison
- [ ] Automated reporting

## Benefits

### Before This Feature
- ❌ Had to manually count rules
- ❌ No quick visibility
- ❌ Time-consuming analysis
- ❌ Easy to miss issues

### After This Feature
- ✅ Instant statistics
- ✅ Clear visual summary
- ✅ Quick health check
- ✅ Easy decision making
- ✅ Better monitoring

## Testing

### Verify Statistics Work
1. Navigate to Financial Integrity Hub
2. Select property and period
3. Run Reconciliation → Validate
4. Go to "By Rule" tab
5. **Verify:** Statistics cards appear at top
6. **Verify:** Numbers match rule list below
7. **Verify:** Pass rate calculation correct

### Test Scenarios

**Scenario 1: All Rules Pass**
- Total: 10
- Passed: 10
- Variance: 0
- Pass Rate: 100%
- **All cards should be green/positive**

**Scenario 2: Mixed Results**
- Total: 10
- Passed: 7
- Variance: 3
- Pass Rate: 70%
- **Amber variance card should stand out**

**Scenario 3: All Rules Fail**
- Total: 10
- Passed: 0
- Variance: 10
- Pass Rate: 0%
- **Red alert needed (future enhancement)**

## Commit Information

**Commit:** 896f6ad
**Feature:** Rule Statistics Summary
**Files Modified:** 
- `src/components/financial_integrity/tabs/ByRuleTab.tsx`

**Status:** ✅ Complete and Committed

## Support

If statistics don't appear:
1. Verify you've selected property/period
2. Run Reconciliation button
3. Click Validate button
4. Refresh browser if needed
5. Check console for errors

---

*Last Updated: January 24, 2026*
*Feature: Rule Statistics Dashboard*
*Status: Production Ready ✅*
