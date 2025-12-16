# REIMS2 NLQ/RAG Optimization - Implementation Guide

## Quick Start

### 1. Deploy Optimized Service

Replace the import in your NLQ service:

```python
# Before
from app.services.rag_retrieval_service import RAGRetrievalService

# After
from app.services.rag_retrieval_service_optimized_v2 import OptimizedRAGRetrievalService as RAGRetrievalService
```

### 2. Configure Redis Caching

Ensure Redis is running and accessible:

```bash
# Check Redis connection
redis-cli ping
```

Update `.env`:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 3. Update Connection Pool (Optional but Recommended)

In `backend/app/db/database.py`:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Increased from default 5
    max_overflow=40,       # Increased from default 10
    pool_pre_ping=True,    # Verify connections
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

### 4. Install pgvector (Optional but Highly Recommended)

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql-17-pgvector
```

**Or compile from source:**
```bash
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**Enable in PostgreSQL:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Run migration:**
```bash
cd backend
alembic upgrade head
```

### 5. Run Benchmarks

```bash
cd backend
python tests/benchmark_rag_retrieval.py
```

---

## Performance Monitoring

### Key Metrics to Watch

1. **Latency (p95)**
   - Target: <1 second
   - Alert if: >2 seconds

2. **Cache Hit Rate**
   - Target: >90%
   - Alert if: <70%

3. **Database Query Count**
   - Target: <10 per request
   - Alert if: >50 per request

4. **Memory Usage**
   - Target: <1GB
   - Alert if: >1.5GB

### Prometheus Queries

```promql
# Latency p95
histogram_quantile(0.95, rate(nlq_query_latency_seconds_bucket[5m]))

# Cache hit rate
rate(nlq_cache_hits_total[5m]) / 
  (rate(nlq_cache_hits_total[5m]) + rate(nlq_cache_misses_total[5m]))

# Database queries per request
rate(nlq_db_queries_total[5m]) / rate(nlq_queries_total[5m])
```

---

## Rollback Procedure

If issues occur:

### Immediate Rollback

1. Revert import:
```python
from app.services.rag_retrieval_service import RAGRetrievalService
```

2. Restart service:
```bash
docker compose restart backend
```

### Gradual Rollback with Feature Flag

1. Add feature flag:
```python
USE_OPTIMIZED_RETRIEVAL = os.getenv("USE_OPTIMIZED_RETRIEVAL", "false") == "true"

if USE_OPTIMIZED_RETRIEVAL:
    from app.services.rag_retrieval_service_optimized_v2 import OptimizedRAGRetrievalService as RAGRetrievalService
else:
    from app.services.rag_retrieval_service import RAGRetrievalService
```

2. Disable via environment:
```env
USE_OPTIMIZED_RETRIEVAL=false
```

---

## Troubleshooting

### Issue: Cache not working

**Symptoms:** Cache hit rate is 0%

**Solutions:**
1. Check Redis connection:
   ```python
   from app.db.redis_client import get_redis
   redis = get_redis()
   redis.ping()
   ```

2. Check Redis logs:
   ```bash
   docker logs reims-redis
   ```

3. Verify cache keys:
   ```bash
   redis-cli KEYS "rag:embedding:*"
   ```

### Issue: N+1 queries still occurring

**Symptoms:** Database query count >50 per request

**Solutions:**
1. Verify relationships in models:
   ```python
   # In DocumentChunk model
   document = relationship("DocumentUpload", back_populates="chunks")
   property = relationship("Property")
   period = relationship("FinancialPeriod")
   ```

2. Check eager loading:
   ```python
   chunks = db.query(DocumentChunk).options(
       joinedload(DocumentChunk.document),
       joinedload(DocumentChunk.property),
       joinedload(DocumentChunk.period)
   ).filter(...).all()
   ```

### Issue: pgvector migration fails

**Symptoms:** Migration error: "extension vector does not exist"

**Solutions:**
1. Install pgvector on database server
2. Run as superuser:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Service will fallback to NumPy if pgvector unavailable

### Issue: Memory usage still high

**Symptoms:** Memory >1.5GB

**Solutions:**
1. Reduce connection pool size:
   ```python
   pool_size=10  # Instead of 20
   ```

2. Reduce cache TTL:
   ```python
   EMBEDDING_CACHE_TTL = 3600  # 1 hour instead of 24 hours
   ```

3. Limit batch size:
   ```python
   chunks = chunk_query.limit(500).all()  # Instead of 1000
   ```

---

## Validation Checklist

Before deploying to production:

- [ ] Benchmarks show <1s latency (p95)
- [ ] Throughput >50 qps
- [ ] Memory <1GB
- [ ] Cache hit rate >90% after warmup
- [ ] Database queries <10 per request
- [ ] All tests passing
- [ ] No errors in logs
- [ ] Monitoring dashboards updated
- [ ] Rollback plan tested
- [ ] Documentation updated

---

## Support

For issues or questions:
1. Check logs: `docker logs reims-backend`
2. Review metrics in Grafana
3. Run benchmarks: `python tests/benchmark_rag_retrieval.py`
4. Check Redis: `redis-cli monitor`

