# Performance Debugging Guide

## Quick Diagnosis

### Step 1: Identify the Bottleneck

```python
# Add timing to your retrieval call
import time

start = time.time()
results = rag_service.retrieve_relevant_chunks(
    query="What was NOI for Q3?",
    top_k=10,
    use_bm25=True
)
elapsed = time.time() - start

print(f"Total time: {elapsed:.3f}s")
print(f"Results: {len(results)}")
```

### Step 2: Check Database Queries

Enable SQLAlchemy query logging:

```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

Look for:
- Multiple queries per chunk (N+1 problem)
- Full table scans
- Missing indexes

### Step 3: Profile with cProfile

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

results = rag_service.retrieve_relevant_chunks(...)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

## Common Issues and Fixes

### Issue 1: N+1 Queries

**Symptom**: 50+ database queries for 10 results

**Fix**: Use batch enrichment (see optimized service)

```python
# Before (N+1 problem)
for chunk_id in chunk_ids:
    chunk = db.query(DocumentChunk).filter(...).first()
    document = db.query(DocumentUpload).filter(...).first()
    property = db.query(Property).filter(...).first()

# After (batch enrichment)
chunks = db.query(DocumentChunk)\
    .options(joinedload(DocumentChunk.document),
             joinedload(DocumentChunk.property))\
    .filter(DocumentChunk.id.in_(chunk_ids))\
    .all()
```

### Issue 2: Full Table Scan

**Symptom**: Loading all 50,000 chunks into memory

**Fix**: Use pgvector or limit query

```python
# Before (loads all chunks)
chunks = db.query(DocumentChunk).filter(...).all()
for chunk in chunks:
    similarity = cosine_similarity(query_embedding, chunk.embedding)

# After (pgvector - fast)
result = db.execute(text("""
    SELECT id, 1 - (embedding_vector <=> :embedding::vector) as similarity
    FROM document_chunks
    WHERE ...
    ORDER BY embedding_vector <=> :embedding::vector
    LIMIT :top_k
"""), {'embedding': query_embedding, 'top_k': top_k})
```

### Issue 3: Missing Indexes

**Symptom**: Slow queries even with filters

**Fix**: Add indexes (see migration file)

```sql
CREATE INDEX idx_document_chunks_property_id ON document_chunks(property_id);
CREATE INDEX idx_document_chunks_period_id ON document_chunks(period_id);
CREATE INDEX idx_document_chunks_document_type ON document_chunks(document_type);
```

### Issue 4: Sequential Hybrid Search

**Symptom**: Hybrid search takes sum of BM25 + semantic time

**Fix**: Use parallel execution

```python
# Before (sequential)
bm25_results = self._retrieve_with_bm25(...)  # 1s
semantic_results = self._retrieve_with_pinecone(...)  # 2s
# Total: 3s

# After (parallel)
with ThreadPoolExecutor(max_workers=2) as executor:
    bm25_future = executor.submit(self._retrieve_with_bm25, ...)
    semantic_future = executor.submit(self._retrieve_with_pinecone, ...)
    bm25_results = bm25_future.result()
    semantic_results = semantic_future.result()
# Total: max(1s, 2s) = 2s
```

## Monitoring

### Prometheus Metrics

```python
# Query latency by method
rag_retrieval_latency_seconds{method="hybrid", has_filters="True"}

# Query count
rag_retrieval_queries_total{method="hybrid", status="success"}

# Cache hit rate
rate(rag_cache_hits_total[5m]) / 
(rate(rag_cache_hits_total[5m]) + rate(rag_cache_misses_total[5m]))
```

### Grafana Dashboard

Create dashboard with:
- Average latency by method
- P95/P99 latency
- Query rate
- Cache hit rate
- Error rate

## Performance Targets

| Operation | Target | Current (Before) | After Optimization |
|-----------|--------|-----------------|-------------------|
| Hybrid Search | <2s | 5-6s | 0.8-1.2s |
| Semantic Search | <1s | 3-4s | 0.3-0.5s |
| BM25 Search | <0.5s | 1-2s | 0.2-0.3s |
| Enrichment | <0.1s | 2-3s | 0.05-0.1s |

## Testing Performance

```python
import time
import statistics

def benchmark_retrieval(rag_service, query, iterations=10):
    """Benchmark retrieval performance."""
    times = []
    
    for _ in range(iterations):
        start = time.time()
        results = rag_service.retrieve_relevant_chunks(query, top_k=10)
        elapsed = time.time() - start
        times.append(elapsed)
    
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'p95': statistics.quantiles(times, n=20)[18],  # 95th percentile
        'p99': statistics.quantiles(times, n=100)[98],  # 99th percentile
        'min': min(times),
        'max': max(times)
    }

# Run benchmark
stats = benchmark_retrieval(rag_service, "What was NOI for Q3?")
print(f"Mean: {stats['mean']:.3f}s")
print(f"P95: {stats['p95']:.3f}s")
```

## Regression Prevention

1. **Add Performance Tests**: Include in CI/CD
2. **Set Alerts**: Alert if P95 latency > 2s
3. **Monitor Trends**: Track latency over time
4. **Load Testing**: Test with production-like data volume

