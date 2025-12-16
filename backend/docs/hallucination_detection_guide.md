# Hallucination Detection Guide

## Overview

Hallucination detection identifies and flags unsupported numeric claims in LLM-generated answers. The system extracts numeric claims (currency, percentages, dates, ratios) and verifies them against source data (database and documents) to ensure users receive accurate information.

## Architecture

```
LLM Answer
    ↓
[Hallucination Detector]
    ├─ Extract Numeric Claims (regex)
    ├─ Verify Against Database
    ├─ Verify Against Documents
    └─ Flag Unverified Claims
    ↓
[Review Queue]
    └─ Flagged answers for manual review
    ↓
[Confidence Adjustment]
    └─ Reduce confidence by 20% for flagged answers
```

## Claim Types

### 1. Currency Claims

**Formats**:
- `$1,234,567.89`
- `$1.2M` (million)
- `$1.5 million`
- `$500K` (thousand)

**Tolerance**: ±5%

**Example**:
- Claim: "$1.5M NOI"
- Actual: $1.2M
- Result: **FLAGGED** (25% difference, outside 5% tolerance)

### 2. Percentage Claims

**Formats**:
- `85%`
- `12.5 percent`
- `12.5 percentage`

**Tolerance**: ±2%

**Example**:
- Claim: "95% occupancy"
- Actual: 85%
- Result: **FLAGGED** (11.8% difference, outside 2% tolerance)

### 3. Date Claims

**Formats**:
- `Q3 2024`
- `December 2024`
- `2024-12-01`
- `12/01/2024`

**Tolerance**: Exact match (0 days)

**Example**:
- Claim: "Q4 2024"
- Actual: Q3 2024
- Result: **FLAGGED** (different period)

### 4. Ratio Claims

**Formats**:
- `DSCR 1.25`
- `1.25x coverage`
- `ratio of 1.25`

**Tolerance**: ±5%

**Example**:
- Claim: "DSCR 1.5"
- Actual: 1.25
- Result: **FLAGGED** (20% difference, outside 5% tolerance)

## Usage

### Basic Detection

```python
from app.services.hallucination_detector import HallucinationDetector
from app.db.database import SessionLocal

db = SessionLocal()
detector = HallucinationDetector(db)

# Detect hallucinations in answer
result = detector.detect_hallucinations(
    answer="The NOI was $1.5M for the property.",
    property_id=1,
    period_id=1
)

print(f"Has hallucinations: {result['has_hallucinations']}")
print(f"Total claims: {result['total_claims']}")
print(f"Unverified claims: {result['unverified_claims']}")
print(f"Confidence adjustment: {result['confidence_adjustment']:.2%}")
```

### With Source Documents

```python
sources = [
    {
        'chunk_text': 'The NOI for the property was $1,200,000 in Q3 2024.',
        'chunk_id': 1
    }
]

result = detector.detect_hallucinations(
    answer="The NOI was $1.2M.",
    sources=sources
)
```

### Confidence Adjustment

```python
original_confidence = 0.9
detection_result = detector.detect_hallucinations(answer, ...)

adjusted_confidence = detector.adjust_confidence(
    original_confidence=original_confidence,
    detection_result=detection_result
)

# If hallucinations detected, confidence reduced by 20%
# adjusted_confidence = 0.7 (0.9 - 0.2)
```

### Flagging for Review

```python
# Automatically flags for review if hallucinations detected
review = detector.flag_for_review(
    nlq_query_id=123,
    user_id=1,
    answer="The NOI was $1.5M.",
    original_confidence=0.9,
    detection_result=result,
    property_id=1,
    period_id=1
)

if review:
    print(f"Answer flagged for review: Review ID {review.id}")
```

## Verification Logic

### Database Verification

**Currency Claims**:
- Checks `FinancialMetrics` table for:
  - `net_operating_income`
  - `total_revenue`
  - `total_expenses`
  - `net_income`
  - `total_assets`
  - `total_liabilities`
- Checks `IncomeStatementData` for `amount` field
- Applies ±5% tolerance

**Percentage Claims**:
- Checks `FinancialMetrics` for:
  - `occupancy_rate`
  - `expense_ratio`
  - `debt_to_equity_ratio`
  - `cap_rate`
  - `return_on_investment`
- Applies ±2% tolerance

**Ratio Claims**:
- Checks `FinancialMetrics` for `dscr` field
- Applies ±5% tolerance

**Date Claims**:
- Checks `FinancialPeriod` for matching year/quarter/month
- Requires exact match

### Document Verification

**Strategy**:
- Searches source document chunks for matching values
- Applies tolerance based on claim type
- Lower confidence (0.8) for document matches vs database (1.0)

## Configuration

### Tolerance Settings

```python
from app.config.hallucination_config import hallucination_config

# Currency tolerance: ±5%
hallucination_config.CURRENCY_TOLERANCE_PERCENT = 5.0

# Percentage tolerance: ±2%
hallucination_config.PERCENTAGE_TOLERANCE_PERCENT = 2.0

# Ratio tolerance: ±5%
hallucination_config.RATIO_TOLERANCE_PERCENT = 5.0

# Date tolerance: 0 days (exact match)
hallucination_config.DATE_TOLERANCE_DAYS = 0
```

### Confidence Penalty

```python
# Reduce confidence by 20% for flagged answers
hallucination_config.CONFIDENCE_PENALTY_PERCENT = 20.0
```

### Environment Variables

```bash
# Tolerance Settings
export HALLUCINATION_CURRENCY_TOLERANCE=5.0
export HALLUCINATION_PERCENTAGE_TOLERANCE=2.0
export HALLUCINATION_RATIO_TOLERANCE=5.0

# Confidence Penalty
export HALLUCINATION_CONFIDENCE_PENALTY=20.0

# Performance
export HALLUCINATION_TARGET_TIME_MS=100
export HALLUCINATION_TARGET_RATE=0.05

# Verification
export HALLUCINATION_VERIFY_CURRENCY="true"
export HALLUCINATION_VERIFY_PERCENTAGES="true"
export HALLUCINATION_VERIFY_DATES="true"
export HALLUCINATION_VERIFY_RATIOS="true"

# Review Queue
export HALLUCINATION_AUTO_FLAG="true"
export HALLUCINATION_REVIEW_QUEUE="true"
```

## Review Queue

### Review Queue Model

The `HallucinationReview` model stores flagged answers for manual review:

```python
{
    'id': 1,
    'nlq_query_id': 123,
    'user_id': 1,
    'original_answer': 'The NOI was $1.5M.',
    'original_confidence': 0.9,
    'adjusted_confidence': 0.7,
    'total_claims': 1,
    'verified_claims': 0,
    'unverified_claims': 1,
    'flagged_claims': [
        {
            'claim_type': 'currency',
            'value': 1500000.0,
            'original_text': '$1.5M',
            'verified': False
        }
    ],
    'status': 'pending',
    'property_id': 1,
    'period_id': 1
}
```

### Review Status

- **pending**: Awaiting review
- **reviewed**: Under review
- **approved**: Verified as correct (false positive)
- **rejected**: Confirmed as hallucination (true positive)

## Examples

### Example 1: Correct Claim (No Hallucination)

**Answer**: "The NOI was $1.2M for the property."

**Actual Value**: $1,200,000

**Result**:
- ✅ Claim verified
- ✅ No hallucination detected
- ✅ Confidence unchanged

### Example 2: Wrong Claim (Hallucination)

**Answer**: "The NOI was $1.5M for the property."

**Actual Value**: $1,200,000

**Result**:
- ❌ Claim unverified (25% difference, outside 5% tolerance)
- ❌ Hallucination detected
- ❌ Confidence reduced by 20%
- ❌ Flagged for review

### Example 3: Within Tolerance (Verified)

**Answer**: "The NOI was $1.25M for the property."

**Actual Value**: $1,200,000

**Result**:
- ✅ Claim verified (4.2% difference, within 5% tolerance)
- ✅ No hallucination detected
- ✅ Confidence unchanged

## Performance

### Verification Time Target: <100ms

**Breakdown**:
- Claim extraction: <10ms
- Database verification: ~50-80ms
- Document verification: ~20-50ms
- Total: <100ms

**Optimization**:
- Limit database queries
- Cache verification results
- Parallel verification when possible

## Accuracy

### Target: <5% Hallucination Rate

**Measurement**:
- Run accuracy measurement script
- Calculate hallucination rate: `unverified_claims / total_claims`
- Track over time

**Improving Accuracy**:
- Tune tolerance thresholds
- Improve claim extraction patterns
- Enhance verification logic
- Learn from review queue

## Accuracy Measurement

### Run Accuracy Script

```bash
python backend/scripts/measure_hallucination_accuracy.py
```

**Output**:
```
============================================================
Hallucination Detection Accuracy Report
============================================================

Total Test Cases: 8

Confusion Matrix:
  True Positives (TP):  4
  False Positives (FP): 0
  False Negatives (FN): 0
  True Negatives (TN):  4

Metrics:
  Accuracy:  100.00%
  Precision: 100.00%
  Recall:    100.00%
  F1 Score:  100.00%

Claims:
  Total Claims:     12
  Verified Claims:  8
  Unverified Claims: 4
  Hallucination Rate: 33.33%
  Target Rate:      5.00%
  Meets Target:     ❌ NO
============================================================
```

## Best Practices

1. **Always Verify Claims**: Run detection on all LLM answers
2. **Use Context**: Provide property_id and period_id for better verification
3. **Include Sources**: Pass source documents for document verification
4. **Review Flagged Answers**: Manually review flagged answers in review queue
5. **Monitor Accuracy**: Track hallucination rate over time
6. **Tune Tolerances**: Adjust tolerances based on data quality

## Troubleshooting

### High False Positive Rate

**Possible Causes**:
- Tolerance too strict
- Data not in database
- Verification logic too conservative

**Solutions**:
- Increase tolerance thresholds
- Ensure data is loaded
- Review verification logic

### High False Negative Rate

**Possible Causes**:
- Tolerance too loose
- Claims not extracted correctly
- Verification not checking all sources

**Solutions**:
- Decrease tolerance thresholds
- Improve claim extraction patterns
- Enhance verification coverage

### Slow Verification

**Possible Causes**:
- Too many database queries
- Large source document sets
- Inefficient verification logic

**Solutions**:
- Limit database queries
- Cache verification results
- Optimize verification logic

## Success Criteria

- ✅ Extracts all numeric claims from LLM answers
- ✅ Verifies each claim exists in source data (within tolerance)
- ✅ Flags unverified claims for manual review
- ✅ Confidence score reduced by 20% for flagged answers
- ✅ Hallucination rate <5% on test set
- ✅ Verification time <100ms
- ✅ Review queue for flagged answers
- ✅ Accuracy measurement script

## Future Enhancements

- **Machine Learning**: Train classifier on review queue data
- **Adaptive Tolerances**: Adjust tolerances based on data quality
- **Claim Confidence**: Score individual claims, not just binary
- **Multi-Source Verification**: Verify against multiple sources
- **Temporal Verification**: Verify claims against historical data

