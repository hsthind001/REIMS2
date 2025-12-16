# REIMS2 NLQ/RAG System Documentation

## Overview

The Natural Language Query (NLQ) and Retrieval-Augmented Generation (RAG) system enables users to query real estate financial data using natural language. The system combines semantic search, keyword search, and LLM-based answer generation to provide accurate, cited responses.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Query                              │
│                    "What was NOI for Q3?"                       │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Query Processing                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Query Router │  │ Query        │  │ Entity       │          │
│  │              │→ │ Rewriter     │→ │ Resolver     │          │
│  │ (Complexity) │  │ (Variations) │  │ (Fuzzy Match)│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Hybrid Retrieval                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Semantic     │  │ BM25         │  │ SQL          │          │
│  │ Search       │  │ Keyword      │  │ Query        │          │
│  │ (Pinecone)   │  │ Search       │  │ Execution    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                  │
│                              │                                    │
│                              ▼                                    │
│                    ┌──────────────┐                               │
│                    │ RRF Fusion   │                               │
│                    │ (Ranking)    │                               │
│                    └──────────────┘                               │
│                              │                                    │
│                              ▼                                    │
│                    ┌──────────────┐                               │
│                    │ Reranker     │                               │
│                    │ (Cross-Enc)  │                               │
│                    └──────────────┘                               │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Answer Generation                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ LLM          │  │ Hallucination │  │ Citation     │          │
│  │ (GPT-4o)     │→ │ Detector     │→ │ Extractor    │          │
│  │              │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Response with Citations                       │
│  {                                                               │
│    "answer": "The NOI was $1,234,567.89",                       │
│    "confidence": 0.95,                                          │
│    "citations": [...],                                           │
│    "sources": [...]                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Hallucination Detector
Detects and verifies numeric claims in LLM-generated answers against source data.

**Location**: `backend/app/services/hallucination_detector.py`

**Key Features**:
- Extracts numeric claims (currency, percentage, date, ratio)
- Verifies claims against database and documents
- Flags unverified claims for review
- Adjusts confidence scores

### 2. Citation Extractor
Extracts granular citations for every claim in LLM answers.

**Location**: `backend/app/services/citation_extractor.py`

**Key Features**:
- Sentence-level citations
- Exact source locations (page, line, coordinates)
- Document and SQL source tracking
- Citation formatting

### 3. RAG Retrieval Service
Hybrid retrieval combining semantic and keyword search.

**Location**: `backend/app/services/rag_retrieval_service.py`

**Key Features**:
- Semantic search (Pinecone/PostgreSQL)
- BM25 keyword search
- Reciprocal Rank Fusion (RRF)
- Cross-encoder reranking
- Query rewriting

### 4. Structured Logging
JSON logging with correlation IDs and context.

**Location**: `backend/app/monitoring/logging_config.py`

**Key Features**:
- JSON format logs
- Correlation ID tracking
- Sensitive data filtering
- Log sampling
- ELK Stack integration

### 5. Correlation ID Middleware
Adds correlation IDs to requests for distributed tracing.

**Location**: `backend/app/middleware/correlation_id.py`

**Key Features**:
- Automatic UUID generation
- Request/response header tracking
- Context variable management

## Quick Start

### Installation

```bash
cd backend
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
# OpenAI API
export OPENAI_API_KEY="your-key"

# Pinecone
export PINECONE_API_KEY="your-key"
export PINECONE_ENVIRONMENT="us-east-1-aws"

# Database
export DATABASE_URL="postgresql://user:pass@localhost/reims"
```

### Basic Usage

```python
from app.services.rag_retrieval_service import RAGRetrievalService
from app.services.hallucination_detector import HallucinationDetector
from app.services.citation_extractor import CitationExtractor
from sqlalchemy.orm import Session

# Initialize services
rag_service = RAGRetrievalService(db=db_session)
detector = HallucinationDetector(db=db_session)
extractor = CitationExtractor(db=db_session)

# Retrieve relevant chunks
chunks = rag_service.retrieve_relevant_chunks(
    query="What was NOI for Eastern Shore in Q3 2024?",
    top_k=10,
    use_rrf=True,
    use_reranker=True
)

# Generate answer (using LLM)
answer = generate_answer(query, chunks)

# Detect hallucinations
detection_result = detector.detect_hallucinations(
    answer=answer,
    sources=chunks,
    property_id=1,
    period_id=1
)

# Extract citations
citations = extractor.extract_citations(
    answer=answer,
    retrieved_chunks=chunks
)
```

## Documentation Index

- [Hallucination Detector](./hallucination_detector.md)
- [Citation Extractor](./citation_extractor.md)
- [RAG Retrieval Service](./rag_retrieval_service.md)
- [Structured Logging](./structured_logging_guide.md)
- [Correlation ID Middleware](./correlation_id_middleware.md)
- [Testing Guide](../tests/README_TESTING.md)

## Performance Targets

- **Query Latency**: <500ms (simple), <2s (complex)
- **Retrieval Latency**: <100ms (semantic), <50ms (BM25)
- **Reranking Latency**: <200ms (50 candidates)
- **Hallucination Detection**: <100ms
- **Citation Extraction**: <200ms

## Monitoring

- **Metrics**: Prometheus metrics at `/metrics`
- **Logs**: Structured JSON logs with correlation IDs
- **Dashboards**: Kibana dashboards for query analysis

## Support

For issues or questions:
1. Check component-specific documentation
2. Review error logs with correlation ID
3. Check Prometheus metrics
4. Review Kibana dashboards

