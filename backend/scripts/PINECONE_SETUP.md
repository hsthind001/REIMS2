# Pinecone Setup Guide

This guide walks you through setting up Pinecone vector database for REIMS2.

## Prerequisites

1. **Pinecone Account**: Sign up at https://app.pinecone.io/
2. **API Key**: Get your API key from the Pinecone dashboard
3. **Python Dependencies**: Ensure `pinecone-client>=3.0.0` is installed

## Step 1: Configure Environment Variables

Add the following to your `.env` file in the `backend/` directory:

```bash
# Pinecone Vector Database Settings
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=reims2-documents
PINECONE_DIMENSION=1536
PINECONE_METRIC=cosine
PINECONE_TIMEOUT=30
```

**Important**: Replace `your-pinecone-api-key-here` with your actual API key from https://app.pinecone.io/

## Step 2: Initialize Pinecone

Run the initialization script:

```bash
cd backend
python scripts/init_pinecone.py
```

This script will:
- Verify your API key is set
- Initialize the Pinecone client
- Create the index if it doesn't exist
- Perform a health check

Expected output:
```
============================================================
Pinecone Vector Database Initialization
============================================================

✓ API Key: ********************abcd
✓ Environment: us-east-1-aws
✓ Index Name: reims2-documents
✓ Dimension: 1536
✓ Metric: cosine

Initializing Pinecone...
✓ Pinecone initialized successfully

Performing health check...
✓ Pinecone is healthy
✓ Total vectors: 0

============================================================
✅ Pinecone initialization complete!
============================================================
```

## Step 3: Migrate Existing Data

After initialization, sync your existing document chunks to Pinecone:

```bash
python scripts/migrate_to_pinecone.py
```

This script will:
- Check for existing chunks with embeddings in PostgreSQL
- Sync them to Pinecone (maintains dual storage)
- Show progress and statistics
- Verify sync status

**Note**: This maintains dual storage - your data remains in PostgreSQL. Pinecone is used for fast vector search.

## Step 4: Verify Setup

Check Pinecone health at any time:

```bash
python scripts/check_pinecone_health.py
```

## Troubleshooting

### API Key Not Set

If you see:
```
❌ ERROR: PINECONE_API_KEY not set in environment variables
```

Solution:
1. Get your API key from https://app.pinecone.io/
2. Add it to your `.env` file:
   ```bash
   PINECONE_API_KEY=your-actual-api-key
   ```
3. Restart your application/scripts

### Index Creation Failed

If index creation fails:
- Check your Pinecone plan limits
- Verify the index name doesn't already exist
- Check your API key permissions

### Migration Issues

If migration fails:
- Ensure Pinecone is initialized first
- Check that chunks have embeddings in PostgreSQL
- Review error messages for specific issues

### Health Check Fails

If health check fails:
- Verify API key is correct
- Check network connectivity
- Ensure Pinecone service is available

## Next Steps

After setup is complete:

1. **Automatic Usage**: The RAG service will automatically use Pinecone when available
2. **New Chunks**: New chunks with embeddings are automatically synced to Pinecone
3. **Monitoring**: Use `check_pinecone_health.py` to monitor status

## Manual Operations

### Sync a Single Chunk

```python
from app.db.database import SessionLocal
from app.services.pinecone_sync_service import PineconeSyncService

db = SessionLocal()
sync_service = PineconeSyncService(db)
result = sync_service.sync_chunk_to_pinecone(chunk_id=123)
```

### Query with Pinecone

```python
from app.services.rag_retrieval_service import RAGRetrievalService

rag_service = RAGRetrievalService(db)
results = rag_service.retrieve_relevant_chunks(
    query="What is the DSCR?",
    top_k=5
)
```

## Support

For more information:
- See `backend/docs/pinecone_usage_examples.md` for detailed usage examples
- Check Pinecone documentation: https://docs.pinecone.io/
- Review unit tests in `backend/tests/services/test_pinecone_service.py`

