# Citation Extraction Guide

## Overview

Citation extraction provides granular, sentence-level citations for every claim in LLM-generated answers. Each numeric claim is linked to its exact source location (document type, page number, line number) for verification.

## Architecture

```
LLM Answer
    ↓
[Citation Extractor]
    ├─ Extract Claims (from answer)
    ├─ Match Claims to Sources
    │   ├─ Document Chunks (RAG results)
    │   └─ SQL Results
    ├─ Extract Metadata (page, line, coordinates)
    └─ Format Citations
    ↓
[Formatted Citations]
    └─ Ready for display in UI
```

## Citation Format

### Citation Structure

```python
{
    'claim': 'The NOI was $1,234,567.89',
    'sources': [
        {
            'type': 'document',
            'document_type': 'income_statement',
            'document_id': 10,
            'chunk_id': 1,
            'file_name': 'income_q3_2024.pdf',
            'page': 2,
            'line': 15,
            'coordinates': {
                'x0': 100.5,
                'y0': 200.3,
                'x1': 300.7,
                'y1': 220.1
            },
            'excerpt': '...Net Operating Income: $1,234,567.89...',
            'confidence': 0.95
        },
        {
            'type': 'sql',
            'query': 'SELECT net_operating_income FROM financial_metrics WHERE property_id = 1',
            'value': 1234567.89,
            'confidence': 0.95
        }
    ],
    'confidence': 0.95,
    'type': 'document'
}
```

## Usage

### Basic Citation Extraction

```python
from app.services.citation_extractor import CitationExtractor
from app.db.database import SessionLocal

db = SessionLocal()
extractor = CitationExtractor(db)

# Extract citations from answer
answer = "The NOI was $1.2M for the property."

retrieved_chunks = [
    {
        'chunk_id': 1,
        'chunk_text': 'Net Operating Income: $1,200,000',
        'document_type': 'income_statement',
        'document_id': 10,
        'file_name': 'income_q3_2024.pdf',
        'metadata': {'page': 2, 'line': 15}
    }
]

result = extractor.extract_citations(
    answer=answer,
    retrieved_chunks=retrieved_chunks
)

print(f"Total claims: {result['total_claims']}")
print(f"Cited claims: {result['cited_claims']}")
print(f"Citations: {result['citations']}")
```

### With SQL Citations

```python
sql_queries = [
    'SELECT net_operating_income FROM financial_metrics WHERE property_id = 1'
]

sql_results = [
    {'net_operating_income': 1200000.0}
]

result = extractor.extract_citations(
    answer="The NOI was $1.2M.",
    retrieved_chunks=retrieved_chunks,
    sql_queries=sql_queries,
    sql_results=sql_results
)
```

### Integration with NLQ Service

```python
from app.services.nlq_service import NLQService
from app.services.citation_extractor import CitationExtractor

nlq_service = NLQService(db)
citation_extractor = CitationExtractor(db)

# Process query
nlq_result = nlq_service.process_query(
    query="What was NOI for Property X?",
    property_id=1
)

# Extract citations
citations = citation_extractor.extract_citations(
    answer=nlq_result['answer'],
    retrieved_chunks=nlq_result.get('sources', []),
    sql_queries=[nlq_result.get('sql_query')] if nlq_result.get('sql_query') else None,
    sql_results=[nlq_result.get('data_retrieved')] if nlq_result.get('data_retrieved') else None
)

# Add citations to result
nlq_result['citations'] = citations['citations']
```

## Frontend Integration

### Using Citation Component

```typescript
import { CitationList } from '@/components/Citation';

function NLQAnswer({ answer, citations }) {
  return (
    <Box>
      <Typography>{answer}</Typography>
      <CitationList
        citations={citations}
        onSourceClick={(source) => {
          // Navigate to document viewer
          if (source.type === 'document') {
            navigate(`/documents/${source.document_id}?page=${source.page}`);
          }
        }}
      />
    </Box>
  );
}
```

### Using Inline Citation

```typescript
import { InlineCitation } from '@/components/CitationInline';

function NLQAnswer({ answer, citations }) {
  return (
    <Box>
      <InlineCitation
        text={answer}
        citations={citations}
        onSourceClick={(source) => {
          // Handle source click
        }}
      />
    </Box>
  );
}
```

## Claim Matching

### Matching Algorithm

1. **Exact Match**: Search for exact claim text in chunk
2. **Fuzzy Match**: Use fuzzy string matching (fuzzywuzzy) if exact match fails
3. **Value Match**: For numeric claims, search for matching values with tolerance
4. **Context Match**: Consider surrounding context for better matching

### Matching Thresholds

- **Exact Match**: Confidence = 1.0
- **Fuzzy Match**: Confidence >= 0.8 (configurable)
- **Value Match**: Confidence = 0.9 (within tolerance)

## Metadata Extraction

### Page Numbers

Extracted from chunk metadata:
```python
chunk['metadata']['page']  # or chunk['page_number']
```

### Line Numbers

Extracted from chunk metadata:
```python
chunk['metadata']['line']  # or chunk['line_number']
```

### PDF Coordinates

Extracted from chunk metadata:
```python
chunk['metadata']['x0']  # Left coordinate
chunk['metadata']['y0']  # Top coordinate
chunk['metadata']['x1']  # Right coordinate
chunk['metadata']['y1']  # Bottom coordinate
```

## Citation Formatting

### Inline Format

```python
formatted = extractor.format_citation_inline(citation)
# "The NOI was $1.2M [Source: Income Statement, Page 2, Line 15]"
```

### API Format

```python
formatted = extractor.format_citations_for_api(citations)
# Returns list of citation dictionaries
```

## Deduplication

### Deduplication Strategy

- **Document Sources**: Deduplicate by document_id + chunk_id + page
- **SQL Sources**: Deduplicate by query hash
- **Threshold**: 0.9 similarity for deduplication

### Example

```python
# Before deduplication
citations = [
    Citation(claim="NOI $1.2M", sources=[source1, source1_duplicate]),
    Citation(claim="NOI $1.2M", sources=[source2])
]

# After deduplication
citations = [
    Citation(claim="NOI $1.2M", sources=[source1]),
    Citation(claim="NOI $1.2M", sources=[source2])
]
```

## Configuration

### Citation Settings

```python
from app.config.citation_config import citation_config

# Extraction settings
citation_config.EXTRACT_FOR_ALL_CLAIMS = True
citation_config.MIN_CONFIDENCE_THRESHOLD = 0.7
citation_config.MAX_SOURCES_PER_CLAIM = 3

# Matching settings
citation_config.FUZZY_MATCH_THRESHOLD = 0.8
citation_config.EXCERPT_WINDOW = 100

# Format settings
citation_config.INCLUDE_PAGE_NUMBER = True
citation_config.INCLUDE_LINE_NUMBER = True
citation_config.INCLUDE_EXCERPT = True
```

### Environment Variables

```bash
# Extraction
export CITATION_EXTRACT_ALL="true"
export CITATION_MIN_CONFIDENCE=0.7
export CITATION_MAX_SOURCES=3

# Matching
export CITATION_FUZZY_THRESHOLD=0.8
export CITATION_EXCERPT_WINDOW=100

# Format
export CITATION_INCLUDE_PAGE="true"
export CITATION_INCLUDE_LINE="true"
export CITATION_INCLUDE_EXCERPT="true"

# Performance
export CITATION_TARGET_TIME_MS=200
```

## Examples

### Example 1: Income Statement Citation

**Answer**: "The NOI was $1,234,567.89 for the property."

**Citation**:
```json
{
  "claim": "The NOI was $1,234,567.89",
  "sources": [
    {
      "type": "document",
      "document_type": "income_statement",
      "page": 2,
      "line": 15,
      "file_name": "income_q3_2024.pdf",
      "excerpt": "...Net Operating Income: $1,234,567.89...",
      "confidence": 0.95
    }
  ]
}
```

### Example 2: Multiple Sources

**Answer**: "The NOI was $1.2M with 85% occupancy."

**Citations**:
```json
[
  {
    "claim": "The NOI was $1.2M",
    "sources": [
      {
        "type": "document",
        "document_type": "income_statement",
        "page": 2
      }
    ]
  },
  {
    "claim": "85% occupancy",
    "sources": [
      {
        "type": "document",
        "document_type": "rent_roll",
        "page": 1
      }
    ]
  }
]
```

### Example 3: SQL Citation

**Answer**: "The NOI was $1.2M."

**Citation**:
```json
{
  "claim": "The NOI was $1.2M",
  "sources": [
    {
      "type": "sql",
      "query": "SELECT net_operating_income FROM financial_metrics WHERE property_id = 1",
      "value": 1200000.0,
      "confidence": 0.95
    }
  ]
}
```

## Click-to-Source Navigation

### Document Navigation

```typescript
function handleSourceClick(source: CitationSource) {
  if (source.type === 'document' && source.document_id) {
    // Navigate to document viewer with page
    navigate(`/documents/${source.document_id}?page=${source.page || 1}`);
    
    // Or scroll to specific coordinates if available
    if (source.coordinates) {
      scrollToCoordinates(source.coordinates);
    }
  }
}
```

### SQL Query Display

```typescript
function handleSourceClick(source: CitationSource) {
  if (source.type === 'sql' && source.query) {
    // Show SQL query in modal or sidebar
    setShowSQLModal(true);
    setSQLQuery(source.query);
  }
}
```

## Performance

### Extraction Time Target: <200ms

**Breakdown**:
- Claim extraction: <10ms
- Source matching: ~100-150ms
- Citation formatting: <10ms
- Total: <200ms

**Optimization**:
- Limit source checks per claim
- Cache matching results
- Parallel source matching

## Best Practices

1. **Always Extract Citations**: Run extraction on all LLM answers
2. **Use Retrieved Chunks**: Pass RAG retrieval results for better matching
3. **Include SQL Queries**: Include SQL queries/results for database citations
4. **Deduplicate Sources**: Enable deduplication to avoid clutter
5. **Display Confidently**: Show confidence scores for transparency
6. **Enable Click-to-Source**: Make citations clickable for navigation

## Troubleshooting

### No Citations Extracted

**Possible Causes**:
- No claims in answer
- No matching chunks
- Matching threshold too high

**Solutions**:
- Verify claims are extracted
- Check retrieved chunks
- Lower fuzzy match threshold

### Missing Metadata

**Possible Causes**:
- Chunks don't have metadata
- Metadata format incorrect
- Page/line numbers not extracted

**Solutions**:
- Ensure chunks have metadata
- Verify metadata format
- Check extraction logic

### Low Confidence Citations

**Possible Causes**:
- Fuzzy matching only
- Value mismatch
- Context mismatch

**Solutions**:
- Improve chunk retrieval
- Adjust matching threshold
- Enhance matching algorithm

## Success Criteria

- ✅ Every numeric claim has citation
- ✅ Citations include: document type, page number, line number
- ✅ Citations clickable to jump to source
- ✅ Citation format consistent
- ✅ Multiple sources for same claim de-duplicated
- ✅ Extraction time <200ms
- ✅ Frontend component for display
- ✅ Click-to-source navigation

## Future Enhancements

- **Visual Highlighting**: Highlight cited text in source documents
- **Citation Confidence**: Show confidence scores in UI
- **Citation History**: Track citation accuracy over time
- **Auto-Verification**: Automatically verify citations
- **Citation Analytics**: Analyze citation patterns

