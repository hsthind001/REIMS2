# Duplicate Prevention System Guide

## Overview

The Duplicate Prevention System is a future-proof, intelligent deduplication service that prevents unique constraint violations during financial document extraction. It ensures that the system never encounters duplicate key errors by intelligently selecting the best record when duplicates are detected.

## Problem Statement

Financial document extraction can sometimes produce duplicate records with the same constraint keys (e.g., same `account_code`, or same `account_code + account_name`). When these duplicates are inserted into the database, they violate unique constraints, causing extraction failures.

### Unique Constraints by Document Type

1. **Balance Sheet**: `(property_id, period_id, account_code)`
2. **Income Statement**: `(property_id, period_id, account_code, account_name)`
3. **Cash Flow**: 
   - `(property_id, period_id, account_code)` 
   - `(property_id, period_id, account_code, account_name, line_number)`

## Solution Architecture

### Core Components

1. **DeduplicationService** (`backend/app/services/deduplication_service.py`)
   - Generic, reusable deduplication service
   - Constraint-aware deduplication logic
   - Intelligent record selection strategies
   - Pre-insertion validation

2. **Integration in ExtractionOrchestrator** (`backend/app/services/extraction_orchestrator.py`)
   - Applied to all document types (balance sheet, income statement, cash flow)
   - Automatic deduplication before database insertion
   - Comprehensive logging and statistics

3. **Pre-Insertion Validation**
   - Safety check that should never fail if deduplication worked correctly
   - Provides clear error messages if validation fails

## How It Works

### 1. Constraint-Aware Deduplication

The service generates a unique constraint key from specified columns:

```python
# Balance Sheet: account_code only
constraint_key = "0121-0000"

# Income Statement: account_code + account_name
constraint_key = "4010-0000|||Base Rentals"

# Cash Flow: account_code + account_name + line_number
constraint_key = "4010-0000|||Base Rentals|||1"
```

### 2. Intelligent Record Selection

When duplicates are detected, the service selects the "best" record based on:

- **For Totals/Subtotals**: Prefer higher absolute amount (more complete)
- **For Detail Lines**: Prefer higher confidence (more accurate)
- **Tie-Breaker**: Higher amount, then first occurrence

### 3. Selection Strategies

The service supports three selection strategies:

- **`confidence`**: Prefer higher confidence score (default for detail lines)
- **`amount`**: Prefer higher absolute amount (default for totals/subtotals)
- **`completeness`**: Prefer record with more non-null fields

### 4. Automatic Strategy Selection

The service automatically uses the appropriate strategy based on item type:

```python
# Totals/subtotals → amount strategy
# Detail lines → confidence strategy
```

## Usage

### Basic Usage

```python
from app.services.deduplication_service import get_deduplication_service

dedup_service = get_deduplication_service()

result = dedup_service.deduplicate_items(
    items=extracted_items,
    constraint_columns=['account_code', 'account_name'],
    selection_strategy='confidence',
    document_type='income_statement',
    is_total_or_subtotal=lambda item: item.get('is_total', False)
)

deduplicated_items = result['deduplicated_items']
statistics = result['statistics']
duplicate_details = result['duplicate_details']
```

### Integration in ExtractionOrchestrator

The deduplication is automatically applied in:

- `_insert_balance_sheet_data()` - Uses `['account_code']` constraint
- `_insert_income_statement_data()` - Uses `['account_code', 'account_name']` constraint
- `_insert_cash_flow_data()` - Uses `['account_code', 'account_name', 'line_number']` constraint

### Pre-Insertion Validation

Before database insertion, validation ensures no duplicates remain:

```python
is_valid, error_msg = dedup_service.validate_no_duplicates(
    items=deduplicated_items,
    constraint_columns=['account_code', 'account_name'],
    context="income_statement insertion (upload_id=123)"
)

if not is_valid:
    raise ValueError(f"Pre-insertion validation failed: {error_msg}")
```

## Configuration

### Constraint Definitions

The service includes predefined constraint mappings:

```python
DOCUMENT_TYPE_CONSTRAINTS = {
    'balance_sheet': ['account_code'],
    'income_statement': ['account_code', 'account_name'],
    'cash_flow': ['account_code', 'account_name', 'line_number']
}
```

### Custom Constraints

You can use any combination of columns as constraints:

```python
# Custom constraint
result = dedup_service.deduplicate_items(
    items=items,
    constraint_columns=['account_code', 'period_type', 'line_number']
)
```

## Logging and Monitoring

### Statistics

The service returns comprehensive statistics:

```python
{
    'total_items': 100,
    'duplicates_found': 5,
    'duplicates_removed': 5,
    'final_count': 95
}
```

### Duplicate Details

Detailed information about each duplicate detection:

```python
{
    'constraint_key': '4010-0000|||Base Rentals',
    'action': 'replaced',  # or 'kept_existing'
    'reason': 'higher confidence (90.0 → 95.0)',
    'existing_confidence': 90.0,
    'new_confidence': 95.0,
    'existing_amount': 1000.0,
    'new_amount': 1200.0,
    'item_index': 5
}
```

### Console Logging

The service logs duplicate detections:

```
⚠️  Found 5 duplicate(s) for income_statement - deduplicated to 95 unique records
   - replaced: 4010-0000|||Base Rentals (higher confidence (90.0 → 95.0))
   - kept_existing: 4020-0000|||Tax (lower confidence (85.0 vs 90.0))
```

## Testing

### Unit Tests

Comprehensive unit tests in `backend/tests/test_deduplication_service.py`:

- No duplicates scenario
- Single column constraint
- Multi-column constraint
- Selection strategies (confidence, amount, completeness)
- Totals vs detail lines
- Tie-breakers
- Missing constraint columns
- UNMATCHED account codes
- Validation tests

### Integration Tests

Full integration tests in `backend/tests/test_deduplication_integration.py`:

- Balance sheet duplicate prevention
- Income statement duplicate prevention
- Cash flow duplicate prevention
- Totals prefer amount strategy
- Details prefer confidence strategy
- Validation catches duplicates

### Running Tests

```bash
# Run unit tests
pytest backend/tests/test_deduplication_service.py -v

# Run integration tests
pytest backend/tests/test_deduplication_integration.py -v

# Run all deduplication tests
pytest backend/tests/test_deduplication*.py -v
```

## Best Practices

### 1. Always Use Deduplication Before Insertion

```python
# ✅ Good: Deduplicate before insertion
dedup_result = dedup_service.deduplicate_items(...)
deduplicated_items = dedup_result['deduplicated_items']
# Insert deduplicated_items

# ❌ Bad: Insert without deduplication
# Insert items directly (will fail on duplicates)
```

### 2. Use Appropriate Constraint Columns

Match the constraint columns to your database unique constraint:

```python
# Balance Sheet: (property_id, period_id, account_code)
constraint_columns = ['account_code']

# Income Statement: (property_id, period_id, account_code, account_name)
constraint_columns = ['account_code', 'account_name']

# Cash Flow: (property_id, period_id, account_code, account_name, line_number)
constraint_columns = ['account_code', 'account_name', 'line_number']
```

### 3. Provide is_total_or_subtotal Function

This enables automatic strategy selection:

```python
is_total_or_subtotal = lambda item: (
    item.get('is_total', False) or 
    item.get('is_subtotal', False)
)
```

### 4. Always Validate Before Insertion

```python
# Safety check (should never fail if deduplication worked)
is_valid, error_msg = dedup_service.validate_no_duplicates(...)
if not is_valid:
    raise ValueError(f"Validation failed: {error_msg}")
```

### 5. Log Statistics

Monitor deduplication patterns:

```python
stats = result['statistics']
if stats['duplicates_removed'] > 0:
    logger.warning(f"Removed {stats['duplicates_removed']} duplicates")
```

## Adding New Document Types

To add deduplication for a new document type:

1. **Define the constraint**:
   ```python
   DOCUMENT_TYPE_CONSTRAINTS['new_document_type'] = ['column1', 'column2']
   ```

2. **Apply deduplication in extraction**:
   ```python
   dedup_result = dedup_service.deduplicate_items(
       items=items,
       constraint_columns=['column1', 'column2'],
       document_type='new_document_type',
       is_total_or_subtotal=lambda item: item.get('is_total', False)
   )
   ```

3. **Add pre-insertion validation**:
   ```python
   is_valid, error_msg = dedup_service.validate_no_duplicates(
       items=deduplicated_items,
       constraint_columns=['column1', 'column2'],
       context="new_document_type insertion"
   )
   ```

4. **Add tests**:
   - Unit tests for the new constraint
   - Integration tests for the new document type

## Troubleshooting

### Validation Fails After Deduplication

If validation fails after deduplication, this indicates a bug in the deduplication logic:

1. Check that constraint columns match the database constraint
2. Verify that `_generate_constraint_key()` handles all edge cases
3. Review duplicate detection logic

### Too Many Duplicates Detected

If deduplication removes many items, this may indicate:

1. Extraction quality issues (low confidence scores)
2. PDF parsing problems (duplicate text extraction)
3. Template matching issues

Monitor the duplicate rate and investigate if it's unusually high.

### Missing Constraint Columns

Items with missing constraint columns are skipped:

```python
# Item with missing account_code will be skipped
{'account_name': 'Base Rentals'}  # Missing account_code
```

Ensure extraction provides all required constraint columns.

## Performance Considerations

- **Time Complexity**: O(n) where n is the number of items
- **Space Complexity**: O(n) for tracking seen items
- **Optimization**: Uses dictionary lookup for O(1) duplicate detection

The service is designed to handle large batches efficiently.

## Future Enhancements

Potential improvements:

1. **Configurable Selection Strategies**: Allow custom selection functions
2. **Duplicate Pattern Detection**: Track patterns to identify extraction issues
3. **Metrics Dashboard**: Visualize deduplication statistics over time
4. **Alerting**: Alert when duplicate rate exceeds threshold
5. **Machine Learning**: Learn optimal selection strategies from historical data

## Related Documentation

- [Extraction Orchestrator](../backend/app/services/extraction_orchestrator.py)
- [Database Schema](../backend/alembic/versions/)
- [Auto-Account Creation System](./AUTO_ACCOUNT_CREATION_SYSTEM.md)

## Support

For issues or questions:

1. Check the test files for usage examples
2. Review the code comments in `DeduplicationService`
3. Check extraction logs for duplicate detection details
4. Review database constraints to ensure correct column mapping

