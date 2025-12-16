# Pinecone Vector Database Usage Examples

This guide provides code examples and migration instructions for using Pinecone vector database in REIMS2.

## Table of Contents

1. [Setup and Configuration](#setup-and-configuration)
2. [Basic Operations](#basic-operations)
3. [Indexing Document Chunks](#indexing-document-chunks)
4. [Querying with Filters](#querying-with-filters)
5. [Namespace Management](#namespace-management)
6. [Sync Service Usage](#sync-service-usage)
7. [RAG Retrieval](#rag-retrieval)
8. [Migration Guide](#migration-guide)
9. [Error Handling](#error-handling)
10. [Best Practices](#best-practices)

## Setup and Configuration

### 1. Environment Variables

Add the following to your `.env` file:

```bash
# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=reims2-documents
PINECONE_DIMENSION=1536
PINECONE_METRIC=cosine
PINECONE_TIMEOUT=30
```

### 2. Initialize Pinecone

```python
from app.config.pinecone_config import pinecone_config

# Initialize Pinecone (automatically creates index if it doesn't exist)
success = pinecone_config.initialize()

if success:
    print("Pinecone initialized successfully")
else:
    print("Failed to initialize Pinecone. Check your API key and configuration.")
```

### 3. Health Check

```python
from app.config.pinecone_config import pinecone_config

health = pinecone_config.health_check()
print(f"Pinecone healthy: {health['healthy']}")
print(f"Total vectors: {health['stats']['total_vector_count']}")
```

## Basic Operations

### Upsert Vectors

```python
from app.services.pinecone_service import PineconeService
from sqlalchemy.orm import Session

# Initialize service
service = PineconeService(db=db_session)

# Upsert a single vector
vector = {
    'id': 'chunk_123',
    'values': [0.1] * 1536,  # 1536-dimensional embedding
    'metadata': {
        'property_id': 1,
        'document_type': 'balance_sheet',
        'period_year': 2024,
        'period_month': 1
    }
}

result = service.upsert_vectors([vector])
print(f"Upserted: {result['upserted']} vectors")
```

### Query Vectors

```python
# Generate query embedding (using your embedding service)
from app.services.embedding_service import EmbeddingService

embedding_service = EmbeddingService(db_session)
query_text = "What is the total revenue?"
query_embedding = embedding_service.generate_embedding(query_text)

# Query Pinecone
results = service.query_vectors(
    query_vector=query_embedding,
    top_k=5,
    include_metadata=True
)

for match in results['matches']:
    print(f"ID: {match['id']}, Score: {match['score']}")
    print(f"Metadata: {match['metadata']}")
```

### Delete Vectors

```python
# Delete by IDs
result = service.delete_vectors(
    vector_ids=['chunk_123', 'chunk_456']
)

# Delete by metadata filter
result = service.delete_vectors(
    filter={'property_id': 1, 'document_type': 'balance_sheet'}
)

# Delete all vectors in a namespace (use with caution!)
result = service.delete_vectors(
    namespace='balance_sheet',
    delete_all=True
)
```

## Indexing Document Chunks

### Index a Single Chunk

```python
from app.services.pinecone_service import PineconeService
from app.models.document_chunk import DocumentChunk

service = PineconeService(db_session)

# Get chunk from database
chunk = db_session.query(DocumentChunk).filter(
    DocumentChunk.id == 123
).first()

# Upsert to Pinecone
result = service.upsert_chunk(
    chunk_id=chunk.id,
    embedding=chunk.embedding,
    property_id=chunk.property_id,
    document_type=chunk.document_type,
    period_year=chunk.period.period_year if chunk.period else None,
    period_month=chunk.period.period_month if chunk.period else None,
    document_id=chunk.document_id,
    chunk_index=chunk.chunk_index
)
```

### Batch Indexing

```python
from app.services.pinecone_service import PineconeService

service = PineconeService(db_session)

# Get chunks with embeddings
chunks = db_session.query(DocumentChunk).filter(
    DocumentChunk.embedding.isnot(None)
).limit(100).all()

# Prepare embeddings
embeddings = [chunk.embedding for chunk in chunks]

# Batch upsert
result = service.upsert_chunks_batch(chunks, embeddings)
print(f"Synced {result['total_chunks']} chunks")
print(f"Namespaces: {result['namespaces']}")
```

## Querying with Filters

### Filter by Property

```python
query_embedding = embedding_service.generate_embedding("revenue and expenses")

results = service.query_vectors(
    query_vector=query_embedding,
    top_k=10,
    filter={
        'property_id': 1
    }
)
```

### Filter by Document Type and Period

```python
results = service.query_vectors(
    query_vector=query_embedding,
    top_k=10,
    filter={
        'document_type': 'balance_sheet',
        'period_year': 2024,
        'period_month': 1
    }
)
```

### Multiple Property Filter

```python
results = service.query_vectors(
    query_vector=query_embedding,
    top_k=10,
    filter={
        'property_id': {'$in': [1, 2, 3]},
        'document_type': 'income_statement'
    }
)
```

## Namespace Management

### Using Namespaces

Namespaces isolate vectors by document type for better organization:

```python
# Upsert to balance_sheet namespace
service.upsert_vectors(
    vectors=[vector],
    namespace='balance_sheet'
)

# Query from specific namespace
results = service.query_vectors(
    query_vector=query_embedding,
    top_k=5,
    namespace='balance_sheet'
)

# Available namespaces:
# - 'balance_sheet'
# - 'income_statement'
# - 'cash_flow'
# - 'rent_roll'
# - '' (default namespace)
```

### Get Namespace Statistics

```python
stats = service.get_index_stats(namespace='balance_sheet')
print(f"Vectors in balance_sheet namespace: {stats['vector_count']}")
```

## Sync Service Usage

### Sync Single Chunk

```python
from app.services.pinecone_sync_service import PineconeSyncService

sync_service = PineconeSyncService(db_session)

# Sync a chunk from PostgreSQL to Pinecone
result = sync_service.sync_chunk_to_pinecone(chunk_id=123)
print(f"Sync successful: {result['success']}")
```

### Sync All Chunks for a Document

```python
# Sync all chunks of a document
result = sync_service.sync_document_to_pinecone(
    document_id=456,
    force_reembed=False  # Set True to regenerate embeddings
)

print(f"Synced {result['synced_chunks']} of {result['total_chunks']} chunks")
```

### Migrate All Existing Chunks

```python
# Sync all chunks with embeddings to Pinecone
result = sync_service.sync_all_chunks_to_pinecone(
    batch_size=100,
    force_reembed=False
)

print(f"Total chunks: {result['total_chunks']}")
print(f"Synced: {result['synced']}")
print(f"Failed: {result['failed']}")
```

### Verify Sync Status

```python
# Check if a chunk is synced
status = sync_service.verify_sync_status(chunk_id=123)
print(f"In PostgreSQL: {status['in_postgresql']}")
print(f"In Pinecone: {status['in_pinecone']}")
```

### Reconcile Sync

```python
# Find chunks missing in Pinecone
reconciliation = sync_service.reconcile_sync(
    property_id=1  # Optional: filter by property
)

print(f"Total chunks: {reconciliation['total_chunks']}")
print(f"In Pinecone: {reconciliation['in_pinecone']}")
print(f"Missing: {reconciliation['missing_in_pinecone']}")
print(f"Missing IDs: {reconciliation['missing_chunk_ids'][:10]}")
```

## RAG Retrieval

### Using RAG Service with Pinecone

The RAG service automatically uses Pinecone if available, with PostgreSQL fallback:

```python
from app.services.rag_retrieval_service import RAGRetrievalService

rag_service = RAGRetrievalService(db_session)

# Query (automatically uses Pinecone if available)
results = rag_service.retrieve_relevant_chunks(
    query="What is the DSCR for property 1?",
    top_k=5,
    property_id=1,
    document_type='balance_sheet',
    min_similarity=0.3
)

for result in results:
    print(f"Chunk {result['chunk_id']}: {result['similarity']:.3f}")
    print(f"Method: {result.get('retrieval_method', 'unknown')}")
    print(f"Text: {result['chunk_text'][:100]}...")
```

### Force PostgreSQL Retrieval

```python
# Force PostgreSQL retrieval (bypass Pinecone)
results = rag_service.retrieve_relevant_chunks(
    query="test query",
    top_k=5,
    use_pinecone=False
)
```

### Get Combined Context

```python
# Get context from multiple chunks
chunk_ids = [1, 2, 3]
context = rag_service.get_chunk_context(chunk_ids)
print(context)
```

## Migration Guide

### Step 1: Install Dependencies

```bash
pip install pinecone-client>=3.0.0
```

### Step 2: Configure Environment

Add Pinecone configuration to your `.env` file (see [Setup](#setup-and-configuration)).

### Step 3: Initialize Pinecone

```python
from app.config.pinecone_config import pinecone_config

# This will create the index if it doesn't exist
pinecone_config.initialize()
```

### Step 4: Migrate Existing Data

```python
from app.services.pinecone_sync_service import PineconeSyncService

sync_service = PineconeSyncService(db_session)

# Migrate all existing chunks
result = sync_service.sync_all_chunks_to_pinecone(
    batch_size=100,
    force_reembed=False
)

print(f"Migration complete: {result['synced']} chunks synced")
```

### Step 5: Verify Migration

```python
# Check sync status
reconciliation = sync_service.reconcile_sync()
print(f"Missing in Pinecone: {reconciliation['missing_in_pinecone']}")

# If missing chunks found, sync them
if reconciliation['missing_in_pinecone'] > 0:
    for chunk_id in reconciliation['missing_chunk_ids']:
        sync_service.sync_chunk_to_pinecone(chunk_id)
```

### Step 6: Update Code to Use Pinecone

The RAG service automatically uses Pinecone if available. No code changes needed for basic usage.

For new chunks, ensure they're synced to Pinecone:

```python
from app.services.pinecone_sync_service import PineconeSyncService

# After creating a chunk with embedding
sync_service = PineconeSyncService(db_session)
sync_service.sync_new_chunk(chunk_id=new_chunk.id)
```

## Error Handling

### Connection Errors

```python
from app.config.pinecone_config import pinecone_config

try:
    health = pinecone_config.health_check()
    if not health['healthy']:
        print(f"Pinecone unhealthy: {health.get('error')}")
except Exception as e:
    print(f"Failed to check Pinecone health: {e}")
    # Fallback to PostgreSQL
```

### Retry Logic

The service includes automatic retry with exponential backoff:

```python
# Operations automatically retry on failure
result = service.upsert_vectors(vectors)

if not result['success']:
    print(f"Upsert failed after retries: {result['error']}")
    # Handle error appropriately
```

### Graceful Degradation

The RAG service automatically falls back to PostgreSQL if Pinecone is unavailable:

```python
# This will use PostgreSQL if Pinecone fails
results = rag_service.retrieve_relevant_chunks(
    query="test",
    top_k=5
)

# Check which method was used
if results and results[0].get('retrieval_method') == 'postgresql':
    print("Using PostgreSQL fallback")
```

## Best Practices

### 1. Batch Operations

Always use batch operations when possible:

```python
# Good: Batch upsert
service.upsert_chunks_batch(chunks, embeddings)

# Avoid: Individual upserts in a loop
for chunk, embedding in zip(chunks, embeddings):
    service.upsert_chunk(...)  # Slow!
```

### 2. Namespace Organization

Use namespaces to organize by document type:

```python
# Good: Use appropriate namespace
service.upsert_vectors(vectors, namespace='balance_sheet')

# Avoid: All vectors in default namespace
service.upsert_vectors(vectors)  # Less organized
```

### 3. Metadata Filtering

Use metadata filters to narrow queries:

```python
# Good: Filtered query
results = service.query_vectors(
    query_vector=embedding,
    top_k=10,
    filter={'property_id': 1, 'document_type': 'balance_sheet'}
)

# Avoid: Query all, filter in application
results = service.query_vectors(query_vector=embedding, top_k=1000)
filtered = [r for r in results if r['metadata']['property_id'] == 1]  # Inefficient!
```

### 4. Sync After Changes

Always sync chunks after creating or updating embeddings:

```python
# After embedding a chunk
embedding_service.embed_chunk(chunk_id=123)

# Sync to Pinecone
sync_service.sync_chunk_to_pinecone(chunk_id=123)
```

### 5. Monitor Sync Status

Regularly check sync status:

```python
# Weekly reconciliation
reconciliation = sync_service.reconcile_sync()
if reconciliation['missing_in_pinecone'] > 0:
    # Sync missing chunks
    for chunk_id in reconciliation['missing_chunk_ids']:
        sync_service.sync_chunk_to_pinecone(chunk_id)
```

### 6. Error Handling

Always handle errors gracefully:

```python
try:
    result = service.query_vectors(...)
    if not result['success']:
        # Log error and use fallback
        logger.error(f"Pinecone query failed: {result['error']}")
        # Use PostgreSQL fallback
        results = rag_service.retrieve_relevant_chunks(..., use_pinecone=False)
except Exception as e:
    logger.error(f"Pinecone error: {e}")
    # Fallback to PostgreSQL
```

## Troubleshooting

### Index Not Found

```python
# Check if index exists
if not pinecone_config.index_exists():
    # Create index
    pinecone_config.create_index_if_not_exists()
```

### Connection Timeout

```python
# Increase timeout in config
# In .env:
PINECONE_TIMEOUT=60
```

### Rate Limiting

The service automatically handles rate limits with retry logic. If you encounter persistent rate limits:

1. Reduce batch sizes
2. Add delays between batches
3. Check your Pinecone plan limits

### Dimension Mismatch

Ensure embeddings match configured dimension:

```python
# Check embedding dimension
embedding = embedding_service.generate_embedding("test")
assert len(embedding) == 1536, f"Expected 1536, got {len(embedding)}"
```

## Additional Resources

- [Pinecone Documentation](https://docs.pinecone.io/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- REIMS2 RAG System Architecture

