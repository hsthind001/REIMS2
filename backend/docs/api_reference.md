# NLQ/RAG System API Reference

## Overview

Complete API reference for all NLQ/RAG system components.

## Hallucination Detector API

### Class: `HallucinationDetector`

#### `__init__(db: Session)`

Initialize the hallucination detector.

**Parameters**:
- `db` (Session): Database session for verifying claims

**Example**:
```python
from app.services.hallucination_detector import HallucinationDetector
detector = HallucinationDetector(db=db_session)
```

---

#### `detect_hallucinations(answer: str, sources: Optional[List[Dict[str, Any]]] = None, property_id: Optional[int] = None, period_id: Optional[int] = None) -> Dict[str, Any]`

Detect hallucinations in LLM answer by verifying numeric claims.

**Parameters**:
- `answer` (str): LLM-generated answer text
- `sources` (Optional[List[Dict[str, Any]]]): List of source documents/chunks used
- `property_id` (Optional[int]): Property ID for context
- `period_id` (Optional[int]): Period ID for context

**Returns**:
```python
{
    'has_hallucinations': bool,
    'claims': List[Dict],  # All extracted claims
    'flagged_claims': List[Dict],  # Unverified claims
    'verification_time_ms': float,
    'confidence_adjustment': float,  # Negative if hallucinations
    'total_claims': int,
    'verified_claims': int,
    'unverified_claims': int
}
```

**Raises**:
- `ValueError`: If answer is invalid
- `SQLAlchemyError`: If database query fails

**Example**:
```python
result = detector.detect_hallucinations(
    answer="The NOI was $1,234,567.89",
    property_id=1,
    period_id=1
)
```

---

#### `adjust_confidence(original_confidence: float, detection_result: Dict[str, Any]) -> float`

Adjust confidence score based on hallucination detection.

**Parameters**:
- `original_confidence` (float): Original confidence score (0-1)
- `detection_result` (Dict[str, Any]): Result from `detect_hallucinations()`

**Returns**:
- `float`: Adjusted confidence score (0-1)

**Example**:
```python
adjusted = detector.adjust_confidence(0.95, result)
```

---

#### `flag_for_review(nlq_query_id: int, user_id: int, answer: str, original_confidence: float, detection_result: Dict[str, Any], property_id: Optional[int] = None, period_id: Optional[int] = None) -> Optional[HallucinationReview]`

Flag answer for manual review if hallucinations detected.

**Parameters**:
- `nlq_query_id` (int): ID of the NLQ query
- `user_id` (int): User ID who asked the question
- `answer` (str): LLM-generated answer
- `original_confidence` (float): Original confidence score
- `detection_result` (Dict[str, Any]): Result from `detect_hallucinations()`
- `property_id` (Optional[int]): Property ID
- `period_id` (Optional[int]): Period ID

**Returns**:
- `Optional[HallucinationReview]`: Review object if flagged, None otherwise

**Example**:
```python
review = detector.flag_for_review(
    nlq_query_id=123,
    user_id=1,
    answer="The NOI was $1,234,567.89",
    original_confidence=0.95,
    detection_result=result
)
```

---

## Citation Extractor API

### Class: `CitationExtractor`

#### `__init__(db=None)`

Initialize citation extractor.

**Parameters**:
- `db` (Optional[Session]): Database session (optional, for SQL citation extraction)

**Example**:
```python
from app.services.citation_extractor import CitationExtractor
extractor = CitationExtractor(db=db_session)
```

---

#### `extract_citations(answer: str, retrieved_chunks: Optional[List[Dict[str, Any]]] = None, sql_queries: Optional[List[str]] = None, sql_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]`

Extract citations for all claims in answer.

**Parameters**:
- `answer` (str): LLM-generated answer text
- `retrieved_chunks` (Optional[List[Dict[str, Any]]]): List of retrieved document chunks (from RAG)
- `sql_queries` (Optional[List[str]]): List of SQL queries executed
- `sql_results` (Optional[List[Dict[str, Any]]]): List of SQL query results

**Returns**:
```python
{
    'citations': List[Citation],
    'extraction_time_ms': float,
    'total_claims': int,
    'cited_claims': int
}
```

**Raises**:
- `ValueError`: If answer is invalid
- `Exception`: If extraction fails (returns error in result)

**Example**:
```python
result = extractor.extract_citations(
    answer="The NOI was $1,234,567.89",
    retrieved_chunks=chunks
)
```

---

#### `format_citation_inline(citation: Citation) -> str`

Format citation as inline text.

**Parameters**:
- `citation` (Citation): Citation object to format

**Returns**:
- `str`: Formatted citation string

**Example**:
```python
formatted = extractor.format_citation_inline(citation)
# "$1,234,567.89 [Source: Income Statement, Page 2, Line 15]"
```

---

#### `format_citations_for_api(citations: List[Citation]) -> List[Dict[str, Any]]`

Format citations for API response.

**Parameters**:
- `citations` (List[Citation]): List of Citation objects

**Returns**:
- `List[Dict[str, Any]]`: List of formatted citation dictionaries

**Example**:
```python
api_citations = extractor.format_citations_for_api(citations)
```

---

## RAG Retrieval Service API

### Class: `RAGRetrievalService`

#### `__init__(db: Session, embedding_service: EmbeddingService = None)`

Initialize RAG retrieval service.

**Parameters**:
- `db` (Session): Database session
- `embedding_service` (Optional[EmbeddingService]): Embedding service (optional)

**Example**:
```python
from app.services.rag_retrieval_service import RAGRetrievalService
rag_service = RAGRetrievalService(db=db_session)
```

---

#### `retrieve_relevant_chunks(query: str, top_k: int = 5, property_id: Optional[int] = None, period_id: Optional[int] = None, document_type: Optional[str] = None, min_similarity: float = 0.3, use_pinecone: Optional[bool] = None, use_bm25: bool = False, bm25_weight: float = 0.5, use_rrf: bool = False, rrf_alpha: Optional[float] = None, rrf_k: Optional[int] = None, use_reranker: bool = False, rerank_top_n: Optional[int] = None, use_query_rewriting: bool = False, num_variations: Optional[int] = None) -> List[Dict]`

Retrieve relevant document chunks for a query.

**Parameters**:
- `query` (str): User's query text
- `top_k` (int): Number of top results to return (default: 5)
- `property_id` (Optional[int]): Filter by property
- `period_id` (Optional[int]): Filter by period
- `document_type` (Optional[str]): Filter by document type
- `min_similarity` (float): Minimum similarity threshold (0-1, default: 0.3)
- `use_pinecone` (Optional[bool]): Force use of Pinecone (True) or PostgreSQL (False). None = auto-detect
- `use_bm25` (bool): Enable BM25 keyword search (default: False)
- `bm25_weight` (float): Weight for BM25 scores in hybrid search (0-1, default: 0.5)
- `use_rrf` (bool): Use Reciprocal Rank Fusion instead of weighted combination (default: False)
- `rrf_alpha` (Optional[float]): Alpha parameter for RRF (0-1, default: 0.7)
- `rrf_k` (Optional[int]): K parameter for RRF (default: 60)
- `use_reranker` (bool): Enable cross-encoder reranking (default: False)
- `rerank_top_n` (Optional[int]): Number of candidates to rerank (default: 50)
- `use_query_rewriting` (bool): Enable LLM-based query rewriting (default: False)
- `num_variations` (Optional[int]): Number of query variations to generate (default: 3)

**Returns**:
- `List[Dict]`: List of relevant chunks with similarity scores

**Example**:
```python
chunks = rag_service.retrieve_relevant_chunks(
    query="What was NOI for Eastern Shore in Q3 2024?",
    top_k=10,
    use_rrf=True,
    use_reranker=True,
    property_id=1
)
```

---

## Correlation ID Middleware API

### Class: `CorrelationIDMiddleware`

#### `__init__(app: ASGIApp, header_name: str = "X-Correlation-ID")`

Initialize correlation ID middleware.

**Parameters**:
- `app` (ASGIApp): ASGI application
- `header_name` (str): Header name for correlation ID (default: "X-Correlation-ID")

**Example**:
```python
from app.middleware.correlation_id import CorrelationIDMiddleware
app.add_middleware(CorrelationIDMiddleware)
```

---

### Context Functions

#### `get_correlation_id() -> Optional[str]`

Get current correlation ID from context.

**Returns**:
- `Optional[str]`: Correlation ID string or None

**Example**:
```python
from app.middleware.correlation_id import get_correlation_id
correlation_id = get_correlation_id()
```

#### `set_user_id(user_id: int)`

Set user ID in context (automatically added to logs).

**Parameters**:
- `user_id` (int): User ID

**Example**:
```python
from app.middleware.correlation_id import set_user_id
set_user_id(123)
```

#### `get_user_id() -> Optional[int]`

Get user ID from context.

**Returns**:
- `Optional[int]`: User ID or None

#### `set_query_id(query_id: int)`

Set query ID in context.

**Parameters**:
- `query_id` (int): Query ID

#### `get_query_id() -> Optional[int]`

Get query ID from context.

**Returns**:
- `Optional[int]`: Query ID or None

#### `set_conversation_id(conversation_id: str)`

Set conversation ID in context.

**Parameters**:
- `conversation_id` (str): Conversation ID

#### `get_conversation_id() -> Optional[str]`

Get conversation ID from context.

**Returns**:
- `Optional[str]`: Conversation ID or None

#### `set_property_id(property_id: int)`

Set property ID in context.

**Parameters**:
- `property_id` (int): Property ID

#### `get_property_id() -> Optional[int]`

Get property ID from context.

**Returns**:
- `Optional[int]`: Property ID or None

---

## Data Models

### Claim

Represents an extracted numeric claim.

```python
class Claim:
    claim_type: str  # 'currency', 'percentage', 'date', 'ratio'
    value: float
    original_text: str
    context: Optional[str]
    verified: bool
    verification_source: Optional[str]
    verification_score: float
    tolerance_applied: Optional[float]
```

### Citation

Represents a citation for a claim.

```python
class Citation:
    citation_type: str  # 'document' or 'sql'
    claim_text: str
    sources: List[Dict[str, Any]]
    confidence: float
```

## Error Codes

### Hallucination Detector Errors

- `ValueError`: Invalid input (empty answer, invalid property_id)
- `SQLAlchemyError`: Database connection/query errors

### Citation Extractor Errors

- `ValueError`: Invalid input (empty answer, invalid chunks)
- `Exception`: General extraction errors (returns error in result)

### RAG Retrieval Errors

- `ValueError`: Invalid query or parameters
- `ConnectionError`: Pinecone/PostgreSQL connection errors
- `TimeoutError`: Operation timeout

## Response Formats

### Hallucination Detection Result

```json
{
    "has_hallucinations": false,
    "claims": [
        {
            "claim_type": "currency",
            "value": 1234567.89,
            "original_text": "$1,234,567.89",
            "verified": true,
            "verification_source": "database"
        }
    ],
    "flagged_claims": [],
    "verification_time_ms": 45.2,
    "confidence_adjustment": 0.0,
    "total_claims": 1,
    "verified_claims": 1,
    "unverified_claims": 0
}
```

### Citation Extraction Result

```json
{
    "citations": [
        {
            "claim": "$1,234,567.89",
            "sources": [
                {
                    "type": "document",
                    "document_type": "income_statement",
                    "page": 2,
                    "line": 15,
                    "confidence": 0.95
                }
            ],
            "confidence": 0.95,
            "type": "document"
        }
    ],
    "extraction_time_ms": 23.5,
    "total_claims": 1,
    "cited_claims": 1
}
```

### Retrieval Result

```json
[
    {
        "chunk_id": 1,
        "chunk_text": "The net operating income was $1,234,567.89",
        "similarity": 0.95,
        "property_code": "ESP",
        "property_name": "Eastern Shore Plaza",
        "period": "2024-09",
        "document_type": "income_statement",
        "file_name": "income_statement_q3_2024.pdf",
        "retrieval_method": "pinecone"
    }
]
```

## Rate Limits

No rate limits enforced at service level. Rate limiting handled at API gateway level.

## Authentication

Services don't handle authentication directly. Authentication handled at API endpoint level.

## Versioning

Current version: `1.0.0`

API versioning handled via URL path: `/api/v1/...`

## Related Documentation

- [Hallucination Detector](./hallucination_detector.md)
- [Citation Extractor](./citation_extractor.md)
- [RAG Retrieval Service](./rag_retrieval_service.md)
- [Structured Logging](./structured_logging_guide.md)
- [Correlation ID Middleware](./correlation_id_middleware.md)

