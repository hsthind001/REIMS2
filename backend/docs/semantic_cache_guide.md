# Semantic Cache Guide for NLQ

## Overview

The Semantic Cache Service provides embedding-based similarity matching for Natural Language Queries, enabling the system to match paraphrased questions and achieve >30% cache hit rate. This replaces the previous exact text matching approach (5% hit rate) with cosine similarity matching (>95% threshold).

## Features

- **Semantic Matching**: Uses embeddings to match paraphrased questions
- **Quick Hash Fallback**: Fast exact match via SHA256 hash
- **TTL-Based Expiration**: Configurable cache time-to-live (default 24 hours)
- **Performance Optimized**: <50ms lookup time target
- **Prometheus Metrics**: Comprehensive monitoring and tracking
- **Graceful Degradation**: Falls back to exact match if embedding service unavailable

## Architecture

```
User Question
    ↓
[Generate Embedding] (OpenAI text-embedding-3-large)
    ↓
[Quick Hash Check] → Exact Match? → Return Cached Result
    ↓ (if no exact match)
[Semantic Search] → Check last 100 queries within TTL
    ↓
[Cosine Similarity] → Filter by threshold (≥0.95)
    ↓
[Best Match] → Return if similarity ≥ threshold
    ↓ (if no match)
[Generate New Answer] → Store with embedding
```

## How It Works

### 1. Cache Lookup Strategy

The cache uses a two-tier lookup strategy:

**Tier 1: Quick Hash Check (Fastest)**
- Calculates SHA256 hash of question
- Looks up exact hash match in database
- Returns immediately if found (<5ms typically)

**Tier 2: Semantic Search (If no hash match)**
- Generates embedding for question
- Searches last 100 queries within TTL window
- Calculates cosine similarity for each
- Returns best match if similarity ≥ threshold (default 0.95)

### 2. Cosine Similarity

Cosine similarity measures the angle between two vectors:

```
similarity = (vec1 · vec2) / (||vec1|| × ||vec2||)
```

- **Range**: -1.0 to 1.0 (typically 0.0 to 1.0 for embeddings)
- **1.0**: Identical vectors
- **0.95**: Very similar (paraphrased questions)
- **0.0**: Orthogonal (unrelated)
- **-1.0**: Opposite

### 3. Cache Storage

Every new query is stored with:
- **Question Embedding**: 1536-dimensional vector (text-embedding-3-large)
- **Question Hash**: SHA256 hash for quick exact match
- **Cache Metadata**: `from_cache` flag, `cache_similarity` score

## Configuration

Configuration is managed in `app/config/cache_config.py`:

```python
from app.config.cache_config import cache_config

# Similarity threshold (0.0 to 1.0)
cache_config.SIMILARITY_THRESHOLD = 0.95  # 95% similarity required

# Cache TTL
cache_config.CACHE_TTL_HOURS = 24  # 24 hour cache window

# Performance settings
cache_config.MAX_QUERIES_TO_CHECK = 100  # Limit search space
cache_config.PERFORMANCE_TARGET_MS = 50  # 50ms lookup target

# Feature flag
cache_config.ENABLE_SEMANTIC_CACHE = True  # Enable/disable
```

## Usage

### Basic Usage

The semantic cache is automatically integrated into the NLQ service:

```python
from app.services.nlq_service import NaturalLanguageQueryService
from app.db.database import SessionLocal

db = SessionLocal()
service = NaturalLanguageQueryService(db)

# Query automatically uses semantic cache
result = service.query("What is NOI?", user_id=1)

# Check if result came from cache
if result.get('from_cache'):
    print(f"Cache hit! Similarity: {result.get('cache_similarity')}%")
```

### Direct Cache Service Usage

```python
from app.services.semantic_cache_service import SemanticCacheService

cache_service = SemanticCacheService(db)

# Find similar query
cached = cache_service.find_similar_query(
    question="What's the NOI?",
    user_id=1,
    threshold=0.95
)

if cached:
    print(f"Found cached query: {cached['question']}")
    print(f"Similarity: {cached.get('similarity', 0):.2%}")
```

### Store Query with Embedding

```python
# Store embedding for a query
result = cache_service.store_query_with_embedding(
    query_id=123,
    question="What is NOI?"
)

if result['success']:
    print(f"Embedding stored: {result['embedding_dimension']} dimensions")
```

### Get Cache Statistics

```python
# Get cache statistics
stats = cache_service.get_cache_statistics(hours=24)

print(f"Total queries: {stats['total_queries']}")
print(f"Cached queries: {stats['cached_queries']}")
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Average similarity: {stats['average_similarity']:.2f}%")
```

## Prometheus Metrics

The service exposes the following Prometheus metrics:

### Counters

- **`nlq_cache_hits_total`**: Total number of cache hits
- **`nlq_cache_misses_total`**: Total number of cache misses

### Gauges

- **`nlq_cache_hit_rate`**: Current cache hit rate (0-1)

### Histograms

- **`nlq_cache_lookup_time_seconds`**: Cache lookup latency
- **`nlq_cache_similarity_score`**: Similarity scores of cache hits

### Example PromQL Queries

```promql
# Cache hit rate
rate(nlq_cache_hits_total[1h]) / (rate(nlq_cache_hits_total[1h]) + rate(nlq_cache_misses_total[1h]))

# 95th percentile lookup time
histogram_quantile(0.95, nlq_cache_lookup_time_seconds)

# Average similarity score
histogram_quantile(0.5, nlq_cache_similarity_score)

# Cache hit rate over time
avg_over_time(nlq_cache_hit_rate[1h])
```

## Performance Targets

- **Cache Lookup Time**: <50ms (target)
- **Cache Hit Rate**: >30% (after 1 week)
- **Similarity Threshold**: ≥95% for cache hit
- **Search Space**: Last 100 queries (configurable)

## Tuning Parameters

### Similarity Threshold

**Default**: 0.95 (95%)

**When to Lower**:
- Cache hit rate is too low (<20%)
- Users frequently ask similar questions that don't match
- False negatives (should match but don't)

**When to Raise**:
- Too many false positives (different questions matching)
- Cache returns incorrect answers
- Users complain about stale answers

**Recommended Range**: 0.90 - 0.98

### Cache TTL

**Default**: 24 hours

**When to Increase**:
- Data changes infrequently
- Higher cache hit rate desired
- Storage capacity allows

**When to Decrease**:
- Data changes frequently
- Stale answers are problematic
- Need fresher responses

**Recommended Range**: 1 - 168 hours (1 week)

### Max Queries to Check

**Default**: 100

**When to Increase**:
- More queries in system
- Higher cache hit rate desired
- Performance allows

**When to Decrease**:
- Performance issues
- Lookup time exceeds target
- Database load too high

**Recommended Range**: 50 - 200

## Monitoring

### Key Metrics to Monitor

1. **Cache Hit Rate**: Should be >30% after 1 week
2. **Lookup Time**: Should be <50ms (p95)
3. **Similarity Distribution**: Most hits should be >95%
4. **Cache Size**: Number of queries with embeddings

### Alerts

Set up alerts for:
- Cache hit rate <20% (warning)
- Cache hit rate <10% (critical)
- Lookup time >100ms (warning)
- Lookup time >200ms (critical)
- Embedding generation failures

### Dashboard

Create a dashboard with:
- Cache hit rate over time
- Lookup time distribution
- Similarity score distribution
- Cache size growth
- Hit/miss ratio

## Troubleshooting

### Low Cache Hit Rate (<20%)

**Possible Causes**:
- Similarity threshold too high
- Not enough queries in cache
- Questions too diverse
- TTL too short

**Solutions**:
- Lower similarity threshold (try 0.90)
- Increase TTL
- Check if questions are actually similar
- Monitor for 1 week before adjusting

### High Lookup Time (>50ms)

**Possible Causes**:
- Too many queries to check
- Database query slow
- Embedding generation slow
- Network latency

**Solutions**:
- Reduce MAX_QUERIES_TO_CHECK
- Optimize database indexes
- Check embedding service performance
- Use connection pooling

### False Positives (Wrong Matches)

**Possible Causes**:
- Similarity threshold too low
- Embeddings not accurate
- Questions semantically similar but contextually different

**Solutions**:
- Raise similarity threshold
- Check embedding quality
- Add context filtering (property, period, etc.)

### Embedding Generation Failures

**Possible Causes**:
- OpenAI API key missing/invalid
- API rate limits
- Network issues
- Service unavailable

**Solutions**:
- Verify API key configuration
- Check rate limits
- Implement retry logic
- Fallback to exact match

## Examples

### Example 1: Exact Match

```python
# First query
result1 = service.query("What is NOI?", user_id=1)
# Generates answer and stores with embedding

# Second query (exact same)
result2 = service.query("What is NOI?", user_id=1)
# Cache hit via hash (similarity = 1.0)
```

### Example 2: Paraphrased Match

```python
# First query
result1 = service.query("What is the Net Operating Income?", user_id=1)
# Generates answer and stores with embedding

# Second query (paraphrased)
result2 = service.query("What's the NOI?", user_id=1)
# Cache hit via semantic similarity (similarity ≈ 0.96)
```

### Example 3: No Match

```python
# First query
result1 = service.query("What is NOI?", user_id=1)

# Second query (different question)
result2 = service.query("What is revenue?", user_id=1)
# Cache miss (similarity < 0.95)
# Generates new answer
```

## Best Practices

1. **Monitor Hit Rate**: Track cache hit rate weekly and adjust threshold
2. **Tune Threshold**: Start with 0.95, adjust based on results
3. **Set Appropriate TTL**: Balance freshness vs. hit rate
4. **Monitor Performance**: Ensure lookup time stays <50ms
5. **Track Similarity Scores**: Most hits should be >95%
6. **Handle Failures Gracefully**: Always fallback to exact match or generate new answer

## Migration

### Running Database Migration

```bash
cd backend
alembic upgrade head
```

This adds:
- `question_embedding` column (FLOAT[])
- `question_hash` column (VARCHAR(64))
- `from_cache` column (BOOLEAN)
- `cache_similarity` column (DECIMAL(5,2))
- Indexes for performance

### Backfilling Embeddings

To add embeddings to existing queries:

```python
from app.services.semantic_cache_service import SemanticCacheService
from app.db.database import SessionLocal
from app.models.nlq_query import NLQQuery

db = SessionLocal()
cache_service = SemanticCacheService(db)

# Get queries without embeddings
queries = db.query(NLQQuery).filter(
    NLQQuery.question_embedding.is_(None)
).all()

for query in queries:
    cache_service.store_query_with_embedding(
        query_id=query.id,
        question=query.question
    )
```

## Success Criteria

- ✅ Cache matches queries with >95% cosine similarity
- ✅ Cache TTL configurable (default 24 hours)
- ✅ Query embeddings stored in nlq_queries table
- ✅ Cache hit rate >30% after 1 week
- ✅ Cache lookup time <50ms
- ✅ Graceful degradation if cache unavailable
- ✅ Prometheus metrics for monitoring

## Future Enhancements

- User-specific cache filtering
- Context-aware caching (property, period)
- Cache warming strategies
- Adaptive threshold based on query patterns
- Multi-level caching (memory + database)

