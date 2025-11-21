# Setup Instructions for RAG System

## Quick Start

The RAG system is now implemented and ready to use! Follow these steps to enable document content queries:

### Step 1: Chunk Existing Documents

Chunk all documents that have been extracted:

```bash
docker exec reims-backend python -c "
from app.db.database import SessionLocal
from app.services.document_chunking_service import DocumentChunkingService

db = SessionLocal()
service = DocumentChunkingService(db)
result = service.chunk_all_documents()
print(f'✅ Chunked {result[\"successful\"]} documents')
print(f'✅ Created {result[\"total_chunks\"]} chunks')
print(f'⚠️  Skipped {result[\"skipped\"]} (already chunked)')
print(f'❌ Failed {result[\"failed\"]}')
if result['errors']:
    print('Errors:', result['errors'][:3])
db.close()
"
```

### Step 2: Generate Embeddings (Requires API Key)

**Option A: Using OpenAI (Recommended)**

Set your OpenAI API key in `.env`:
```bash
OPENAI_API_KEY=your_key_here
```

Then generate embeddings:
```bash
docker exec reims-backend python -c "
from app.db.database import SessionLocal
from app.services.embedding_service import EmbeddingService

db = SessionLocal()
service = EmbeddingService(db)
if service.embedding_method:
    result = service.embed_all_chunks()
    print(f'✅ Embedded {result[\"successful\"]} chunks using {service.embedding_method}')
    print(f'❌ Failed {result[\"failed\"]}')
else:
    print('⚠️  No embedding service available. Set OPENAI_API_KEY or install sentence-transformers.')
db.close()
"
```

**Option B: Using Sentence-Transformers (Local, No API Key)**

The system will automatically use sentence-transformers if OpenAI is unavailable. It's slower but works offline.

### Step 3: Test Document Queries

Now you can ask questions about your documents:

```bash
docker exec reims-backend python -c "
from app.db.database import SessionLocal
from app.services.nlq_service import NaturalLanguageQueryService

db = SessionLocal()
service = NaturalLanguageQueryService(db)

# Test document content query
result = service.query('What did the income statement say about operating expenses?', 1)
print('Query:', result.get('question'))
print('Success:', result.get('success'))
print('Answer:', result.get('answer', '')[:500])

db.close()
"
```

## What Queries Are Now Supported?

### ✅ Document Content Queries
- "What did the income statement say about operating expenses?"
- "Find all mentions of 'debt restructuring'"
- "What were the main concerns in the financial notes?"

### ✅ Hybrid Queries (Structured + Document Content)
- "Compare Q3 2024 income statement notes with calculated metrics"
- "What does the balance sheet say about total assets vs calculated value?"

### ✅ Structured Data Queries (Still Work!)
- "Total portfolio value"
- "NOI trends for last 12 months"
- "Which properties have DSCR below 1.25?"

## Troubleshooting

### No Embeddings Generated
- **Check API key**: Ensure `OPENAI_API_KEY` is set in `.env` or `docker-compose.yml`
- **Check logs**: Look for "No embedding method available" warning
- **Fallback**: System will use text search if embeddings unavailable

### No Chunks Found
- **Check extraction**: Documents must have `extraction_status = 'completed'`
- **Check extraction_log**: Must have `extracted_text` populated
- **Re-chunk**: Run chunking service again

### Queries Not Working
- **Check backend logs**: `docker logs reims-backend`
- **Test basic query**: Try "Total portfolio value" first
- **Check database**: Verify `document_chunks` table exists

## Performance Tips

1. **Batch Processing**: Chunk and embed documents in batches
2. **API Costs**: OpenAI embeddings cost ~$0.0001 per 1K tokens
3. **Caching**: Query results are cached for 24 hours
4. **Indexing**: Database indexes are created automatically

## Next Steps

1. ✅ Chunk all documents
2. ✅ Generate embeddings (requires API key)
3. ✅ Test document queries
4. ✅ Monitor performance and accuracy

The system is backward compatible - all existing queries continue to work!

