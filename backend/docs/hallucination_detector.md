# Hallucination Detector Service

## Overview

The Hallucination Detector service identifies and verifies numeric claims in LLM-generated answers by comparing them against source data (database records and document chunks). Unverified claims are flagged for review, and confidence scores are adjusted accordingly.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              LLM-Generated Answer                          │
│  "The NOI was $1,234,567.89 and occupancy was 85.5%"       │
└────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Claim Extraction                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Currency │  │Percentage│  │   Date   │  │  Ratio   │    │
│  │  $1.2M   │  │   85.5%  │  │ Q3 2024  │  │ DSCR 1.25│    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Claim Verification                             │
│  ┌──────────────┐              ┌──────────────┐            │
│  │  Database    │              │  Documents   │            │
│  │  Verification│              │  Verification│            │
│  │  (PostgreSQL)│              │  (Chunks)    │            │
│  └──────────────┘              └──────────────┘            │
│         │                              │                    │
│         └──────────────┬───────────────┘                    │
│                        ▼                                    │
│              ┌──────────────────┐                           │
│              │ Verified/Unverified│                          │
│              └──────────────────┘                           │
└────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Result & Confidence Adjustment                  │
│  {                                                           │
│    "has_hallucinations": false,                              │
│    "verified_claims": 2,                                    │
│    "unverified_claims": 0,                                  │
│    "confidence_adjustment": 0.0                             │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Installation

No additional installation required. Dependencies are included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from app.services.hallucination_detector import HallucinationDetector
from sqlalchemy.orm import Session

# Initialize detector
detector = HallucinationDetector(db=db_session)

# Detect hallucinations in LLM answer
result = detector.detect_hallucinations(
    answer="The NOI was $1,234,567.89 and occupancy was 85.5%",
    sources=retrieved_chunks,  # Optional: document chunks
    property_id=1,  # Optional: for database verification
    period_id=1     # Optional: for database verification
)

# Check results
if result['has_hallucinations']:
    print(f"Found {result['unverified_claims']} unverified claims")
    for claim in result['flagged_claims']:
        print(f"  - {claim['original_text']} ({claim['claim_type']})")
else:
    print("All claims verified!")
```

### Adjusting Confidence

```python
# Get original confidence from LLM
original_confidence = 0.95

# Adjust based on hallucination detection
adjusted_confidence = detector.adjust_confidence(
    original_confidence=original_confidence,
    detection_result=result
)

print(f"Original: {original_confidence}, Adjusted: {adjusted_confidence}")
```

### Flagging for Review

```python
# Flag answer for manual review if hallucinations detected
review = detector.flag_for_review(
    nlq_query_id=123,
    user_id=1,
    answer="The NOI was $1,234,567.89",
    original_confidence=0.95,
    detection_result=result,
    property_id=1,
    period_id=1
)

if review:
    print(f"Answer flagged for review: {review.id}")
```

## API Reference

### HallucinationDetector

#### `__init__(db: Session)`

Initialize the hallucination detector.

**Args**:
- `db`: Database session for verifying claims

**Example**:
```python
detector = HallucinationDetector(db=db_session)
```

---

#### `detect_hallucinations(answer: str, sources: Optional[List[Dict]] = None, property_id: Optional[int] = None, period_id: Optional[int] = None) -> Dict[str, Any]`

Detect hallucinations in LLM answer by verifying numeric claims.

**Args**:
- `answer`: LLM-generated answer text
- `sources`: List of source documents/chunks used (optional)
- `property_id`: Property ID for context (optional)
- `period_id`: Period ID for context (optional)

**Returns**:
Dictionary with detection results:
```python
{
    'has_hallucinations': bool,
    'claims': List[Dict],  # All extracted claims
    'flagged_claims': List[Dict],  # Unverified claims
    'verification_time_ms': float,
    'confidence_adjustment': float,  # Negative if hallucinations
    'total_claims': int,
    'verified_claims': int,
    'unverified_claims': int
}
```

**Raises**:
- `ValueError`: If answer is invalid
- `SQLAlchemyError`: If database query fails

**Example**:
```python
result = detector.detect_hallucinations(
    answer="The NOI was $1,234,567.89",
    property_id=1,
    period_id=1
)
```

---

#### `adjust_confidence(original_confidence: float, detection_result: Dict[str, Any]) -> float`

Adjust confidence score based on hallucination detection.

**Args**:
- `original_confidence`: Original confidence score (0-1)
- `detection_result`: Result from `detect_hallucinations()`

**Returns**:
Adjusted confidence score (0-1)

**Example**:
```python
adjusted = detector.adjust_confidence(0.95, result)
```

---

#### `flag_for_review(nlq_query_id: int, user_id: int, answer: str, original_confidence: float, detection_result: Dict[str, Any], property_id: Optional[int] = None, period_id: Optional[int] = None) -> Optional[HallucinationReview]`

Flag answer for manual review if hallucinations detected.

**Args**:
- `nlq_query_id`: ID of the NLQ query
- `user_id`: User ID who asked the question
- `answer`: LLM-generated answer
- `original_confidence`: Original confidence score
- `detection_result`: Result from `detect_hallucinations()`
- `property_id`: Property ID (optional)
- `period_id`: Period ID (optional)

**Returns**:
`HallucinationReview` object if flagged, `None` otherwise

**Example**:
```python
review = detector.flag_for_review(
    nlq_query_id=123,
    user_id=1,
    answer="The NOI was $1,234,567.89",
    original_confidence=0.95,
    detection_result=result
)
```

## Configuration

Configuration is managed in `backend/app/config/hallucination_config.py`:

```python
# Tolerance settings
CURRENCY_TOLERANCE_PERCENT = 5.0  # 5% tolerance for currency
PERCENTAGE_TOLERANCE_PERCENT = 2.0  # 2% tolerance for percentages
RATIO_TOLERANCE_PERCENT = 5.0  # 5% tolerance for ratios
DATE_TOLERANCE_DAYS = 7  # 7 days tolerance for dates

# Confidence adjustment
CONFIDENCE_PENALTY_PERCENT = 20.0  # Reduce confidence by 20% if hallucinations

# Verification settings
VERIFY_CURRENCY = True
VERIFY_PERCENTAGES = True
VERIFY_DATES = True
VERIFY_RATIOS = True
VERIFY_AGAINST_DATABASE = True
VERIFY_AGAINST_DOCUMENTS = True

# Review queue
REVIEW_QUEUE_ENABLED = True
AUTO_FLAG_UNVERIFIED = True
LOG_UNVERIFIED_CLAIMS = True

# Performance
VERIFICATION_TIMEOUT_MS = 100  # Timeout for verification
MAX_SOURCE_CHECKS = 10  # Max sources to check per claim
```

## Claim Types

### Currency Claims

Extracts currency values in various formats:
- `$1,234,567.89`
- `$1.2M` (million)
- `$500K` (thousand)
- `1.5 million dollars`

**Verification**: Checks against `FinancialMetrics` and `IncomeStatementData` tables.

### Percentage Claims

Extracts percentage values:
- `85.5%`
- `12.5 percent`
- `15.25 percentage`

**Verification**: Checks against percentage fields in `FinancialMetrics`.

### Ratio Claims

Extracts ratio values:
- `DSCR 1.25`
- `1.5x coverage`
- `ratio of 1.25`

**Verification**: Checks against `dscr` field in `FinancialMetrics`.

### Date Claims

Extracts date values:
- `Q3 2024`
- `December 2024`
- `2024-12-01`
- `12/01/2024`

**Verification**: Checks against `FinancialPeriod` table.

## Error Handling

### Database Errors

```python
try:
    result = detector.detect_hallucinations(answer)
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    # Returns result with error flag
    result = {'error': str(e), 'has_hallucinations': False}
```

### Invalid Input

```python
# Empty answer
result = detector.detect_hallucinations("")
# Returns: {'has_hallucinations': False, 'total_claims': 0}

# None answer
result = detector.detect_hallucinations(None)
# Returns: {'has_hallucinations': False, 'total_claims': 0}
```

### Timeout Handling

Verification operations have a timeout (default: 100ms). If timeout exceeded:
- Returns unverified status for the claim
- Logs warning
- Continues with other claims

## Performance Considerations

### Optimization Tips

1. **Batch Verification**: Verify multiple claims in single database query
2. **Caching**: Cache verification results for repeated claims
3. **Parallel Processing**: Verify claims in parallel (if needed)
4. **Index Usage**: Ensure database indexes on `property_id` and `period_id`

### Performance Targets

- **Claim Extraction**: <10ms per answer
- **Database Verification**: <50ms per claim
- **Document Verification**: <30ms per claim
- **Total Detection**: <100ms for typical answer

## Testing

### Unit Tests

```bash
pytest tests/services/test_hallucination_detector.py -v
```

### Test Coverage

Target: >80% code coverage

```bash
pytest tests/services/test_hallucination_detector.py --cov=app.services.hallucination_detector --cov-report=html
```

## Troubleshooting

### No Claims Extracted

**Issue**: No claims found in answer.

**Solutions**:
- Check answer format (should contain numeric values)
- Verify claim patterns match answer format
- Check configuration (VERIFY_* flags enabled)

### All Claims Unverified

**Issue**: All claims marked as unverified.

**Solutions**:
- Check database has matching data
- Verify property_id/period_id are correct
- Check tolerance settings (may be too strict)
- Verify document chunks contain claim values

### Slow Performance

**Issue**: Detection takes too long.

**Solutions**:
- Check database indexes
- Reduce MAX_SOURCE_CHECKS
- Enable caching
- Use batch verification

### Database Errors

**Issue**: Database connection errors.

**Solutions**:
- Check database connection
- Verify database schema
- Check SQLAlchemy session
- Review error logs

## Examples

### Example 1: Simple Currency Verification

```python
answer = "The NOI was $1,234,567.89 for Q3 2024."

result = detector.detect_hallucinations(
    answer=answer,
    property_id=1,
    period_id=1
)

# Result:
# {
#     'has_hallucinations': False,
#     'total_claims': 2,  # Currency + Date
#     'verified_claims': 2,
#     'unverified_claims': 0,
#     'confidence_adjustment': 0.0
# }
```

### Example 2: Unverified Claim

```python
answer = "The NOI was $9,999,999.99 for Q3 2024."

result = detector.detect_hallucinations(
    answer=answer,
    property_id=1,
    period_id=1
)

# Result:
# {
#     'has_hallucinations': True,
#     'total_claims': 2,
#     'verified_claims': 1,  # Date verified
#     'unverified_claims': 1,  # Currency not verified
#     'flagged_claims': [
#         {
#             'claim_type': 'currency',
#             'value': 9999999.99,
#             'original_text': '$9,999,999.99'
#         }
#     ],
#     'confidence_adjustment': -0.20  # 20% penalty
# }
```

### Example 3: With Document Sources

```python
chunks = [
    {
        'chunk_text': 'The net operating income was $1,234,567.89',
        'chunk_id': 1
    }
]

result = detector.detect_hallucinations(
    answer="The NOI was $1,234,567.89",
    sources=chunks
)

# Claims verified against document chunks
```

## Related Documentation

- [Citation Extractor](./citation_extractor.md)
- [RAG Retrieval Service](./rag_retrieval_service.md)
- [Testing Guide](../tests/README_TESTING.md)

