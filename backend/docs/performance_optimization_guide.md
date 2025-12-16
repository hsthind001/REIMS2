# REIMS2 NLQ/RAG Performance Optimization Guide

## Identified Bottlenecks

### 1. N+1 Query Problem (CRITICAL)
**Location**: `_retrieve_with_pinecone`, `_retrieve_with_postgresql`, `_retrieve_with_bm25`

**Issue**: For each retrieved chunk, separate queries are executed:
- `DocumentChunk` (1 query per chunk)
- `DocumentUpload` (1 query per chunk)
- `Property` (1 query per chunk)
- `FinancialPeriod` (1 query per chunk)

**Impact**: For 20 results = 80 database queries (~2-3 seconds)

### 2. PostgreSQL Full Table Scan (CRITICAL)
**Location**: `_retrieve_with_postgresql`

**Issue**: Loads ALL chunks matching filters, calculates similarity in Python
- With 50,000 chunks = loads all into memory
- Cosine similarity calculation for all chunks

**Impact**: ~3-4 seconds for large datasets

### 3. No Eager Loading
**Issue**: SQLAlchemy relationships not used, causing lazy loading

### 4. No Caching
**Issue**: Embedding generation, period lookups repeated

### 5. Sequential Hybrid Search
**Issue**: BM25 and semantic search run sequentially, each doing enrichment

## Optimization Solutions

### Solution 1: Batch Enrichment with Eager Loading

**Estimated Improvement**: 80% reduction (2-3s → 0.3-0.5s)

```python
from sqlalchemy.orm import joinedload, selectinload

def _enrich_chunks_batch(self, chunk_ids: List[int]) -> Dict[int, Dict]:
    """
    Batch enrich chunks with related data using eager loading.
    
    Args:
        chunk_ids: List of chunk IDs to enrich
    
    Returns:
        Dict mapping chunk_id to enriched data
    """
    # Single query with eager loading
    chunks = self.db.query(DocumentChunk)\
        .options(
            joinedload(DocumentChunk.document),
            joinedload(DocumentChunk.property),
            joinedload(DocumentChunk.period)
        )\
        .filter(DocumentChunk.id.in_(chunk_ids))\
        .all()
    
    # Build enrichment map
    enrichment_map = {}
    for chunk in chunks:
        enrichment_map[chunk.id] = {
            'chunk': chunk,
            'document': chunk.document,
            'property': chunk.property,
            'period': chunk.period
        }
    
    return enrichment_map
```

### Solution 2: PostgreSQL Vector Similarity (pgvector)

**Estimated Improvement**: 90% reduction (3-4s → 0.2-0.3s)

```sql
-- Add pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add vector column (if not exists)
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector(1536);

-- Create index for fast similarity search
CREATE INDEX IF NOT EXISTS document_chunks_embedding_vector_idx 
ON document_chunks 
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

-- Optimized query
SELECT 
    dc.*,
    1 - (dc.embedding_vector <=> %s::vector) as similarity
FROM document_chunks dc
WHERE dc.embedding_vector IS NOT NULL
    AND dc.property_id = %s  -- if filter
ORDER BY dc.embedding_vector <=> %s::vector
LIMIT %s;
```

### Solution 3: Parallel Hybrid Search

**Estimated Improvement**: 50% reduction (sequential → parallel)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

def _retrieve_hybrid_parallel(
    self,
    query: str,
    top_k: int,
    property_id: Optional[int],
    period_id: Optional[int],
    document_type: Optional[str],
    min_similarity: float,
    bm25_weight: float,
    use_pinecone: Optional[bool]
) -> List[Dict]:
    """
    Parallel hybrid search using ThreadPoolExecutor.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both searches in parallel
        bm25_future = executor.submit(
            self._retrieve_with_bm25,
            query, top_k * 2, property_id, period_id, document_type
        )
        semantic_future = executor.submit(
            self._retrieve_with_pinecone if use_pinecone else self._retrieve_with_postgresql,
            query, top_k * 2, property_id, period_id, document_type, min_similarity
        )
        
        # Wait for both
        bm25_results = bm25_future.result()
        semantic_results = semantic_future.result()
    
    # Combine results (same as before)
    return self._combine_results(bm25_results, semantic_results, bm25_weight)
```

### Solution 4: Embedding Cache

**Estimated Improvement**: 30% reduction for repeated queries

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def _get_cached_embedding(self, query_hash: str) -> Optional[List[float]]:
    """Get cached embedding if available."""
    # Check Redis cache
    cached = redis_client.get(f"embedding:{query_hash}")
    if cached:
        return json.loads(cached)
    return None

def generate_embedding(self, query: str) -> List[float]:
    """Generate embedding with caching."""
    query_hash = hashlib.md5(query.encode()).hexdigest()
    
    # Check cache
    cached = self._get_cached_embedding(query_hash)
    if cached:
        return cached
    
    # Generate new embedding
    embedding = self.embedding_service.generate_embedding(query)
    
    # Cache for 1 hour
    redis_client.setex(
        f"embedding:{query_hash}",
        3600,
        json.dumps(embedding)
    )
    
    return embedding
```

### Solution 5: Database Indexes

**Estimated Improvement**: 50-70% reduction in query time

```sql
-- Indexes for common filters
CREATE INDEX IF NOT EXISTS idx_document_chunks_property_id 
ON document_chunks(property_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_period_id 
ON document_chunks(period_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_type 
ON document_chunks(document_type);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id 
ON document_chunks(document_id);

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_document_chunks_filters 
ON document_chunks(property_id, period_id, document_type) 
WHERE embedding IS NOT NULL;
```

## Implementation Priority

1. **HIGH**: Batch enrichment (Solution 1) - Immediate 80% improvement
2. **HIGH**: Database indexes (Solution 5) - Quick win, 50-70% improvement
3. **MEDIUM**: PostgreSQL pgvector (Solution 2) - Requires migration
4. **MEDIUM**: Parallel hybrid search (Solution 3) - Easy to implement
5. **LOW**: Embedding cache (Solution 4) - Good for repeated queries

## Expected Performance

### Before Optimization
- Hybrid search: 5-6 seconds
- Semantic search: 3-4 seconds
- BM25 search: 1-2 seconds

### After Optimization
- Hybrid search: 0.8-1.2 seconds (80% improvement)
- Semantic search: 0.3-0.5 seconds (90% improvement)
- BM25 search: 0.2-0.3 seconds (85% improvement)

## Monitoring

Add performance metrics:

```python
from prometheus_client import Histogram
import time

retrieval_latency = Histogram(
    'rag_retrieval_latency_seconds',
    'RAG retrieval latency',
    ['method', 'has_filters']
)

def retrieve_relevant_chunks(self, ...):
    start_time = time.time()
    try:
        results = self._retrieve_hybrid(...)
        return results
    finally:
        duration = time.time() - start_time
        retrieval_latency.labels(
            method='hybrid',
            has_filters=str(bool(property_id or period_id))
        ).observe(duration)
```

