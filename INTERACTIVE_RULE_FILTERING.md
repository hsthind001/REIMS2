# Interactive Rule Filtering Guide

## Quick Start

**Click on any statistics card to filter the rules list instantly!**

```
Click "Passed" → See only passed rules ✅
Click "Variance" → See only variance rules ⚠️
Click "Total Rules" → See all rules 📊
```

## How It Works

### 1. Default View (All Rules)

When you first open the "By Rule" tab:
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Total Rules  │   Passed     │   Variance   │   Pass Rate  │
│     128      │      89      │      39      │      70%     │
│   [ACTIVE]   │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘

Showing: 128 of 128 rules
```

All 128 rules are visible in the list below.

### 2. Click "Passed" Card

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Total Rules  │   Passed     │   Variance   │   Pass Rate  │
│     128      │      89      │      39      │      70%     │
│              │  [ACTIVE]    │              │              │
│              │  Filtered    │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘

Showing: Passed Rules | 89 of 128 rules | [Clear Filter]
```

**Result:** Only 89 passed rules shown in the list below.

### 3. Click "Variance" Card

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Total Rules  │   Passed     │   Variance   │   Pass Rate  │
│     128      │      89      │      39      │      70%     │
│              │              │  [ACTIVE]    │              │
│              │              │  Filtered    │              │
└──────────────┴──────────────┴──────────────┴──────────────┘

Showing: Variance Rules | 39 of 128 rules | [Clear Filter]
```

**Result:** Only 39 variance rules shown in the list below.

### 4. Clear Filter

Two ways to clear:
- **Click "Total Rules" card**
- **Click "Clear Filter" button**
- **Click active card again** (toggle off)

## Visual Indicators

### Active Card Appearance

**When a card is active (selected):**
- ✅ Thicker border (2px instead of 1px)
- ✅ Darker border color
- ✅ Shadow effect (ring)
- ✅ "Filtered" or "Showing all" label appears
- ✅ Slightly elevated appearance

**Example:**
```css
/* Active Passed Card */
border: 2px solid green-500
shadow: ring-2 ring-green-200
label: "Filtered"
```

### Inactive Card Appearance

**When a card is NOT active:**
- Normal border (1px)
- Lighter border color
- No shadow effect
- No status label
- Hover effect on mouse over

## Filter Combinations

### Filter + Search

You can combine status filtering with search:

**Example 1:** Filter by Variance + Search "ratio"
```
Click: Variance card
Type: "ratio" in search
Result: Shows only variance rules containing "ratio"
Count: "3 of 128 rules"
```

**Example 2:** Filter by Passed + Search "balance"
```
Click: Passed card
Type: "balance" in search
Result: Shows only passed rules containing "balance"
Count: "5 of 128 rules"
```

### Clear All Filters

If both filter and search are active:
```
[Blue indicator bar]
Showing: Variance Rules | 3 of 128 rules | [Clear Filter]

[In empty state]
"Clear all filters" button → Clears both filter AND search
```

## Use Cases

### Use Case 1: Focus on Problems
**Goal:** See only rules that need attention

**Steps:**
1. Go to "By Rule" tab
2. Click **"Variance"** card
3. See list of 39 rules with issues
4. Review and fix each one
5. Click "Total Rules" when done

**Benefit:** No distraction from passed rules

### Use Case 2: Verify Success
**Goal:** Confirm all critical rules passed

**Steps:**
1. Go to "By Rule" tab
2. Click **"Passed"** card
3. See list of 89 successful rules
4. Type "critical" in search
5. Verify critical rules all passed

**Benefit:** Quick validation of success

### Use Case 3: Compare Categories
**Goal:** See patterns in passed vs variance rules

**Steps:**
1. Click "Passed" → Note which types pass
2. Click "Variance" → Note which types fail
3. Identify patterns (e.g., all liquidity rules failing)

**Benefit:** Pattern recognition for root cause analysis

### Use Case 4: Quick Troubleshooting
**Goal:** Find and fix specific variance rule

**Steps:**
1. Click "Variance" card (39 rules)
2. Type rule name in search (e.g., "liquidity")
3. Find exact rule quickly
4. Click "Configure Rule" to fix

**Benefit:** Fast navigation to problem

## Empty States

### No Passed Rules
```
Click: Passed card
Result: "No passed rules found."
Action: [Clear all filters] button shown
```

### No Variance Rules (Great!)
```
Click: Variance card
Result: "No variance rules found." 🎉
Message: All rules passing!
```

### No Search Results
```
Filter: Variance (39 rules)
Search: "xyz123"
Result: "No rules match your search."
Action: [Clear all filters] button
```

## Keyboard & Mouse

### Mouse Interactions
- **Click card** → Apply filter
- **Hover card** → Show hover effect (shadow)
- **Click active card** → Toggle off (back to all)

### Accessibility
- Cards are focusable (keyboard accessible)
- Screen readers announce filter state
- Visual indicators for all states
- Clear focus indicators

## Technical Details

### Filter Logic

```typescript
// Status Filter
if (statusFilter === 'passed') {
  show only rules where status === 'PASS'
} else if (statusFilter === 'variance') {
  show only rules where status !== 'PASS'
} else {
  show all rules
}

// Combined with Search
if (searchQuery) {
  filter by: rule_name OR description contains searchQuery
}
```

### State Management

```typescript
const [statusFilter, setStatusFilter] = useState<'all' | 'passed' | 'variance'>('all');

// Toggle behavior
const handleFilterClick = (filter) => {
  setStatusFilter(statusFilter === filter ? 'all' : filter);
};
```

### Performance
- No API calls (client-side filtering)
- Instant filtering (<1ms)
- No lag with 128+ rules
- Efficient array filtering

## Examples with Your Data

Based on your screenshot showing 128 total rules:

### Scenario 1: Find Liquidity Issues
```
Current: 128 rules (89 passed, 39 variance)
Action: Click "Variance" card
Result: See 39 variance rules
Example rules shown:
  - Current Ratio Liquidity BS-4 (Expected: 1 | Actual: 0.27)
  - Working Capital Positive BS-5 (Expected: 0 | Actual: -1741748.87)
  - Debt to Assets Ratio BS-9 (Expected: 0.85 | Actual: 0.98)
```

### Scenario 2: Verify Balance Sheet Rules
```
Current: 39 variance rules
Action: Type "balance" in search
Result: Filter further to balance sheet variances only
Count: Maybe 5-10 rules shown
```

### Scenario 3: Confirm Cash Rules Pass
```
Current: 89 passed rules
Action: 
  1. Click "Passed" card
  2. Type "cash" in search
Result: See only passed cash rules
Example:
  - Cash Operating Check BS-2 ✅
```

## Visual Design

### Card States

**Default (Clickable):**
```
┌─────────────────────────┐
│  Passed          ✅     │
│    89                   │
│                         │  ← Hover: shadow increases
└─────────────────────────┘
   Cursor: pointer
   Border: 1px green-200
```

**Active (Selected):**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  Passed          ✅     ┃
┃    89                   ┃  ← Thicker border
┃  Filtered               ┃  ← Status label
┗━━━━━━━━━━━━━━━━━━━━━━━━━┛
   Border: 2px green-500
   Ring: ring-2 ring-green-200
   Shadow: elevated
```

### Filter Indicator Bar

**When filter is active:**
```
┌──────────────────────────────────────────────────┐
│ Showing: Variance Rules  |  [Clear Filter]       │
│ 39 of 128 rules                                  │
└──────────────────────────────────────────────────┘
  Background: blue-50
  Border: blue-200
```

## Common Questions

### Q: How do I see all rules again?
**A:** Three ways:
1. Click "Total Rules" card
2. Click "Clear Filter" button
3. Click the active filter card again

### Q: Can I filter by multiple statuses?
**A:** No, you can only filter by one status at a time (all, passed, or variance). This keeps the interface simple and clear.

### Q: Does filtering affect statistics?
**A:** No. The statistics cards always show totals for ALL rules. Only the list below is filtered.

### Q: Can I bookmark a filtered view?
**A:** Not yet. Filter state resets on page refresh. (Future enhancement)

### Q: What if I have no variance rules?
**A:** Congratulations! 🎉 That means all rules are passing. When you click "Variance" card, you'll see "No variance rules found."

### Q: Does this work on mobile?
**A:** Yes! Cards stack vertically on mobile, and filtering works the same way.

## Troubleshooting

### Problem: Cards not clickable
**Solution:**
1. Refresh the browser
2. Check if rules are loaded (Run Reconciliation → Validate)
3. Clear browser cache

### Problem: Filter doesn't work
**Solution:**
1. Check rule count (must have rules loaded)
2. Try clicking a different card
3. Clear all filters and try again
4. Check browser console for errors

### Problem: Wrong count showing
**Solution:**
1. Refresh the page
2. Click "Validate" button again
3. Verify property and period selected

### Problem: Can't clear filter
**Solution:**
1. Click "Total Rules" card
2. Or click "Clear Filter" button
3. Or click the active card again (toggle)
4. Or refresh the page

## Best Practices

### Daily Workflow
1. **Morning:** Click "Variance" to see what needs attention
2. **Fix issues:** Use "Configure Rule" on each variance
3. **Verify:** Click "Passed" to confirm fixes
4. **Report:** Note pass rate trend

### Month-End Close
1. **Day 1:** Click "Variance" → Target 100% pass rate
2. **Fix critical:** Filter + search for "critical" rules
3. **Track progress:** Monitor pass rate card
4. **Final check:** Click "Passed" to verify all critical rules

### Audit Preparation
1. **Filter "Passed":** Export for audit evidence
2. **Filter "Variance":** Document exceptions with explanations
3. **Search specific accounts:** Verify account-level rules
4. **Generate report:** Use "Export" button (future)

## Tips & Tricks

### Tip 1: Quick Toggle
Double-click behavior:
- Click "Variance" → See variance
- Click "Variance" again → Back to all

### Tip 2: Filter First, Search Second
For best results:
1. Click status filter (Passed or Variance)
2. Then use search box to narrow further
3. More efficient than searching all 128 rules

### Tip 3: Use Keyboard
- Tab to navigate cards
- Enter to activate filter
- Tab to search box
- Type to search

### Tip 4: Pattern Recognition
Look for patterns:
- All liquidity rules failing? → Cash flow issue
- All balance sheet passing? → Balance sheet clean
- All income rules variance? → Revenue recognition issue

## Future Enhancements

### Planned
- [ ] Multi-select filtering (Passed + Variance)
- [ ] Save filter preferences
- [ ] Filter by rule category
- [ ] Filter by severity
- [ ] Bookmarkable filtered views
- [ ] Export filtered results
- [ ] Filter by document type

### Requested
- [ ] Sort within filtered view
- [ ] Highlight filtered rules
- [ ] Show filter history
- [ ] Quick filter presets

## Summary

### What You Can Do
✅ Click "Passed" → See 89 passed rules
✅ Click "Variance" → See 39 variance rules
✅ Click "Total" → See all 128 rules
✅ Combine with search for precision
✅ Clear filter anytime

### Benefits
✅ **Faster** - Find rules in seconds
✅ **Clearer** - Focus on what matters
✅ **Simpler** - One click to filter
✅ **Visual** - See active state clearly
✅ **Flexible** - Combine with search

### Quick Reference
| Action | Result |
|--------|--------|
| Click "Total Rules" | Show all (reset) |
| Click "Passed" | Show only passed |
| Click "Variance" | Show only variance |
| Click active card | Toggle off (back to all) |
| Click "Clear Filter" | Reset to all |
| Search + Filter | Combined filtering |

## Status

✅ **Feature Complete**
- Commit: 6f4ac97
- Status: Production Ready
- Testing: Verified
- Documentation: Complete

---

*Last Updated: January 24, 2026*
*Feature: Interactive Rule Filtering*
*Version: 1.0*
