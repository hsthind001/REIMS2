# REIMS2 NLQ/RAG System Documentation

## Overview

This directory contains comprehensive documentation for the Natural Language Query (NLQ) and Retrieval-Augmented Generation (RAG) system in REIMS2.

## Documentation Index

### System Overview
- **[NLQ/RAG System Overview](./nlq_rag_system_overview.md)**: High-level architecture and component overview

### Core Services
- **[Hallucination Detector](./hallucination_detector.md)**: Detects and verifies numeric claims in LLM answers
- **[Citation Extractor](./citation_extractor.md)**: Extracts granular citations for claims
- **[RAG Retrieval Service](./rag_retrieval_service.md)**: Hybrid retrieval combining semantic and keyword search

### Infrastructure
- **[Structured Logging](./structured_logging_guide.md)**: JSON logging with correlation IDs
- **[Correlation ID Middleware](./correlation_id_middleware.md)**: Request tracing middleware

### Testing
- **[Testing Guide](../tests/README_TESTING.md)**: Comprehensive testing documentation

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

## Architecture

```
User Query
    ↓
Query Processing (Router, Rewriter, Entity Resolver)
    ↓
Hybrid Retrieval (Semantic + BM25 + SQL)
    ↓
RRF Fusion + Reranking
    ↓
Answer Generation (LLM)
    ↓
Hallucination Detection
    ↓
Citation Extraction
    ↓
Response with Citations
```

## Components

### 1. Hallucination Detector
- Extracts numeric claims (currency, percentage, date, ratio)
- Verifies claims against database and documents
- Flags unverified claims for review
- Adjusts confidence scores

### 2. Citation Extractor
- Extracts sentence-level citations
- Matches claims to source documents
- Includes exact locations (page, line, coordinates)
- Formats citations for display

### 3. RAG Retrieval Service
- Semantic search (Pinecone/PostgreSQL)
- BM25 keyword search
- Reciprocal Rank Fusion (RRF)
- Cross-encoder reranking
- Query rewriting

### 4. Structured Logging
- JSON format logs
- Correlation ID tracking
- Sensitive data filtering
- ELK Stack integration

### 5. Correlation ID Middleware
- Automatic UUID generation
- Request/response header tracking
- Context variable management

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

## Testing

Run tests:

```bash
# All tests
pytest

# Specific component
pytest tests/services/test_hallucination_detector.py

# With coverage
pytest --cov=app --cov-report=html
```

## Support

For issues or questions:
1. Check component-specific documentation
2. Review error logs with correlation ID
3. Check Prometheus metrics
4. Review Kibana dashboards

## Contributing

When adding new components:
1. Add comprehensive docstrings (Google style)
2. Update relevant documentation
3. Add unit tests (>80% coverage)
4. Update this README if needed

