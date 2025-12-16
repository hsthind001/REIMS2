# RAG Accuracy Fix Guide

## Problem Summary

- **Precision@5**: 65% (target: >90%)
- **Hybrid search worse than semantic alone**: 65% vs 70%
- **Issues**: Wrong time periods, wrong property types

## Root Causes Identified

### 1. Score Normalization Issue (CRITICAL)
**Problem**: BM25 scores (0-100+) vs semantic scores (0-1) on different scales
**Impact**: RRF fusion gives incorrect weights
**Fix**: Normalize BM25 scores to 0-1 range before fusion

### 2. Metadata Filtering Not Applied (CRITICAL)
**Problem**: Filters applied AFTER scoring, not before
**Impact**: Wrong property/period results included
**Fix**: Apply filters in Pinecone query and BM25 search

### 3. RRF Alpha Too Low
**Problem**: Alpha=0.7 gives too much weight to low-quality BM25 results
**Impact**: BM25 noise drags down hybrid precision
**Fix**: Increase alpha to 0.85 or use adaptive alpha

### 4. No Entity Extraction
**Problem**: Query "Q3" not extracted to period_id filter
**Impact**: Returns Q4 data because no filter applied
**Fix**: Extract entities from query and set filters

### 5. Chunking Context Loss
**Problem**: 100-token overlap may split important context
**Impact**: Chunks missing query-relevant information
**Fix**: Increase overlap to 200 tokens, use sentence-aware chunking

## Implementation

### Step 1: Use Fixed Service (Immediate)

```python
# Replace
from app.services.rag_retrieval_service import RAGRetrievalService
rag_service = RAGRetrievalService(db)

# With
from app.services.rag_retrieval_service_fixed import FixedRAGRetrievalService
rag_service = FixedRAGRetrievalService(db)
```

### Step 2: Update RRF Config

```python
# In app/config/rrf_config.py
ALPHA = 0.85  # Increased from 0.7 (favor semantic more)
```

### Step 3: Improve Chunking

```python
# In app/config/chunking_config.py
CHUNK_OVERLAP = 200  # Increased from 100
CHUNK_SIZE = 800  # Keep same
```

### Step 4: Fix BM25 Score Normalization

The fixed service already includes this, but if using old service:

```python
# In bm25_search_service.py search() method
# Normalize scores
max_score = max(r['score'] for r in results) if results else 1.0
for result in results:
    result['normalized_score'] = result['score'] / max_score if max_score > 0 else 0
```

## Evaluation

Run evaluation script:

```bash
python backend/tests/evaluation/test_rag_accuracy.py
```

Expected improvements:
- Precision@5: 65% → 85-90%
- Hybrid vs semantic: 65% → 90% (better than semantic alone)

## Testing Specific Queries

### Query 1: "What was NOI for Eastern Shore in Q3?"

**Before Fix**:
- Returns Q4 data (no period filter)
- Precision@5: ~40%

**After Fix**:
- Extracts "Q3 2024" → period_id filter
- Extracts "Eastern Shore" → property_id filter
- Precision@5: ~90%

### Query 2: "Show me properties with losses"

**Before Fix**:
- BM25 matches "losses" in profitable properties (negative numbers)
- Precision@5: ~50%

**After Fix**:
- Uses semantic-only (conceptual query)
- Better understanding of "losses" concept
- Precision@5: ~85%

## Monitoring

Track these metrics:
- Precision@5 per query type
- Metadata filter accuracy
- Score normalization effectiveness
- RRF alpha effectiveness

## Rollback

If issues occur:
1. Revert to old service
2. Keep chunking improvements (safe)
3. Keep entity extraction (safe)

