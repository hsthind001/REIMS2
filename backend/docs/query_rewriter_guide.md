# Query Rewriter Guide

## Overview

Query rewriting improves retrieval recall by generating query variations using LLM and domain-specific synonyms. This helps capture relevant documents that use different terminology (e.g., "revenue" vs "income", "DSCR" vs "debt service coverage ratio").

## Architecture

```
User Query
    ↓
[Query Rewriter]
    ├─ LLM (GPT-4o) - Primary
    └─ Synonym Dictionary - Fallback
    ↓
[Generate 3 Variations]
    ├─ Original query
    ├─ Synonym-based variation
    ├─ More specific variation
    └─ More general variation
    ↓
[Search with All Variations]
    ↓
[Combine & Deduplicate Results]
    ↓
[Return Top-K Results]
```

## When to Use Query Rewriting

### Use Query Rewriting When:
- **Recall is important** (need to find all relevant documents)
- **Users phrase questions differently** (synonym variations)
- **Domain-specific terminology** (financial/real estate terms)
- **Initial recall is low** (<70%)
- **Willing to trade precision for recall** (may retrieve more irrelevant results)

### Trade-offs:
- **Recall**: Improves by 15%+ (finds more relevant documents)
- **Precision**: May decrease slightly (more results to filter)
- **Latency**: Adds ~100-500ms per query (LLM generation)
- **Cost**: OpenAI API usage costs

## Configuration

Configuration is managed in `app/config/query_rewriter_config.py`:

```python
from app.config.query_rewriter_config import query_rewriter_config

# LLM Settings
query_rewriter_config.OPENAI_API_KEY = "your-api-key"  # Set via OPENAI_API_KEY env var
query_rewriter_config.OPENAI_MODEL = "gpt-4o"  # Fast, high quality
query_rewriter_config.OPENAI_TEMPERATURE = 0.7
query_rewriter_config.OPENAI_MAX_TOKENS = 200

# Query Variation Settings
query_rewriter_config.NUM_VARIATIONS = 3
query_rewriter_config.TARGET_GENERATION_TIME_MS = 500

# Caching Settings
query_rewriter_config.CACHE_ENABLED = True
query_rewriter_config.CACHE_TTL_HOURS = 24
query_rewriter_config.CACHE_MAX_SIZE = 1000

# Fallback Settings
query_rewriter_config.FALLBACK_TO_ORIGINAL = True
query_rewriter_config.USE_SYNONYM_DICT_ON_FAILURE = True
```

### Environment Variables

```bash
# OpenAI API (uses OPENAI_API_KEY from main config)
export OPENAI_API_KEY="your-api-key"
export QUERY_REWRITER_MODEL="gpt-4o"
export QUERY_REWRITER_TEMPERATURE=0.7

# Query Variation
export QUERY_REWRITER_NUM_VARIATIONS=3
export QUERY_REWRITER_TARGET_TIME_MS=500

# Caching
export QUERY_REWRITER_CACHE_ENABLED="true"
export QUERY_REWRITER_CACHE_TTL_HOURS=24
export QUERY_REWRITER_CACHE_MAX_SIZE=1000

# Fallback
export QUERY_REWRITER_FALLBACK_TO_ORIGINAL="true"
export QUERY_REWRITER_USE_SYNONYM_DICT="true"
```

## Usage

### Basic Query Rewriting

```python
from app.services.query_rewriter_service import QueryRewriterService

# Initialize rewriter
rewriter = QueryRewriterService()

# Rewrite query
result = rewriter.rewrite_query("DSCR below 1.25")

print(f"Original: {result['original_query']}")
print(f"Variations: {result['variations']}")
print(f"Method: {result['method']}")  # 'llm' or 'synonym_dict'
print(f"Cached: {result['cached']}")
print(f"Generation time: {result['generation_time_ms']:.2f}ms")
```

### Integration with RAGRetrievalService

```python
from app.services.rag_retrieval_service import RAGRetrievalService
from app.db.database import SessionLocal

db = SessionLocal()
rag_service = RAGRetrievalService(db)

# Search with query rewriting
results = rag_service.retrieve_relevant_chunks(
    query="DSCR below 1.25",
    top_k=10,
    use_query_rewriting=True  # Enable query rewriting
)

# Results include documents matching all query variations
for result in results:
    print(f"Chunk: {result['chunk_text'][:100]}...")
    print(f"Similarity: {result['similarity']:.4f}")
```

## Rewriting Methods

### LLM-Based Rewriting (Primary)

**Advantages**:
- High-quality variations
- Context-aware
- Handles complex queries
- Natural language generation

**Configuration**:
```python
# Uses GPT-4o by default (fast, high quality)
export QUERY_REWRITER_MODEL="gpt-4o"
```

**Example**:
```python
# Original: "DSCR below 1.25"
# Variations:
# 1. "DSCR below 1.25" (original)
# 2. "debt service coverage ratio below 1.25" (synonym)
# 3. "coverage ratio under threshold" (more general)
```

### Synonym Dictionary Fallback

**Advantages**:
- No API costs
- Fast (no LLM call)
- Works offline
- Predictable results

**Configuration**:
```python
# Synonym dictionary location
export QUERY_REWRITER_SYNONYM_DICT_PATH="app/data/financial_synonyms.json"
```

**Example Synonyms**:
- `revenue` → `income`, `earnings`, `proceeds`
- `DSCR` → `debt service coverage ratio`, `coverage ratio`
- `property` → `asset`, `real estate`, `building`

## Caching

### Cache Behavior

- **Cache Key**: MD5 hash of normalized query (lowercase, stripped)
- **TTL**: 24 hours (configurable)
- **Max Size**: 1000 queries (configurable)
- **Eviction**: FIFO when max size reached

### Cache Management

```python
rewriter = QueryRewriterService()

# Get cache statistics
stats = rewriter.get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Max size: {stats['cache_max_size']}")

# Clear cache
rewriter.clear_cache()
```

## Performance

### Latency Targets

- **LLM Generation**: ~200-500ms (GPT-4o)
- **Synonym Dictionary**: <10ms
- **Cached Lookup**: <1ms
- **Target**: <500ms total generation time

### Recall Improvement

- **Initial Recall@10**: ~70%
- **After Rewriting**: ~85%+
- **Improvement**: +15%+ absolute recall

## Evaluation

### Evaluate Recall Improvement

```bash
# Evaluate query rewriter on test set
python backend/scripts/evaluate_query_rewriter.py \
    --test-queries test_queries.json \
    --top-k 10 \
    --output results.json
```

### Example Evaluation Output

```
============================================================
Query Rewriter Evaluation Results
============================================================
Average Initial Recall@10: 0.7000
Average Rewritten Recall@10: 0.8500
Average Improvement: +0.1500 (+21.43%)
Target Improvement (15%+): ✅ MET
============================================================
```

## Synonym Dictionary

### Adding Synonyms

Edit `backend/app/data/financial_synonyms.json`:

```json
{
  "revenue": ["income", "earnings", "proceeds"],
  "DSCR": ["debt service coverage ratio", "coverage ratio"],
  "property": ["asset", "real estate", "building"]
}
```

### Synonym Format

- **Key**: Term to match (case-insensitive)
- **Value**: List of synonyms
- **Usage**: Automatically used when term appears in query

## Best Practices

1. **Use for Recall-Critical Queries**: Enable when finding all relevant documents is important
2. **Monitor Cache Hit Rate**: Track cache performance to optimize TTL
3. **Evaluate Regularly**: Run evaluation script to measure recall improvement
4. **Update Synonym Dictionary**: Add domain-specific terms as needed
5. **Balance Latency**: Consider caching for common queries
6. **Fallback Strategy**: Always have synonym dictionary as fallback

## Troubleshooting

### Low Recall Improvement

**Possible Causes**:
- Initial recall already very high
- Query variations not diverse enough
- Ground truth quality issues

**Solutions**:
- Check initial recall (should be ~70%)
- Verify LLM is generating diverse variations
- Review synonym dictionary coverage
- Increase NUM_VARIATIONS (e.g., 5 instead of 3)

### High Latency (>500ms)

**Possible Causes**:
- LLM API slow
- Network issues
- Cache not working

**Solutions**:
- Check OpenAI API status
- Enable caching
- Use synonym dictionary fallback
- Reduce NUM_VARIATIONS

### Rewriting Not Working

**Possible Causes**:
- API key not set
- LLM model unavailable
- Synonym dictionary not loaded

**Solutions**:
- Check `OPENAI_API_KEY` environment variable
- Verify rewriter status: `rewriter.get_status()`
- Check synonym dictionary path
- Review logs for errors

## Success Criteria

- ✅ Generates 3 query variations using LLM
- ✅ Maintains original intent
- ✅ Uses domain-specific synonyms
- ✅ Generation time <500ms
- ✅ Falls back to original query if LLM fails
- ✅ Caches variations for common queries
- ✅ Recall improvement: +15%+

## Future Enhancements

- **Adaptive Rewriting**: Only rewrite when initial recall is low
- **Query-Specific Strategies**: Different rewriting for different query types
- **Learning Synonyms**: Extract synonyms from query logs
- **Multi-Language Support**: Rewrite queries in multiple languages
- **User Feedback**: Learn from user clicks to improve variations

