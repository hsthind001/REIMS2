# Accuracy Fix - Quick Start Guide

## Problem
- Precision@5: 65% (target: >90%)
- Hybrid search worse than semantic alone
- Wrong time periods, wrong properties

## Quick Fix (5 minutes)

### Step 1: Use Fixed Service

```python
# In your NLQ service or API
from app.services.rag_retrieval_service_fixed import FixedRAGRetrievalService

# Replace old service
rag_service = FixedRAGRetrievalService(db)
```

### Step 2: Update Config

```python
# In app/config/rrf_config.py (or create rrf_config_fixed.py)
ALPHA = 0.85  # Increased from 0.7
```

### Step 3: Test

```python
# Test query
results = rag_service.retrieve_relevant_chunks(
    query="What was NOI for Eastern Shore in Q3 2024?",
    top_k=5,
    use_bm25=True,
    use_rrf=True
)

# Should now return Q3 data, not Q4
```

## Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Precision@5 | 65% | 85-90% | +20-25% |
| Hybrid vs Semantic | 65% < 70% | 85-90% > 70% | Fixed |
| Time Period Accuracy | 40% | 90% | +50% |
| Property Accuracy | 50% | 85% | +35% |

## What Was Fixed

1. **Score Normalization**: BM25 scores normalized to 0-1 range
2. **Entity Extraction**: "Q3" → period_id filter automatically
3. **Pre-Filtering**: Filters applied before scoring, not after
4. **Adaptive Alpha**: RRF alpha adjusted based on query type
5. **Better Chunking**: Increased overlap to preserve context

## Verification

Run evaluation script:
```bash
python backend/tests/evaluation/test_rag_accuracy.py
```

Check logs for:
- "Extracted property_id X from query"
- "Extracted period_id Y from query"
- Normalized BM25 scores (0-1 range)

## Rollback

If issues:
```python
# Revert to old service
from app.services.rag_retrieval_service import RAGRetrievalService
rag_service = RAGRetrievalService(db)
```

## Next Steps

1. **Monitor**: Track precision@5 in production
2. **Tune**: Adjust alpha based on query patterns
3. **Improve Chunking**: Re-chunk documents with new overlap settings
4. **Evaluate**: Run evaluation script weekly

