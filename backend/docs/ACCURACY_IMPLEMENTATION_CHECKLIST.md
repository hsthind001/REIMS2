# Accuracy Fix Implementation Checklist

## Pre-Implementation

- [ ] Review current precision@5 metrics
- [ ] Identify worst-performing queries
- [ ] Backup current service code
- [ ] Set up evaluation environment

## Implementation

### Phase 1: Core Fixes (15 minutes)

- [ ] **Replace Service**
  ```python
  # Change import
  from app.services.rag_retrieval_service_fixed import FixedRAGRetrievalService
  rag_service = FixedRAGRetrievalService(db)
  ```

- [ ] **Update RRF Config**
  ```python
  # In app/config/rrf_config.py
  ALPHA = 0.85  # Changed from 0.7
  ```

- [ ] **Test Basic Functionality**
  ```python
  results = rag_service.retrieve_relevant_chunks(
      query="What was NOI for Eastern Shore in Q3?",
      top_k=5
  )
  assert len(results) > 0
  ```

### Phase 2: BM25 Fixes (10 minutes)

- [ ] **Use Fixed BM25 Service** (if using BM25 directly)
  ```python
  from app.services.bm25_search_service_fixed import FixedBM25SearchService
  bm25_service = FixedBM25SearchService(db)
  ```

- [ ] **Verify Score Normalization**
  ```python
  results = bm25_service.search("NOI", top_k=5)
  # Check that scores are 0-1 range
  assert all(0 <= r['score'] <= 1 for r in results)
  ```

### Phase 3: Chunking Improvements (30 minutes)

- [ ] **Update Chunking Config**
  ```python
  # In app/config/chunking_config.py
  CHUNK_OVERLAP = 200  # Increased from 100
  ```

- [ ] **Re-chunk Documents** (optional, for new documents)
  ```python
  # Re-process documents with new overlap
  # Only needed for new documents or if re-indexing
  ```

### Phase 4: Evaluation (20 minutes)

- [ ] **Run Evaluation Script**
  ```bash
  python backend/tests/evaluation/test_rag_accuracy.py
  ```

- [ ] **Verify Improvements**
  - Precision@5 > 85%
  - Hybrid > semantic alone
  - Time period accuracy > 90%

- [ ] **Test Specific Queries**
  - "What was NOI for Eastern Shore in Q3?" → Should return Q3 data
  - "Show me properties with losses" → Should return loss-making properties

## Post-Implementation

### Monitoring

- [ ] **Set Up Metrics**
  - Track precision@5 per query type
  - Monitor metadata filter accuracy
  - Track score normalization

- [ ] **Set Up Alerts**
  - Alert if precision@5 < 80%
  - Alert if hybrid < semantic

### Tuning

- [ ] **Tune RRF Alpha**
  - Test different alpha values (0.75, 0.80, 0.85, 0.90)
  - Use adaptive alpha for best results

- [ ] **Tune Chunking**
  - Test overlap values (150, 200, 250)
  - Measure context preservation

### Documentation

- [ ] **Update API Docs**
  - Document entity extraction
  - Document adaptive alpha
  - Document score normalization

- [ ] **Update User Guide**
  - Explain query improvements
  - Show examples of better results

## Verification Tests

### Test 1: Time Period Extraction
```python
query = "What was NOI for Eastern Shore in Q3 2024?"
results = rag_service.retrieve_relevant_chunks(query, top_k=5)

# Verify all results are Q3 2024
for result in results:
    assert result['period'] == "2024-07" or result['period'] == "2024-08" or result['period'] == "2024-09"
```

### Test 2: Property Extraction
```python
query = "What was NOI for Eastern Shore Plaza?"
results = rag_service.retrieve_relevant_chunks(query, top_k=5)

# Verify all results are Eastern Shore
for result in results:
    assert "Eastern Shore" in result.get('property_name', '')
```

### Test 3: Score Normalization
```python
results = rag_service.retrieve_relevant_chunks(
    query="NOI",
    top_k=10,
    use_bm25=True,
    use_rrf=True
)

# Verify scores are normalized
for result in results:
    assert 0 <= result.get('similarity', 0) <= 1
    if 'bm25_score' in result:
        assert 0 <= result['bm25_score'] <= 1
```

### Test 4: Hybrid vs Semantic
```python
# Semantic only
semantic_results = rag_service.retrieve_relevant_chunks(
    query="NOI",
    top_k=5,
    use_bm25=False
)

# Hybrid
hybrid_results = rag_service.retrieve_relevant_chunks(
    query="NOI",
    top_k=5,
    use_bm25=True,
    use_rrf=True
)

# Hybrid should have equal or better precision
# (assuming ground truth available)
```

## Success Metrics

- [ ] Precision@5 > 85% (target: >90%)
- [ ] Hybrid precision > semantic precision
- [ ] Time period accuracy > 90%
- [ ] Property accuracy > 85%
- [ ] No regression in semantic-only queries

## Rollback Plan

If issues occur:

1. **Immediate Rollback**
   ```python
   # Revert to old service
   from app.services.rag_retrieval_service import RAGRetrievalService
   rag_service = RAGRetrievalService(db)
   ```

2. **Partial Rollback**
   - Keep entity extraction (safe)
   - Keep chunking improvements (safe)
   - Revert RRF alpha if needed

3. **Investigation**
   - Check evaluation results
   - Review diagnostic reports
   - Identify specific failing queries

## Support

For issues:
1. Check `ACCURACY_ISSUES_ANALYSIS.md` for root causes
2. Run diagnostic script
3. Review evaluation results
4. Check logs for entity extraction

