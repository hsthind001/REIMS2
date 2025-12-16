# Performance Fix Implementation Guide

## Executive Summary

**Problem**: Hybrid search queries taking 5+ seconds (target: <2s)  
**Root Causes**: N+1 queries, full table scans, no caching, sequential execution  
**Solution**: Batch enrichment, pgvector, parallel execution, caching  
**Expected Improvement**: 80-90% reduction (5-6s → 0.8-1.2s)

## Implementation Steps

### Step 1: Add Database Indexes (5 minutes, Immediate 50-70% improvement)

```bash
# Run migration
psql -U postgres -d reims -f backend/migrations/add_performance_indexes.sql
```

**Impact**: Reduces query time from 3-4s to 1-2s

### Step 2: Replace Service with Optimized Version (15 minutes)

```python
# In your NLQ service or API endpoint
from app.services.rag_retrieval_service_optimized import OptimizedRAGRetrievalService

# Replace
# rag_service = RAGRetrievalService(db)
# With
rag_service = OptimizedRAGRetrievalService(db)
```

**Impact**: Eliminates N+1 queries, reduces enrichment from 2-3s to 0.05-0.1s

### Step 3: Add pgvector Extension (Optional, 30 minutes, 90% improvement)

**Prerequisites**: Install pgvector extension

```bash
# Install pgvector (Ubuntu/Debian)
sudo apt-get install postgresql-14-pgvector

# Or compile from source
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**Run Migration**:
```bash
psql -U postgres -d reims -f backend/migrations/add_pgvector_extension.sql
```

**Impact**: Reduces PostgreSQL semantic search from 3-4s to 0.2-0.3s

### Step 4: Add Performance Monitoring (10 minutes)

```python
# In your main.py or service initialization
from app.monitoring.performance_monitoring import track_retrieval_performance

# Decorate retrieval methods
@track_retrieval_performance(method='hybrid')
def retrieve_relevant_chunks(self, ...):
    ...
```

**Impact**: Enables monitoring and alerting

### Step 5: Configure Redis for Caching (Optional, 10 minutes)

```bash
# Install Redis (if not already installed)
sudo apt-get install redis-server

# Update .env
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Impact**: 30% improvement for repeated queries

## Code Changes Summary

### Files Created
1. `backend/app/services/rag_retrieval_service_optimized.py` - Optimized service
2. `backend/migrations/add_performance_indexes.sql` - Database indexes
3. `backend/migrations/add_pgvector_extension.sql` - pgvector setup
4. `backend/app/monitoring/performance_monitoring.py` - Performance tracking
5. `backend/docs/performance_optimization_guide.md` - Detailed guide
6. `backend/docs/PERFORMANCE_DEBUGGING.md` - Debugging guide

### Files to Modify
1. **NLQ Service** (`backend/app/services/nlq_service.py`):
   ```python
   # Change import
   from app.services.rag_retrieval_service_optimized import OptimizedRAGRetrievalService as RAGRetrievalService
   ```

2. **API Endpoint** (if using directly):
   ```python
   from app.services.rag_retrieval_service_optimized import OptimizedRAGRetrievalService
   ```

## Performance Comparison

### Before Optimization
```
Hybrid Search Flow:
├─ BM25 Search: 1-2s
│  └─ Enrichment: 0.5s (N+1 queries)
├─ Semantic Search: 3-4s
│  ├─ Load all chunks: 2s
│  └─ Enrichment: 1s (N+1 queries)
└─ Total: 5-6s
```

### After Optimization
```
Hybrid Search Flow (Parallel):
├─ BM25 Search: 0.2-0.3s (parallel)
│  └─ Batch Enrichment: 0.05s
├─ Semantic Search: 0.3-0.5s (parallel, pgvector)
│  └─ Batch Enrichment: 0.05s
└─ Total: 0.8-1.2s (80% improvement)
```

## Verification

### Test Performance
```python
import time

# Test query
query = "What was NOI for Eastern Shore in Q3 2024?"

# Before
start = time.time()
results_old = old_service.retrieve_relevant_chunks(query, top_k=10, use_bm25=True)
time_old = time.time() - start

# After
start = time.time()
results_new = new_service.retrieve_relevant_chunks(query, top_k=10, use_bm25=True)
time_new = time.time() - start

print(f"Before: {time_old:.3f}s")
print(f"After: {time_new:.3f}s")
print(f"Improvement: {(1 - time_new/time_old) * 100:.1f}%")
```

### Check Database Queries
```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Run query and count SQL statements
# Should see: 1-2 queries instead of 80+
```

## Rollback Plan

If issues occur:

1. **Revert Service**: Change import back to original
2. **Keep Indexes**: They won't hurt, only help
3. **Disable pgvector**: Service falls back to Python calculation

## Monitoring

### Key Metrics to Track

1. **Latency**:
   - P50 (median): Should be <1s
   - P95: Should be <2s
   - P99: Should be <3s

2. **Query Count**:
   - Should be 1-2 queries per retrieval
   - Not 50-80 queries

3. **Cache Hit Rate**:
   - Target: >30% for repeated queries

### Alerts

Set up alerts for:
- P95 latency > 2s
- Error rate > 5%
- Query count > 10 per retrieval

## Troubleshooting

### Issue: Still slow after optimization

1. **Check indexes**: `\d+ document_chunks` in psql
2. **Check pgvector**: `SELECT * FROM pg_extension WHERE extname = 'vector'`
3. **Check query count**: Enable SQL logging
4. **Check cache**: Redis connection

### Issue: Errors after migration

1. **pgvector not installed**: Service falls back to Python
2. **Missing columns**: Check migration ran successfully
3. **Redis connection**: Service works without cache

## Next Steps

1. **Immediate** (Today):
   - Add database indexes
   - Deploy optimized service
   - Monitor performance

2. **Short-term** (This week):
   - Add pgvector extension
   - Configure Redis caching
   - Set up monitoring alerts

3. **Long-term** (This month):
   - Load testing with production data
   - Fine-tune pgvector index parameters
   - Optimize cache TTL based on usage

## Support

For issues:
1. Check `PERFORMANCE_DEBUGGING.md`
2. Review Prometheus metrics
3. Check application logs
4. Profile with cProfile

