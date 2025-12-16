# Component Integration Guide: SemanticCacheService + NLQService

## Overview

This guide documents the integration between **SemanticCacheService** (Component A) and **NaturalLanguageQueryService** (Component B) in the REIMS2 NLQ/RAG system.

## Integration Requirements

✅ **Requirement 1**: Component A called before Component B  
✅ **Requirement 2**: If Component A returns cached result, skip Component B  
✅ **Requirement 3**: Component B updates Component A cache on new queries  
✅ **Requirement 4**: Error in Component A should not block Component B (graceful degradation)  
✅ **Requirement 5**: Metrics for cache hit/miss rate  

## Architecture

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  IntegratedNLQService           │
│                                 │
│  1. Check Cache (Component A)   │
│     ├─ Cache Hit? → Return     │
│     └─ Cache Miss? → Continue  │
│                                 │
│  2. Call NLQ (Component B)     │
│     └─ Process Query            │
│                                 │
│  3. Update Cache (Component A)  │
│     └─ Store Embedding          │
└─────────────────────────────────┘
```

## Usage

### Basic Usage

```python
from app.services.nlq_service_integrated import IntegratedNLQService
from sqlalchemy.orm import Session

# Initialize
service = IntegratedNLQService(db)

# Query with automatic caching
result = service.query(
    question="What was NOI for Eastern Shore in Q3 2024?",
    user_id=1,
    context={
        'property_id': 1,
        'property_code': 'ESP001',
        'property_name': 'Eastern Shore Plaza'
    }
)

# Check if result was from cache
if result.get('from_cache'):
    print(f"Cache hit! Similarity: {result.get('cache_similarity')}")
else:
    print("Cache miss - new query processed")
```

### API Integration

```python
# In your FastAPI endpoint
from app.services.nlq_service_integrated import IntegratedNLQService

@router.post("/nlq/query")
def query_nlq(
    request: NLQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = IntegratedNLQService(db)
    result = service.query(
        question=request.question,
        user_id=current_user.id,
        context=request.context
    )
    return result
```

## Integration Flow

### Flow 1: Cache Hit (Fast Path)

```
1. User Query: "What was NOI?"
   ↓
2. Component A: find_similar_query()
   ├─ Exact match? → Return cached result ✅
   └─ Semantic match? → Return cached result ✅
   ↓
3. Skip Component B (NLQ Service) ⏭️
   ↓
4. Return cached result
   - Latency: ~50ms (cache lookup only)
```

### Flow 2: Cache Miss (Full Path)

```
1. User Query: "What was NOI?"
   ↓
2. Component A: find_similar_query()
   └─ No match found ❌
   ↓
3. Component B: query()
   ├─ Intent Detection
   ├─ Data Retrieval
   ├─ Answer Generation
   └─ Store Query
   ↓
4. Component A: store_query_with_embedding()
   └─ Store for future cache hits
   ↓
5. Return new result
   - Latency: ~2-5s (full processing)
```

### Flow 3: Cache Error (Graceful Degradation)

```
1. User Query: "What was NOI?"
   ↓
2. Component A: find_similar_query()
   └─ Exception: "Database connection error" ⚠️
   ↓
3. Log warning, continue to Component B
   ↓
4. Component B: query()
   └─ Process normally ✅
   ↓
5. Try to update cache (non-critical)
   └─ If fails, log warning but don't break
   ↓
6. Return result
   - Latency: ~2-5s (full processing)
   - Status: Success (degraded mode)
```

## Error Handling

### Component A Errors

**Scenario**: Cache service unavailable or throws exception

**Handling**:
```python
try:
    cached_result = self.cache_service.find_similar_query(...)
except Exception as e:
    # Graceful degradation: Continue to Component B
    logger.warning(f"Cache lookup failed: {e}. Proceeding with NLQ service.")
    cached_result = None
```

**Result**: Query still processes successfully, just without caching

### Component B Errors

**Scenario**: NLQ service fails

**Handling**:
```python
try:
    nlq_result = self.nlq_service.query(...)
except Exception as e:
    # Return error response
    return {
        "success": False,
        "error": str(e),
        "from_cache": False
    }
```

**Result**: Error returned to user (Component B is critical)

### Cache Update Errors

**Scenario**: Cache update fails after successful query

**Handling**:
```python
try:
    self.cache_service.store_query_with_embedding(...)
except Exception as e:
    # Non-critical: Log warning but don't break
    logger.warning(f"Cache update failed (non-critical): {e}")
```

**Result**: Query succeeds, but won't be cached for future use

## Metrics

### Prometheus Metrics

The integration exposes the following metrics:

```python
# Counters
nlq_integration_cache_hits_total      # Total cache hits
nlq_integration_cache_misses_total    # Total cache misses
nlq_integration_cache_error_total     # Total cache errors
nlq_integration_total_queries         # Total queries processed

# Gauges
nlq_integration_cache_hit_rate       # Current hit rate (0-1)

# Histograms
nlq_integration_query_latency_seconds # Query latency distribution
```

### Accessing Metrics

```python
# Get statistics
stats = service.get_cache_statistics(hours=24)

# Returns:
{
    'integration_stats': {
        'total_queries': 1000,
        'cache_hits': 350,
        'cache_misses': 650,
        'cache_errors': 5,
        'hit_rate': 0.35
    },
    'component_a_stats': {
        'total_queries': 1000,
        'cached_queries': 350,
        'hit_rate': 0.35,
        'average_similarity': 0.92
    }
}
```

### Health Status

```python
health = service.get_health_status()

# Returns:
{
    'component_a': {
        'name': 'SemanticCacheService',
        'available': True,
        'enabled': True
    },
    'component_b': {
        'name': 'NaturalLanguageQueryService',
        'available': True
    },
    'integration': {
        'status': 'healthy',
        'graceful_degradation': True
    }
}
```

## Configuration

### Enable/Disable Cache

```python
# In app/config/cache_config.py
ENABLE_SEMANTIC_CACHE = True  # Set to False to disable
```

### Cache Parameters

```python
# In app/config/cache_config.py
SIMILARITY_THRESHOLD = 0.95  # Minimum similarity for cache hit
CACHE_TTL_HOURS = 24         # Cache expiration time
MAX_QUERIES_TO_CHECK = 100   # Max queries to check for similarity
```

## Testing

### Unit Tests

```bash
# Run integration tests
pytest backend/tests/services/test_nlq_integration.py -v
```

### Test Scenarios

1. **Cache Hit**: Verify Component B is skipped
2. **Cache Miss**: Verify Component B is called
3. **Cache Update**: Verify new queries update cache
4. **Graceful Degradation**: Verify cache errors don't block queries
5. **Metrics**: Verify metrics are recorded correctly

## Performance

### Expected Latencies

- **Cache Hit**: 50-100ms (cache lookup only)
- **Cache Miss**: 2-5s (full NLQ processing)
- **Cache Error**: 2-5s (full processing, degraded mode)

### Cache Hit Rate Targets

- **Target**: >30% after 1 week of production use
- **Current**: Monitor via `nlq_integration_cache_hit_rate` metric

## Troubleshooting

### Issue: Low Cache Hit Rate

**Possible Causes**:
- Queries are too diverse
- Similarity threshold too high
- Cache TTL too short

**Solutions**:
- Lower `SIMILARITY_THRESHOLD` (e.g., 0.90)
- Increase `CACHE_TTL_HOURS`
- Review query patterns

### Issue: Cache Errors

**Possible Causes**:
- Database connection issues
- Embedding service unavailable
- Cache service initialization failed

**Solutions**:
- Check database connectivity
- Verify embedding service is running
- Review logs for initialization errors

### Issue: Component B Not Called

**Possible Causes**:
- Cache always returning results (even for new queries)
- Similarity threshold too low

**Solutions**:
- Check cache similarity scores
- Review cache lookup logic
- Verify cache TTL is correct

## Migration from Old Service

### Step 1: Update Imports

```python
# Old
from app.services.nlq_service import NaturalLanguageQueryService
service = NaturalLanguageQueryService(db)

# New
from app.services.nlq_service_integrated import IntegratedNLQService
service = IntegratedNLQService(db)
```

### Step 2: Update API Endpoints

```python
# In app/api/v1/nlq.py
from app.services.nlq_service_integrated import IntegratedNLQService

@router.post("/nlq/query")
def natural_language_query(...):
    service = IntegratedNLQService(db)  # Changed
    result = service.query(...)
    return result
```

### Step 3: Monitor Metrics

- Check cache hit rate after deployment
- Monitor error rates
- Verify graceful degradation works

## Best Practices

1. **Always use IntegratedNLQService** for new code
2. **Monitor cache hit rate** via Prometheus
3. **Set up alerts** for high cache error rates
4. **Review cache statistics** weekly
5. **Tune similarity threshold** based on query patterns

## Example: Complete Integration

```python
from app.services.nlq_service_integrated import IntegratedNLQService
from sqlalchemy.orm import Session

def process_nlq_query(db: Session, question: str, user_id: int):
    """Process NLQ query with integrated caching"""
    
    # Initialize service
    service = IntegratedNLQService(db)
    
    # Check health
    health = service.get_health_status()
    if health['integration']['status'] != 'healthy':
        logger.warning(f"Service degraded: {health}")
    
    # Process query
    result = service.query(
        question=question,
        user_id=user_id,
        context={'property_id': 1}
    )
    
    # Log cache status
    if result.get('from_cache'):
        logger.info(f"Cache hit: {result.get('cache_similarity')}")
    else:
        logger.info("Cache miss - new query processed")
    
    # Get statistics
    stats = service.get_cache_statistics(hours=24)
    logger.info(f"Cache hit rate: {stats['integration_stats']['hit_rate']:.2%}")
    
    return result
```

