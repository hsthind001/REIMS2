# Citation Extractor Service

## Overview

The Citation Extractor service provides granular, sentence-level citations for every claim in LLM-generated answers. It matches claims to source documents and SQL query results, extracting exact locations (page numbers, line numbers, coordinates) for precise citation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              LLM Answer + Retrieved Chunks                   │
│  Answer: "The NOI was $1,234,567.89"                       │
│  Chunks: [{chunk_text: "...", metadata: {...}}]            │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Claim Extraction                                │
│  (Uses HallucinationDetector or manual extraction)         │
│  Claims: [                                                  │
│    {type: 'currency', value: 1234567.89, text: '$1.2M'}    │
│  ]                                                           │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Citation Matching                               │
│  ┌──────────────┐              ┌──────────────┐           │
│  │ Document      │              │ SQL Results  │           │
│  │ Matching      │              │ Matching     │           │
│  │ (Fuzzy/Exact) │              │ (Value Match)│           │
│  └──────────────┘              └──────────────┘           │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Citation Formatting                             │
│  {                                                           │
│    "claim": "$1,234,567.89",                                │
│    "sources": [                                              │
│      {                                                        │
│        "type": "document",                                   │
│        "document_type": "income_statement",                  │
│        "page": 2,                                            │
│        "line": 15,                                           │
│        "excerpt": "..."                                      │
│      }                                                        │
│    ]                                                          │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Installation

No additional installation required. Dependencies are included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

**Optional**: For better fuzzy matching:
```bash
pip install fuzzywuzzy python-Levenshtein
```

## Usage

### Basic Usage

```python
from app.services.citation_extractor import CitationExtractor
from sqlalchemy.orm import Session

# Initialize extractor
extractor = CitationExtractor(db=db_session)

# Extract citations
result = extractor.extract_citations(
    answer="The NOI was $1,234,567.89 for Q3 2024.",
    retrieved_chunks=chunks,  # From RAG retrieval
    sql_queries=["SELECT noi FROM metrics"],  # Optional
    sql_results=[{'noi': 1234567.89}]  # Optional
)

# Access citations
for citation in result['citations']:
    print(f"Claim: {citation['claim']}")
    for source in citation['sources']:
        print(f"  Source: {source['type']} - Page {source.get('page', 'N/A')}")
```

### With Document Chunks Only

```python
chunks = [
    {
        'chunk_text': 'The net operating income was $1,234,567.89',
        'chunk_id': 1,
        'document_type': 'income_statement',
        'metadata': {
            'page': 2,
            'line': 15,
            'x0': 100, 'y0': 200, 'x1': 500, 'y1': 250
        }
    }
]

result = extractor.extract_citations(
    answer="The NOI was $1,234,567.89",
    retrieved_chunks=chunks
)
```

### With SQL Results

```python
sql_queries = [
    "SELECT net_operating_income FROM financial_metrics WHERE property_id = 1"
]
sql_results = [
    {'net_operating_income': 1234567.89}
]

result = extractor.extract_citations(
    answer="The NOI was $1,234,567.89",
    sql_queries=sql_queries,
    sql_results=sql_results
)
```

### Formatting Citations

```python
# Format for inline display
for citation in result['citations']:
    formatted = extractor.format_citation_inline(citation)
    print(formatted)
    # Output: "$1,234,567.89 [Source: Income Statement, Page 2, Line 15]"

# Format for API response
api_citations = extractor.format_citations_for_api(result['citations'])
```

## API Reference

### CitationExtractor

#### `__init__(db=None)`

Initialize citation extractor.

**Args**:
- `db`: Database session (optional, for SQL citation extraction)

**Example**:
```python
extractor = CitationExtractor(db=db_session)
```

---

#### `extract_citations(answer: str, retrieved_chunks: Optional[List[Dict]] = None, sql_queries: Optional[List[str]] = None, sql_results: Optional[List[Dict]] = None) -> Dict[str, Any]`

Extract citations for all claims in answer.

**Args**:
- `answer`: LLM-generated answer text
- `retrieved_chunks`: List of retrieved document chunks (from RAG)
- `sql_queries`: List of SQL queries executed (optional)
- `sql_results`: List of SQL query results (optional)

**Returns**:
Dictionary with citations:
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

**Args**:
- `citation`: Citation object to format

**Returns**:
Formatted citation string

**Example**:
```python
formatted = extractor.format_citation_inline(citation)
# "$1,234,567.89 [Source: Income Statement, Page 2, Line 15]"
```

---

#### `format_citations_for_api(citations: List[Citation]) -> List[Dict[str, Any]]`

Format citations for API response.

**Args**:
- `citations`: List of Citation objects

**Returns**:
List of formatted citation dictionaries

**Example**:
```python
api_citations = extractor.format_citations_for_api(citations)
```

## Configuration

Configuration is managed in `backend/app/config/citation_config.py`:

```python
# Matching settings
MIN_CONFIDENCE = 0.7  # Minimum confidence for citation match
FUZZY_MATCH_THRESHOLD = 0.8  # Fuzzy matching threshold
MAX_SOURCES_PER_CLAIM = 3  # Maximum sources per claim

# Citation format
INCLUDE_PAGE_NUMBER = True
INCLUDE_LINE_NUMBER = True
INCLUDE_EXCERPT = True
EXCERPT_WINDOW = 100  # Characters around match
INCLUDE_SQL_CITATIONS = True

# Deduplication
DEDUPLICATE_SOURCES = True  # Remove duplicate sources
```

## Citation Format

### Document Citation

```json
{
    "type": "document",
    "document_type": "income_statement",
    "chunk_id": 1,
    "document_id": 1,
    "file_name": "income_statement_q3_2024.pdf",
    "page": 2,
    "line": 15,
    "coordinates": {
        "x0": 100,
        "y0": 200,
        "x1": 500,
        "y1": 250
    },
    "excerpt": "...net operating income was $1,234,567.89...",
    "confidence": 0.95
}
```

### SQL Citation

```json
{
    "type": "sql",
    "query": "SELECT net_operating_income FROM financial_metrics WHERE property_id = 1",
    "value": 1234567.89,
    "confidence": 0.95
}
```

## Matching Strategies

### Exact Matching

First attempts exact text match:
```python
claim_text = "$1,234,567.89"
chunk_text = "The NOI was $1,234,567.89"
# Match found with confidence 1.0
```

### Fuzzy Matching

If exact match fails, uses fuzzy matching:
```python
from fuzzywuzzy import fuzz

similarity = fuzz.ratio(claim_text, chunk_text) / 100.0
# Returns similarity score (0-1)
```

### Value Matching

For numeric claims, matches values within tolerance:
```python
claim_value = 1234567.89
chunk_value = 1234567.90  # From extracted text
tolerance = 0.05  # 5%

if abs(claim_value - chunk_value) / claim_value <= tolerance:
    # Match found
```

## Error Handling

### Missing Chunks

```python
# Empty chunks list
result = extractor.extract_citations(
    answer="The NOI was $1,234,567.89",
    retrieved_chunks=[]
)
# Returns: {'citations': [], 'total_claims': 1, 'cited_claims': 0}
```

### Invalid Input

```python
# None answer
result = extractor.extract_citations(None)
# Returns: {'citations': [], 'total_claims': 0, 'cited_claims': 0}
```

### Extraction Errors

```python
try:
    result = extractor.extract_citations(answer, chunks)
except Exception as e:
    # Error included in result
    if 'error' in result:
        logger.error(f"Citation extraction failed: {result['error']}")
```

## Performance Considerations

### Optimization Tips

1. **Limit Sources**: Use `MAX_SOURCES_PER_CLAIM` to limit sources per claim
2. **Fuzzy Matching**: Use `fuzzywuzzy` for better matching (optional)
3. **Batch Processing**: Process multiple citations in batch
4. **Caching**: Cache citation results for repeated queries

### Performance Targets

- **Extraction**: <200ms for typical answer
- **Matching**: <50ms per claim
- **Formatting**: <10ms per citation

## Testing

### Unit Tests

```bash
pytest tests/services/test_citation_extractor.py -v
```

### Test Coverage

```bash
pytest tests/services/test_citation_extractor.py --cov=app.services.citation_extractor --cov-report=html
```

## Troubleshooting

### No Citations Extracted

**Issue**: No citations found for claims.

**Solutions**:
- Check chunks contain claim values
- Verify fuzzy matching threshold (may be too high)
- Check claim extraction (may not be extracting claims)
- Verify chunk metadata (page, line numbers)

### Low Confidence Citations

**Issue**: Citations have low confidence scores.

**Solutions**:
- Lower `FUZZY_MATCH_THRESHOLD`
- Improve chunk text quality
- Use exact matching when possible
- Check claim value format matches chunk format

### Missing Metadata

**Issue**: Citations missing page/line numbers.

**Solutions**:
- Verify chunk metadata includes page/line
- Check `INCLUDE_PAGE_NUMBER` and `INCLUDE_LINE_NUMBER` config
- Ensure document processor extracts metadata

### Performance Issues

**Issue**: Citation extraction is slow.

**Solutions**:
- Limit `MAX_SOURCES_PER_CLAIM`
- Reduce `EXCERPT_WINDOW` size
- Use caching for repeated queries
- Optimize fuzzy matching

## Examples

### Example 1: Simple Citation

```python
answer = "The NOI was $1,234,567.89"
chunks = [
    {
        'chunk_text': 'The net operating income was $1,234,567.89',
        'metadata': {'page': 2, 'line': 15}
    }
]

result = extractor.extract_citations(answer, chunks)

# Result:
# {
#     'citations': [
#         {
#             'claim': '$1,234,567.89',
#             'sources': [
#                 {
#                     'type': 'document',
#                     'page': 2,
#                     'line': 15,
#                     'confidence': 1.0
#                 }
#             ]
#         }
#     ],
#     'total_claims': 1,
#     'cited_claims': 1
# }
```

### Example 2: Multiple Sources

```python
answer = "The NOI was $1,234,567.89"
chunks = [
    {'chunk_text': 'NOI: $1,234,567.89', 'metadata': {'page': 2}},
    {'chunk_text': 'Net operating income was $1,234,567.89', 'metadata': {'page': 3}}
]

result = extractor.extract_citations(answer, chunks)

# Multiple sources for same claim
```

### Example 3: SQL Citation

```python
answer = "The NOI was $1,234,567.89"
sql_queries = ["SELECT noi FROM metrics WHERE property_id = 1"]
sql_results = [{'noi': 1234567.89}]

result = extractor.extract_citations(
    answer=answer,
    sql_queries=sql_queries,
    sql_results=sql_results
)

# SQL citation included
```

## Related Documentation

- [Hallucination Detector](./hallucination_detector.md)
- [RAG Retrieval Service](./rag_retrieval_service.md)
- [Testing Guide](../tests/README_TESTING.md)

