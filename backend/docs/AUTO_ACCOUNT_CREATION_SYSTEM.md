# Auto-Account Creation System Documentation

## Overview

The auto-account creation system makes REIMS2 intelligent and self-maintaining by automatically creating missing chart of accounts entries when encountered during PDF extraction. This prevents extraction failures due to missing accounts and ensures the system can handle new accounts without manual intervention.

## Features

### 1. Intelligent Account Type Inference
The system analyzes account names using pattern matching to determine the correct account type and category:

- **Assets**: Cash, receivables, prepaid expenses, land, buildings, equipment
- **Liabilities**: Payables, accrued expenses, mortgages, loans
- **Equity**: Owner's equity, capital contributions, retained earnings
- **Income**: Rental income, reimbursements, revenue
- **Expenses**: Maintenance, utilities, insurance, property taxes

### 2. Automatic Account Code Generation
When an account code is missing or "UNMATCHED", the system generates sequential codes:

- Assets: `0xxx-0000` (e.g., `0900-0000`)
- Liabilities: `2xxx-0000` (e.g., `2900-0000`)
- Equity: `3xxx-0000` (e.g., `3900-0000`)
- Income: `4xxx-0000` (e.g., `4900-0000`)
- Expenses: `5xxx-0000` (e.g., `5900-0000`)
- Unknown: `9xxx-0000` (fallback)

### 3. Review Flagging
All auto-created accounts are flagged with `needs_review = True` so users can verify the inference was correct.

### 4. Context-Aware Inference
The system uses document type context:
- Balance sheet accounts → defaults to assets
- Income statement accounts → defaults to expenses

## Implementation

### Core Methods

#### `_auto_create_account(account_name, account_code, document_type)`
**Location**: `app/services/extraction_orchestrator.py:2425`

Main entry point for auto-account creation.

**Parameters**:
- `account_name` (str, required): Name of the account from PDF
- `account_code` (str, optional): Account code from PDF (auto-generated if None)
- `document_type` (str, optional): Type of document (balance_sheet, income_statement, etc.)

**Returns**: `ChartOfAccounts` object or `None` if creation fails

**Example**:
```python
new_account = self._auto_create_account(
    account_name="Prepaid Expenses",
    account_code=None,  # Will auto-generate
    document_type="balance_sheet"
)
```

#### `_infer_account_type_category(account_name, document_type)`
**Location**: `app/services/extraction_orchestrator.py:2493`

Determines account type and category from name patterns.

**Returns**: `(account_type, category)` tuple

**Example**:
```python
account_type, category = self._infer_account_type_category(
    "Prepaid Insurance",
    "balance_sheet"
)
# Returns: ('asset', 'current_asset')
```

#### `_generate_account_code(account_name, account_type)`
**Location**: `app/services/extraction_orchestrator.py:2549`

Generates sequential account codes based on type.

**Example**:
```python
code = self._generate_account_code("Cash", "asset")
# Returns: "0900-0000" (or next available in 0xxx range)
```

## Integration Flow

```
PDF Upload
    ↓
PDF Extraction
    ↓
Line Item Parsing
    ↓
_match_accounts_intelligent() ← document_type passed here
    ↓
Account Matching (exact/fuzzy)
    ↓
NO MATCH FOUND?
    ↓
_auto_create_account() ← receives document_type
    ↓
_infer_account_type_category() ← uses document_type for context
    ↓
_generate_account_code()
    ↓
Create ChartOfAccounts record
    ↓
Flag for review (needs_review=True)
    ↓
Continue extraction with new account
```

## Pattern Matching Logic

### Asset Patterns
| Pattern | Account Type | Category |
|---------|-------------|----------|
| cash, bank, deposit | asset | current_asset |
| receivable, a/r | asset | current_asset |
| prepaid | asset | current_asset |
| land, building, equipment | asset | fixed_asset |
| accumulated, depreciation | asset | contra_asset |

### Liability Patterns
| Pattern | Account Type | Category |
|---------|-------------|----------|
| payable, a/p, accrued | liability | current_liability |
| loan, mortgage (without "long") | liability | current_liability |
| long-term, mortgage, note | liability | long_term_liability |

### Equity Patterns
| Pattern | Account Type | Category |
|---------|-------------|----------|
| equity, capital | equity | capital |
| contribution, distribution | equity | capital |
| retained, earnings | equity | capital |

### Income Patterns
| Pattern | Account Type | Category |
|---------|-------------|----------|
| income, revenue | income | rental_income |
| rent, rental | income | rental_income |
| reimbursement | income | rental_income |

### Expense Patterns
| Pattern | Account Type | Category |
|---------|-------------|----------|
| expense, cost, fee | expense | operating_expense |
| tax, insurance | expense | operating_expense |
| utility, maintenance, repair | expense | operating_expense |

## Error Handling & Defensive Programming

### Parameter Validation
All methods validate inputs and fail gracefully:

```python
# Invalid inputs return None or raise ValueError
if not account_name or not isinstance(account_name, str):
    print(f"❌ Auto-create failed: Invalid account_name parameter")
    return None

if not account_name.strip():
    print(f"❌ Auto-create failed: Empty account_name")
    return None
```

### Detailed Logging
Every auto-creation is logged with full context:

```
🔧 Auto-creating account with context:
   - Account Name: Prepaid Expenses
   - Account Code: auto-generate
   - Document Type: balance_sheet
✅ Auto-created account: 0901-0000 - Prepaid Expenses
```

### Race Condition Protection
Before creating, the system checks if the account was just created by another process:

```python
existing = self.db.query(ChartOfAccounts).filter(
    ChartOfAccounts.account_code == account_code
).first()

if existing:
    print(f"ℹ️  Account already exists, using existing")
    return existing
```

## Testing

### Unit Tests
**Location**: `tests/test_auto_account_creation.py`

Comprehensive test suite covering:
- ✅ Parameter validation
- ✅ Account type inference for all patterns
- ✅ Account code generation
- ✅ Variable scope regression prevention
- ✅ Document type parameter passing
- ✅ Invalid input handling
- ✅ Fallback behavior

Run tests:
```bash
docker compose exec backend pytest tests/test_auto_account_creation.py -v
```

### Static Analysis
**Location**: `scripts/check_method_signatures.py`

Detects variable scope issues at development time:

```bash
python3 scripts/check_method_signatures.py app/services/extraction_orchestrator.py
```

This prevents bugs like:
- Variables used but not passed as parameters
- Missing parameter passing in method calls
- Undefined variable references

## Bug Prevention Measures

### 1. Type Hints & Validation
All methods have proper type hints and validate inputs:

```python
def _auto_create_account(
    self,
    account_name: str,
    account_code: str = None,
    document_type: str = None
) -> ChartOfAccounts:
```

### 2. Required Parameter Passing
Critical fix: `document_type` is now properly passed through the call chain:

```python
# Before (BROKEN):
def _match_accounts_intelligent(self, extracted_items: List[Dict]):
    # document_type not available here!
    self._auto_create_account(account_name, account_code, document_type)  # NameError!

# After (FIXED):
def _match_accounts_intelligent(self, extracted_items: List[Dict], document_type: str = None):
    # document_type parameter added ↑
    self._auto_create_account(account_name, account_code, document_type)  # Works!
```

### 3. Comprehensive Error Messages
All failures log detailed context for debugging:

```python
except Exception as e:
    print(f"❌ Failed to auto-create account '{account_name}': {e}")
    return None
```

### 4. Automated Testing
Test suite catches regressions before deployment:
- 30+ unit tests
- Variable scope regression tests
- Parameter passing verification

### 5. Static Analysis
Pre-commit checks prevent scope issues from being committed.

## Usage Examples

### Example 1: Missing Account in Balance Sheet
```python
# User uploads balance sheet with "Prepaid Insurance" account
# System encounters account not in chart_of_accounts
# Auto-creation triggered:

new_account = _auto_create_account(
    account_name="Prepaid Insurance",
    account_code=None,
    document_type="balance_sheet"
)

# System infers: asset, current_asset
# Generates code: 0901-0000
# Creates account with notes: "Auto-created from balance_sheet extraction"
# Flags for review: needs_review = True
# Extraction continues successfully
```

### Example 2: Unknown Expense
```python
# User uploads income statement with unknown expense
# System handles gracefully:

new_account = _auto_create_account(
    account_name="Property Management Fee",
    account_code="UNMATCHED",  # Will auto-generate
    document_type="income_statement"
)

# System infers: expense, operating_expense
# Generates code: 5901-0000
# Extraction continues
```

## Future Improvements

1. **Machine Learning**: Train ML model on historical account patterns
2. **User Feedback Loop**: Learn from user corrections to improve inference
3. **Confidence Scoring**: Add confidence scores to auto-created accounts
4. **Bulk Review**: UI for reviewing all auto-created accounts at once
5. **Account Merging**: Detect and merge duplicate auto-created accounts

## Troubleshooting

### Issue: Auto-creation fails silently
**Check**: Backend logs for detailed error messages
```bash
docker compose logs backend | grep "Auto-creating"
```

### Issue: Wrong account type inferred
**Action**: The account is flagged with `needs_review=True`. User should:
1. Review auto-created accounts in UI
2. Correct type/category if needed
3. System learns from correction (future enhancement)

### Issue: Duplicate accounts created
**Cause**: Race condition between parallel extractions
**Prevention**: Code checks for existing accounts before creating
**Fix**: Merge duplicates manually or use upcoming bulk review feature

## Configuration

No configuration needed - the system works out of the box!

Optional environment variables (future):
- `AUTO_CREATE_ACCOUNTS` - Enable/disable feature (default: true)
- `AUTO_CREATE_REVIEW_THRESHOLD` - Confidence threshold for flagging review (default: 100%)

## Conclusion

The auto-account creation system eliminates a major pain point in financial data extraction by making the system intelligent and self-maintaining. With comprehensive testing, validation, and defensive programming, it prevents the class of variable scope bugs that could have broken the feature.

**Key Benefits**:
- ✅ No more extraction failures due to missing accounts
- ✅ System handles new accounts automatically
- ✅ Users retain control via review flags
- ✅ Robust error handling and validation
- ✅ Comprehensive testing prevents regressions
- ✅ Static analysis catches issues at development time

---

**Last Updated**: 2025-12-19
**Version**: 1.0
**Author**: REIMS2 Development Team
