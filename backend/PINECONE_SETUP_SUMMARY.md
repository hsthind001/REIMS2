# Pinecone Setup - Quick Start

## ✅ Implementation Complete

All Pinecone infrastructure has been implemented and is ready to use.

## 🚀 Quick Setup (3 Steps)

### Step 1: Add API Key to .env

Add this line to your `backend/.env` file:

```bash
PINECONE_API_KEY=your-pinecone-api-key-here
```

Get your API key from: https://app.pinecone.io/

### Step 2: Initialize Pinecone

```bash
cd backend
python3 scripts/init_pinecone.py
```

### Step 3: Migrate Existing Data

```bash
python3 scripts/migrate_to_pinecone.py
```

## 📋 What Was Implemented

### Core Components
- ✅ Pinecone configuration module with connection pooling and retry logic
- ✅ Pinecone service with vector operations (upsert, query, delete, update)
- ✅ Sync service for dual storage (PostgreSQL + Pinecone)
- ✅ Updated RAG service to use Pinecone as primary with PostgreSQL fallback
- ✅ Updated embedding service to use `text-embedding-3-large` (1536 dimensions)

### Utilities
- ✅ `init_pinecone.py` - Initialize Pinecone and create index
- ✅ `migrate_to_pinecone.py` - Sync existing data to Pinecone
- ✅ `check_pinecone_health.py` - Health check utility

### Testing
- ✅ Comprehensive unit tests with mocked Pinecone client
- ✅ Integration tests for end-to-end scenarios

### Documentation
- ✅ Usage examples and migration guide
- ✅ Setup instructions

## 📁 File Locations

### Configuration
- `backend/app/config/pinecone_config.py` - Pinecone client and index management
- `backend/app/core/config.py` - Environment variables (updated)

### Services
- `backend/app/services/pinecone_service.py` - Vector operations
- `backend/app/services/pinecone_sync_service.py` - Dual storage sync
- `backend/app/services/rag_retrieval_service.py` - Updated to use Pinecone
- `backend/app/services/embedding_service.py` - Updated to use text-embedding-3-large

### Scripts
- `backend/scripts/init_pinecone.py` - Initialization script
- `backend/scripts/migrate_to_pinecone.py` - Migration script
- `backend/scripts/check_pinecone_health.py` - Health check script

### Tests
- `backend/tests/services/test_pinecone_service.py` - Unit tests
- `backend/tests/integration/test_pinecone_integration.py` - Integration tests

### Documentation
- `backend/docs/pinecone_usage_examples.md` - Detailed usage guide
- `backend/scripts/PINECONE_SETUP.md` - Setup instructions

## 🔧 Configuration

All configuration is done via environment variables in `.env`:

```bash
PINECONE_API_KEY=your-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=reims2-documents
PINECONE_DIMENSION=1536
PINECONE_METRIC=cosine
PINECONE_TIMEOUT=30
```

## ✨ Features

- **Dual Storage**: PostgreSQL (metadata) + Pinecone (vectors)
- **Automatic Retry**: Exponential backoff for reliability
- **Namespace Isolation**: Separate namespaces per document type
- **Metadata Filtering**: Filter by property_id, document_type, period_year
- **Graceful Degradation**: Falls back to PostgreSQL if Pinecone unavailable
- **Production Ready**: Connection pooling, error handling, logging

## 📖 Next Steps

1. **Get Pinecone API Key**: Sign up at https://app.pinecone.io/
2. **Add to .env**: Set `PINECONE_API_KEY` in your `.env` file
3. **Initialize**: Run `python3 scripts/init_pinecone.py`
4. **Migrate**: Run `python3 scripts/migrate_to_pinecone.py`
5. **Verify**: Run `python3 scripts/check_pinecone_health.py`

## 🎯 Usage

After setup, the RAG service automatically uses Pinecone:

```python
from app.services.rag_retrieval_service import RAGRetrievalService

rag_service = RAGRetrievalService(db_session)
results = rag_service.retrieve_relevant_chunks(
    query="What is the DSCR?",
    top_k=5
)
```

See `backend/docs/pinecone_usage_examples.md` for detailed examples.

## ⚠️ Important Notes

- **API Key Required**: You must set `PINECONE_API_KEY` before initialization
- **Dual Storage**: Data is stored in both PostgreSQL and Pinecone
- **Automatic Sync**: New chunks are automatically synced (when sync service is called)
- **Fallback**: System works without Pinecone (uses PostgreSQL only)

## 🐛 Troubleshooting

See `backend/scripts/PINECONE_SETUP.md` for detailed troubleshooting guide.

