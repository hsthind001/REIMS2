# BM25 Keyword Search Guide

## Overview

BM25 keyword search complements semantic search by providing exact term matching capabilities. While semantic search excels at conceptual queries, BM25 is ideal for queries requiring exact keyword matches, such as "DSCR below 1.25" or specific financial metrics.

## When to Use BM25 vs Semantic Search

### Use BM25 When:
- **Exact term matching** is required (e.g., "DSCR below 1.25")
- **Specific numbers or values** need to be found
- **Keyword-heavy queries** (e.g., "net operating income", "property revenue")
- **Precise document retrieval** based on exact text matches

### Use Semantic Search When:
- **Conceptual queries** (e.g., "financial performance", "risk indicators")
- **Paraphrased questions** (e.g., "What is the debt coverage?")
- **Contextual understanding** is needed
- **Multi-language support** (if embeddings support it)

### Use Hybrid Search When:
- **Best of both worlds** - combine keyword matching with semantic understanding
- **Uncertain query type** - let the system decide
- **Maximum recall** - ensure no relevant documents are missed

## Architecture

```
User Query
    ↓
[Tokenize Query] (lowercase, whitespace split)
    ↓
[BM25 Scoring] (BM25Okapi algorithm)
    ↓
[Metadata Filtering] (property_id, document_type, period_id)
    ↓
[Top-K Results] (sorted by score)
```

## Configuration

Configuration is managed in `app/config/bm25_config.py`:

```python
from app.config.bm25_config import bm25_config

# BM25 Algorithm Parameters
bm25_config.K1 = 1.5  # Term frequency saturation
bm25_config.B = 0.75   # Length normalization

# Cache Settings
bm25_config.CACHE_DIR = "/tmp/bm25_cache"  # Configurable via BM25_CACHE_DIR env var
bm25_config.CACHE_FILENAME = "bm25_index.pkl"

# Auto-Rebuild
bm25_config.AUTO_REBUILD = False  # Enable via BM25_AUTO_REBUILD=true
bm25_config.REBUILD_THRESHOLD = 100  # Rebuild when chunk count changes by N

# Performance
bm25_config.MAX_RESULTS = 100
bm25_config.SEARCH_TIMEOUT_MS = 100  # Target latency
```

## Usage

### Basic BM25 Search

```python
from app.services.bm25_search_service import BM25SearchService
from app.db.database import SessionLocal

db = SessionLocal()
service = BM25SearchService(db)

# Search
results = service.search(
    query="DSCR below 1.25",
    top_k=10,
    property_id=1,
    document_type="income_statement"
)

for result in results:
    print(f"Score: {result['score']}")
    print(f"Text: {result['chunk_text'][:200]}...")
```

### Hybrid Search (BM25 + Semantic)

```python
from app.services.rag_retrieval_service import RAGRetrievalService

rag_service = RAGRetrievalService(db)

# Hybrid search with 60% BM25, 40% semantic
results = rag_service.retrieve_relevant_chunks(
    query="DSCR below 1.25",
    top_k=10,
    use_bm25=True,
    bm25_weight=0.6,  # 60% BM25, 40% semantic
    property_id=1
)
```

### Index Management

```python
# Build index
result = service.build_index()
print(f"Indexed {result['chunk_count']} chunks")

# Rebuild index
result = service.rebuild_index()

# Get statistics
stats = service.get_index_stats()
print(f"Chunk count: {stats['chunk_count']}")
print(f"Cache size: {stats['cache_size_mb']} MB")

# Clear cache
service.clear_cache()
```

## BM25 Parameters Tuning

### K1 Parameter (Term Frequency Saturation)

**Default**: 1.5

**What it controls**: How much term frequency affects the score

- **Higher K1 (2.0-3.0)**: More weight to term frequency
  - Use when: Documents with many occurrences of a term should rank higher
  - Example: "revenue" appearing 10 times vs 1 time
  
- **Lower K1 (0.5-1.0)**: Less weight to term frequency
  - Use when: Term presence is more important than frequency
  - Example: Boolean-like matching

**Tuning Guide**:
- Start with default (1.5)
- If queries with repeated terms rank too high → lower K1
- If term frequency isn't considered enough → raise K1

### B Parameter (Length Normalization)

**Default**: 0.75

**What it controls**: How much document length affects scoring

- **Higher B (0.8-1.0)**: More penalty for long documents
  - Use when: Shorter, focused documents should rank higher
  - Example: Short financial summaries vs long reports
  
- **Lower B (0.3-0.5)**: Less penalty for long documents
  - Use when: Document length shouldn't significantly affect ranking
  - Example: All documents are similar length

**Tuning Guide**:
- Start with default (0.75)
- If short documents rank too high → lower B
- If long documents are unfairly penalized → raise B

### Example Tuning Scenarios

**Scenario 1: Financial Documents with Specific Metrics**
```python
# Emphasize exact matches, less length penalty
bm25_config.K1 = 1.2
bm25_config.B = 0.6
```

**Scenario 2: Mixed Document Lengths**
```python
# Standard settings work well
bm25_config.K1 = 1.5
bm25_config.B = 0.75
```

**Scenario 3: Keyword-Heavy Queries**
```python
# Higher term frequency weight
bm25_config.K1 = 2.0
bm25_config.B = 0.75
```

## Index Management

### Building the Index

**Manual Build**:
```bash
python backend/scripts/build_bm25_index.py
```

**Programmatic Build**:
```python
service = BM25SearchService(db)
result = service.build_index()
```

### Auto-Rebuild

Enable auto-rebuild to keep index up-to-date:

```bash
export BM25_AUTO_REBUILD=true
export BM25_REBUILD_THRESHOLD=100
```

The index will automatically rebuild when:
- Chunk count changes by more than `REBUILD_THRESHOLD`
- This happens during search operations (if enabled)

### Cache Management

**Cache Location**: `/tmp/bm25_cache/bm25_index.pkl` (configurable)

**Custom Cache Directory**:
```bash
export BM25_CACHE_DIR=/path/to/cache
```

**Clear Cache**:
```python
service.clear_cache()
```

Or via CLI:
```bash
python -m app.cli.bm25_commands clear-cache
```

## CLI Commands

### Rebuild Index

```bash
python -m app.cli.bm25_commands rebuild
```

### View Statistics

```bash
python -m app.cli.bm25_commands stats
```

### Clear Cache

```bash
python -m app.cli.bm25_commands clear-cache
```

### Test Search

```bash
python -m app.cli.bm25_commands search "DSCR below 1.25" --top-k 10 --property-id 1
```

## Performance Optimization

### Index Building

- **Batch Processing**: Index builds in batches (configurable via `BATCH_SIZE`)
- **Memory Management**: Old index cleared before rebuild
- **Caching**: Index cached to disk for fast loading

### Search Performance

- **Target Latency**: <100ms for top-20 results
- **Optimization Tips**:
  - Use metadata filters to reduce search space
  - Limit `top_k` to reasonable values
  - Enable index caching for faster startup

### Cache Performance

- **Load Time**: <1s for typical index sizes
- **Save Time**: <2s for typical index sizes
- **Cache Size**: Typically 10-50MB for 10k chunks

## Integration with RAGRetrievalService

### BM25-Only Search

```python
results = rag_service.retrieve_relevant_chunks(
    query="DSCR below 1.25",
    top_k=10,
    use_bm25=True,
    use_pinecone=False  # Disable semantic search
)
```

### Hybrid Search

```python
results = rag_service.retrieve_relevant_chunks(
    query="What is the DSCR?",
    top_k=10,
    use_bm25=True,
    bm25_weight=0.6,  # 60% BM25, 40% semantic
    use_pinecone=True
)
```

### Score Normalization

Hybrid search normalizes both BM25 and semantic scores to 0-1 range:

```python
combined_score = (bm25_weight * normalized_bm25_score) + 
                 ((1 - bm25_weight) * normalized_semantic_score)
```

## Troubleshooting

### Low Search Performance (>100ms)

**Possible Causes**:
- Index too large
- Too many chunks to filter
- Database query slow

**Solutions**:
- Use metadata filters to reduce search space
- Reduce `top_k` value
- Check database indexes
- Consider rebuilding index

### Index Build Fails

**Possible Causes**:
- No chunks in database
- Empty chunk text
- Memory issues

**Solutions**:
- Verify chunks exist: `SELECT COUNT(*) FROM document_chunks WHERE chunk_text IS NOT NULL`
- Check chunk text is not empty
- Build in smaller batches
- Increase available memory

### Cache Load Fails

**Possible Causes**:
- Cache file corrupted
- Version mismatch
- Permission issues

**Solutions**:
- Clear cache and rebuild: `service.clear_cache()` then `service.build_index()`
- Check file permissions on cache directory
- Verify cache version matches code version

### Poor Search Results

**Possible Causes**:
- BM25 parameters not tuned
- Query tokenization issues
- Index out of date

**Solutions**:
- Tune K1 and B parameters
- Check query tokenization (should be lowercase, whitespace split)
- Rebuild index to include new chunks
- Try hybrid search for better results

## Best Practices

1. **Regular Index Rebuilds**: Schedule nightly rebuilds for production
2. **Monitor Performance**: Track search latency and adjust parameters
3. **Use Metadata Filters**: Always filter by property_id/document_type when possible
4. **Hybrid Search**: Use hybrid search for best results (combines BM25 + semantic)
5. **Cache Management**: Keep cache directory clean, monitor disk space
6. **Parameter Tuning**: Start with defaults, tune based on query patterns

## Examples

### Example 1: Exact Number Match

```python
# Query: "DSCR below 1.25"
results = service.search("DSCR below 1.25", top_k=5)

# BM25 excels at finding exact matches
# Results will have high scores for chunks containing "DSCR", "below", "1.25"
```

### Example 2: Keyword-Heavy Query

```python
# Query: "net operating income"
results = service.search("net operating income", top_k=10)

# BM25 finds documents with these exact terms
# Higher scores for documents with all three terms
```

### Example 3: Hybrid Search

```python
# Query: "What is the debt service coverage ratio?"
results = rag_service.retrieve_relevant_chunks(
    query="What is the debt service coverage ratio?",
    top_k=10,
    use_bm25=True,
    bm25_weight=0.4,  # 40% BM25 (for "debt service coverage ratio")
    use_pinecone=True  # 60% semantic (for "What is" conceptual part)
)

# Hybrid combines:
# - BM25: Exact matches for "debt service coverage ratio"
# - Semantic: Conceptual understanding of "What is"
```

## Success Criteria

- ✅ BM25 index built from all document chunks
- ✅ Search returns top-k results with scores
- ✅ Index cached to disk for fast loading
- ✅ Supports filtering by metadata (property_id, document_type)
- ✅ Index rebuilds automatically when threshold exceeded (or on-demand)
- ✅ Search latency <100ms for top-20 results
- ✅ Unit tests for search accuracy
- ✅ CLI command for index rebuild
- ✅ Documentation for BM25 parameters and tuning

## Future Enhancements

- **Incremental Updates**: Update index without full rebuild
- **Multi-Index Support**: Separate indexes per document type
- **Advanced Tokenization**: Support for stemming, stop words
- **Query Expansion**: Automatic synonym expansion
- **Result Caching**: Cache frequent query results

## Related Documentation

- [RRF Fusion Guide](../docs/rrf_fusion_guide.md): Combine BM25 and semantic search using Reciprocal Rank Fusion

