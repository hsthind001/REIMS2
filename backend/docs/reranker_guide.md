# Cross-Encoder Reranker Guide

## Overview

Cross-encoder reranking improves retrieval precision from ~85% to >90% by reranking initial search results using advanced neural models. The reranker uses Cohere Rerank API as the primary method, with sentence-transformers as a fallback.

## Architecture

```
Initial Retrieval (Hybrid Search)
    ↓
[Get Top 50 Candidates]
    ↓
[Cross-Encoder Reranking]
    ├─ Cohere Rerank API (Primary)
    └─ sentence-transformers (Fallback)
    ↓
[Return Top-K Reranked Results]
```

## When to Use Reranking

### Use Reranking When:
- **High precision required** (>90% precision@5)
- **Initial retrieval gets ~85% precision** (needs improvement)
- **Quality over speed** (acceptable to trade ~100ms for better results)
- **Top-k results are critical** (e.g., top 5-10 results)

### Trade-offs:
- **Latency**: Adds ~100-200ms per query
- **Cost**: Cohere API has usage costs
- **Precision**: Improves from ~85% to >90%

## Configuration

Configuration is managed in `app/config/reranker_config.py`:

```python
from app.config.reranker_config import reranker_config

# Cohere API Settings
reranker_config.COHERE_API_KEY = "your-api-key"  # Set via COHERE_API_KEY env var
reranker_config.COHERE_MODEL = "rerank-english-v3.0"  # or rerank-multilingual-v3.0
reranker_config.COHERE_TOP_N = 50  # Number of candidates to rerank

# Fallback Settings
reranker_config.FALLBACK_MODEL = "cross-encoder/ms-marco-MiniLM-L-12-v2"
reranker_config.FALLBACK_DEVICE = "cpu"  # or "cuda"

# Reranking Parameters
reranker_config.RERANK_TOP_N = 50  # Rerank top 50 from initial retrieval
reranker_config.RERANK_TOP_K = 10  # Return top 10 after reranking
reranker_config.RERANK_ENABLED = True

# Performance
reranker_config.TARGET_LATENCY_MS = 200  # Target <200ms
```

### Environment Variables

```bash
# Cohere API
export COHERE_API_KEY="your-api-key"
export COHERE_RERANK_MODEL="rerank-english-v3.0"

# Fallback
export RERANKER_FALLBACK_MODEL="cross-encoder/ms-marco-MiniLM-L-12-v2"
export RERANKER_FALLBACK_DEVICE="cpu"

# Configuration
export RERANKER_ENABLED="true"
export RERANKER_TOP_N=50
export RERANKER_TOP_K=10
export RERANKER_TARGET_LATENCY_MS=200
```

## Usage

### Basic Reranking

```python
from app.services.reranker_service import RerankerService

# Initialize reranker
reranker = RerankerService()

# Initial search results (from hybrid search, RRF, etc.)
initial_results = [
    {'chunk_id': 1, 'chunk_text': 'DSCR is 1.20, below threshold', 'similarity': 0.9},
    {'chunk_id': 2, 'chunk_text': 'Debt service coverage analysis', 'similarity': 0.8},
    # ... more results
]

# Rerank results
reranked_results = reranker.rerank(
    query="DSCR below 1.25",
    candidates=initial_results,
    top_k=10
)

for result in reranked_results:
    print(f"Rerank Score: {result['rerank_score']}")
    print(f"Rerank Rank: {result['rerank_rank']}")
    print(f"Method: {result['rerank_method']}")
    print(f"Text: {result['chunk_text'][:200]}...")
```

### Integration with RAGRetrievalService

```python
from app.services.rag_retrieval_service import RAGRetrievalService
from app.db.database import SessionLocal

db = SessionLocal()
rag_service = RAGRetrievalService(db)

# Search with reranking
results = rag_service.retrieve_relevant_chunks(
    query="DSCR below 1.25",
    top_k=10,
    use_rrf=True,  # Use RRF fusion
    use_reranker=True,  # Enable reranking
    rerank_top_n=50  # Rerank top 50 candidates
)

# Results are automatically reranked
for result in results:
    if 'rerank_score' in result:
        print(f"Reranked: {result['rerank_score']}")
    else:
        print(f"Original: {result['similarity']}")
```

## Reranking Methods

### Cohere Rerank API (Primary)

**Advantages**:
- State-of-the-art performance
- Handles multilingual queries
- No local model loading
- Fast API response

**Configuration**:
```python
# Set API key
export COHERE_API_KEY="your-api-key"

# Choose model
export COHERE_RERANK_MODEL="rerank-english-v3.0"  # English
# or
export COHERE_RERANK_MODEL="rerank-multilingual-v3.0"  # Multilingual
```

**Usage**:
```python
reranker = RerankerService()
# Automatically uses Cohere if API key is set
reranked = reranker.rerank(query, candidates, top_k=10)
```

### Sentence-Transformers Fallback

**Advantages**:
- No API costs
- Works offline
- Fast inference on GPU

**Configuration**:
```python
export RERANKER_FALLBACK_MODEL="cross-encoder/ms-marco-MiniLM-L-12-v2"
export RERANKER_FALLBACK_DEVICE="cuda"  # Use GPU if available
```

**Usage**:
```python
# Automatically used if Cohere unavailable
reranker = RerankerService()
# Falls back to sentence-transformers if Cohere fails
reranked = reranker.rerank(query, candidates, top_k=10)
```

## Performance

### Latency Targets

- **Cohere API**: ~100-150ms for 50 candidates
- **sentence-transformers**: ~50-100ms for 50 candidates (CPU), ~20-50ms (GPU)
- **Target**: <200ms total reranking latency

### Precision Improvement

- **Initial Precision@5**: ~85%
- **After Reranking**: >90%
- **Improvement**: +5-10% absolute precision

## Evaluation

### Evaluate Precision Improvement

```bash
# Evaluate reranker on test set
python backend/scripts/evaluate_reranker.py \
    --test-queries test_queries.json \
    --top-k 5 \
    --output results.json
```

### Example Evaluation Output

```
============================================================
Reranker Evaluation Results
============================================================
Average Initial Precision@5: 0.8500
Average Reranked Precision@5: 0.9200
Average Improvement: +0.0700 (+8.24%)
Target Precision (90%): ✅ MET
============================================================
```

## Error Handling

### Automatic Fallback

The reranker automatically falls back to sentence-transformers if:
- Cohere API key is not set
- Cohere API call fails
- Cohere API times out

### Return Original Results

If both methods fail and `RETURN_ORIGINAL_ON_FAILURE=true`:
- Returns original results (limited to top_k)
- Logs warning
- Does not raise exception

### Configuration

```python
# Enable fallback on error
export RERANKER_FALLBACK_ON_ERROR="true"

# Return original results on failure
export RERANKER_RETURN_ORIGINAL_ON_FAILURE="true"
```

## Best Practices

1. **Use Reranking for Critical Queries**: Enable for queries where precision is important
2. **Limit Candidates**: Rerank top 50, not all results (performance)
3. **Monitor Latency**: Track reranking latency to ensure <200ms target
4. **Evaluate Regularly**: Run evaluation script to measure precision improvement
5. **Fallback Strategy**: Always have fallback enabled for reliability
6. **Cost Management**: Monitor Cohere API usage if using paid tier

## Troubleshooting

### Low Precision Improvement

**Possible Causes**:
- Initial retrieval already very good
- Reranker model not suitable for domain
- Ground truth quality issues

**Solutions**:
- Check initial precision (should be ~85%)
- Try different reranker models
- Verify ground truth quality
- Increase rerank_top_n (e.g., 100 instead of 50)

### High Latency (>200ms)

**Possible Causes**:
- Too many candidates
- Slow API response
- CPU inference (fallback)

**Solutions**:
- Reduce rerank_top_n (e.g., 30 instead of 50)
- Use GPU for fallback model
- Check Cohere API status
- Optimize batch size

### Reranking Not Working

**Possible Causes**:
- API key not set
- Model not loaded
- Reranking disabled

**Solutions**:
- Check `COHERE_API_KEY` environment variable
- Verify reranker status: `reranker.get_status()`
- Check `RERANKER_ENABLED` configuration
- Review logs for errors

## Success Criteria

- ✅ Reranks top 50 candidates using cross-encoder
- ✅ Uses Cohere Rerank API (primary) or sentence-transformers (fallback)
- ✅ Reranking latency <200ms for 50 candidates
- ✅ Fallback to original ranking if reranker fails
- ✅ Precision@5 improvement: 85% → 90%+

## Future Enhancements

- **Adaptive Reranking**: Only rerank when initial precision is low
- **Query-Specific Models**: Different models for different query types
- **Batch Reranking**: Rerank multiple queries in parallel
- **Caching**: Cache rerank results for identical queries
- **Learning to Rank**: Train custom reranker on domain data

