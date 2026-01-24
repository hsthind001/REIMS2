# Syntax Guide - Quick Usage Guide

## How to Access

### Method 1: From Rule Edit Page
```
1. Navigate to any rule edit page
   URL: http://localhost:5173/#rule-edit/BS-1

2. Scroll to "Execution Formula" section

3. Click "Syntax Guide" link (top right, next to field label)

4. Modal opens with comprehensive guide
```

### Method 2: From Edit Rule Modal
```
1. Open EditRuleModal (if used elsewhere in app)

2. Find "Execution Formula" section

3. Click "Syntax Guide" link

4. Same modal opens
```

## What You'll See

### Section 1: Basic Syntax
Learn the fundamental structure of formulas:
```
Account Name [Operator] Account Name
```

**Example:** `Total Assets - Total Liabilities`

### Section 2: Available Operators
5 mathematical operators explained with examples:

| Operator | Usage |
|----------|-------|
| + | Addition |
| - | Subtraction |
| * | Multiplication |
| / | Division |
| () | Grouping |

### Section 3: Formula Examples (6 Examples)

Each example includes:
- **Title** - What the formula does
- **Description** - When to use it
- **Formula** - The actual code
- **Copy Button** - One-click copy to clipboard

**Examples Provided:**
1. Basic Arithmetic
2. Accounting Equation
3. Percentage Calculation
4. Ratio Calculation
5. Multi-Line Items
6. Nested Operations

**Copy Feature:**
Click the copy icon → Formula copied → Paste into your formula field

### Section 4: Best Practices
6 golden rules for writing formulas:
- ✅ Use exact account names
- ✅ Use parentheses for clarity
- ✅ Account names are case-sensitive
- ✅ Preserve spaces exactly
- ✅ Match chart of accounts
- ✅ Test before deploying

### Section 5: Common Errors
4 common mistakes and how to fix them:
- ⚠️ Division by zero
- ⚠️ Account name not found
- ⚠️ Missing parentheses
- ⚠️ Syntax errors

Each error includes a solution.

### Section 6: Account Reference Guide
12+ common account names you can use:
- Total Assets
- Total Liabilities
- Total Equity
- Total Revenue
- Total Expenses
- Net Income
- Current Assets
- Current Liabilities
- Cash
- Accounts Receivable
- Accounts Payable
- Operating Expenses

**Note:** Your specific account names may differ. Check your Chart of Accounts.

### Section 7: Order of Operations (PEMDAS)
Mathematical precedence rules:
1. **Parentheses** - First
2. **Multiplication & Division** - Left to right
3. **Addition & Subtraction** - Left to right

**Example:**
```
A + B * C  →  evaluates as  →  A + (B * C)
```

## Quick Examples

### Copy & Use These Formulas

**Balance Sheet Validation:**
```
Total Assets - (Total Liabilities + Total Equity)
```

**Profit Margin:**
```
(Net Income / Total Revenue) * 100
```

**Current Ratio:**
```
Current Assets / Current Liabilities
```

**Working Capital:**
```
Current Assets - Current Liabilities
```

**Debt-to-Equity:**
```
Total Liabilities / Total Equity
```

## Tips & Tricks

### Tip 1: Use Parentheses Liberally
```
✅ Good: (Revenue - Expenses) / Revenue
❌ Bad:  Revenue - Expenses / Revenue
```

### Tip 2: Match Account Names Exactly
```
✅ Correct: Total Assets
❌ Wrong:   total assets (wrong case)
❌ Wrong:   TotalAssets (missing space)
```

### Tip 3: Test with Known Values
Before deploying a formula:
1. Check with actual financial data
2. Verify the result makes sense
3. Ensure no division by zero
4. Confirm all accounts exist

### Tip 4: Start Simple, Then Expand
```
Step 1: A - B
Step 2: A - (B + C)
Step 3: (A - B) / A * 100
```

### Tip 5: Document Your Formulas
Use the description field to explain:
- What the formula validates
- Why it's important
- What constitutes a pass/fail

## Common Use Cases

### 1. Balance Sheet Validation
**Purpose:** Ensure accounting equation balances

**Formula:**
```
Total Assets - (Total Liabilities + Total Equity)
```

**Expected Result:** 0 (or within threshold)

### 2. Income Statement Check
**Purpose:** Verify net income calculation

**Formula:**
```
Total Revenue - Total Expenses - Net Income
```

**Expected Result:** 0 (or within threshold)

### 3. Cash Flow Verification
**Purpose:** Ensure cash flow statement balances

**Formula:**
```
Beginning Cash + Operating Activities + Investing Activities + Financing Activities - Ending Cash
```

**Expected Result:** 0 (or within threshold)

### 4. Ratio Analysis
**Purpose:** Calculate financial ratios

**Formula:**
```
Current Assets / Current Liabilities
```

**Expected Result:** > 1.0 (healthy liquidity)

### 5. Percentage Calculations
**Purpose:** Calculate margins or rates

**Formula:**
```
(Net Income / Total Revenue) * 100
```

**Expected Result:** Positive percentage

## Troubleshooting

### Problem: "Account not found" error
**Solution:**
1. Go to Chart of Accounts
2. Find exact account name (case-sensitive)
3. Copy account name exactly
4. Paste into formula

### Problem: Formula gives unexpected results
**Solution:**
1. Check order of operations
2. Add parentheses for clarity
3. Test with known values
4. Verify all accounts exist for the period

### Problem: Can't copy example formula
**Solution:**
1. Click the copy icon on the right side of formula
2. If that doesn't work, manually select and copy
3. Paste into formula field

### Problem: Modal won't close
**Solution:**
1. Click "Got it" button
2. Click outside modal (on backdrop)
3. If stuck, refresh page

## Quick Reference Card

```
┌─────────────────────────────────────────┐
│         FORMULA QUICK REFERENCE         │
├─────────────────────────────────────────┤
│                                         │
│  Operators:  + - * / ()                │
│                                         │
│  Structure:  Account [op] Account      │
│                                         │
│  Example:    Total Assets - Total Liab │
│                                         │
│  Remember:                              │
│  ✓ Exact account names                 │
│  ✓ Case sensitive                      │
│  ✓ Use parentheses                     │
│  ✓ Test before deploy                  │
│                                         │
└─────────────────────────────────────────┘
```

## Visual Layout Preview

```
╔════════════════════════════════════════════════════╗
║  📊 Formula Syntax Guide                           ║
║  Learn how to write powerful validation rules      ║
╠════════════════════════════════════════════════════╣
║                                                    ║
║  [1] Basic Syntax                                  ║
║  ├─ Explanation                                    ║
║  └─ Examples                                       ║
║                                                    ║
║  [2] Available Operators                           ║
║  ├─ + Addition                                     ║
║  ├─ - Subtraction                                  ║
║  ├─ * Multiplication                               ║
║  ├─ / Division                                     ║
║  └─ () Parentheses                                 ║
║                                                    ║
║  [3] Formula Examples                              ║
║  ├─ Basic Arithmetic          [Copy]               ║
║  ├─ Accounting Equation       [Copy]               ║
║  ├─ Percentage Calculation    [Copy]               ║
║  ├─ Ratio Calculation         [Copy]               ║
║  ├─ Multi-Line Items          [Copy]               ║
║  └─ Nested Operations         [Copy]               ║
║                                                    ║
║  [✓] Best Practices                                ║
║  ├─ 6 guidelines                                   ║
║                                                    ║
║  [!] Common Errors                                 ║
║  ├─ 4 common mistakes + solutions                  ║
║                                                    ║
║  [4] Account Reference Guide                       ║
║  ├─ 12+ common account names                       ║
║                                                    ║
║  [5] Order of Operations (PEMDAS)                  ║
║  └─ Mathematical precedence rules                  ║
║                                                    ║
╠════════════════════════════════════════════════════╣
║  Need help? Contact finance team    [Got it]       ║
╚════════════════════════════════════════════════════╝
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open Guide | Click "Syntax Guide" link |
| Close Guide | Click "Got it" or click outside |
| Navigate | Tab / Shift+Tab |
| Activate | Enter |
| Scroll | Arrow keys or mouse wheel |

## Mobile Experience

On mobile devices:
- Modal takes full screen
- Scrollable content
- Touch-friendly buttons
- Responsive grid layout
- Easy to read and interact

## Support

For questions or additional formula examples:
1. Check this guide first
2. Review the examples section
3. Try the best practices
4. Contact finance team if needed

## Status

✅ **Implementation Complete and Committed**

- Commit: 300acfd
- Files: 5 modified/created
- Status: Ready for use
- Persistence: ✅ Yes (committed to git)
