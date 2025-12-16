# Enhanced Document Processor Guide

## Overview

The Enhanced Document Processor is a table-aware document processing system designed to preserve financial table structure during chunking, enabling better LLM understanding and more accurate RAG retrieval.

## Features

- **Table Extraction**: Uses Camelot (stream + lattice modes) for accurate table detection
- **Semantic Text Chunking**: LangChain RecursiveCharacterTextSplitter with 100-token overlap
- **Structure Preservation**: Tables converted to markdown format for better LLM understanding
- **Hierarchy**: Parent-child relationships (headers → content)
- **Metadata Enrichment**: PDF coordinates, page numbers, chunk types
- **Dual Storage**: PostgreSQL (document_chunks) + Pinecone (embeddings)

## Architecture

```
PDF Document
    ↓
[Table Extraction] (Camelot)
    ↓
[Text Extraction] (PyMuPDF/PDFPlumber)
    ↓
[Semantic Chunking] (LangChain RecursiveCharacterTextSplitter)
    ↓
[Header Detection] → [Parent-Child Relationships]
    ↓
[Metadata Enrichment] (coordinates, page numbers, types)
    ↓
[Save to PostgreSQL] → [Generate Embeddings] → [Sync to Pinecone]
```

## Chunking Strategy

### Text Chunking

- **Chunk Size**: 1000 tokens (configurable, default ~4000 characters)
- **Overlap**: 100 tokens (~400 characters) to maintain context
- **Separators**: Respects paragraph breaks, sentence boundaries, word boundaries
- **Method**: RecursiveCharacterTextSplitter from LangChain

### Table Extraction

- **Primary Method**: Camelot Lattice (for bordered tables)
- **Fallback Method**: Camelot Stream (for borderless tables)
- **Output Format**: Markdown tables for better LLM understanding
- **Multi-page Support**: Automatically detects and merges tables across pages
- **Filtering**: Tables must have minimum 2 rows and 2 columns

### Parent-Child Relationships

- **Header Detection**: Identifies headers using:
  - Text formatting (all caps, title case)
  - Position on page (top 15% of page)
  - Common header patterns (Balance Sheet, Income Statement, etc.)
  - Header levels: 1 (main sections), 2 (subsections), 3 (sub-subsections)

- **Content Association**: Links content chunks to nearest preceding header
- **Maximum Distance**: 500 characters between header and content
- **Search Range**: Looks back up to 3 chunks for parent header

## Chunk Types

### Text Chunks (`chunk_type: 'text'`)
- Regular document text
- Chunked with overlap for context preservation
- Linked to parent headers when available

### Table Chunks (`chunk_type: 'table'`)
- Extracted tables converted to markdown
- Includes table metadata (rows, columns, accuracy)
- Preserves table structure for LLM understanding

### Header Chunks (`chunk_type: 'header'`)
- Section headers and titles
- Acts as parent for following content chunks
- Includes header level (1-3) in metadata

## Metadata Structure

Each chunk includes enriched metadata:

```json
{
  "chunk_type": "text|table|header",
  "page_number": 1,
  "coordinates": {
    "x0": 10.0,
    "y0": 20.0,
    "x1": 100.0,
    "y1": 200.0
  },
  "table_index": 1,  // For table chunks
  "parent_chunk_id": 5,  // For child chunks
  "header_level": 1,  // For header chunks
  "token_count": 250,
  "table_metadata": {  // For table chunks
    "rows": 10,
    "columns": 5,
    "accuracy": 95.0,
    "flavor": "lattice"
  }
}
```

## Usage

### Basic Usage

```python
from app.services.document_processor_enhanced import EnhancedDocumentProcessor
from app.db.database import SessionLocal

db = SessionLocal()
processor = EnhancedDocumentProcessor(db)

# Process a document
result = processor.process_document(
    document_id=123,
    pdf_data=pdf_bytes,
    generate_embeddings=True,
    sync_to_pinecone=True
)

print(f"Created {result['statistics']['total_chunks']} chunks")
print(f"Text: {result['statistics']['text_chunks']}")
print(f"Tables: {result['statistics']['table_chunks']}")
print(f"Headers: {result['statistics']['header_chunks']}")
```

### Integration with Extraction Orchestrator

The enhanced processor is automatically integrated into the extraction workflow:

```python
from app.services.extraction_orchestrator import ExtractionOrchestrator

orchestrator = ExtractionOrchestrator(db)

# Extract and parse document (includes chunking)
result = orchestrator.extract_and_parse_document(upload_id=123)
```

The processor runs automatically after successful extraction, creating chunks with embeddings and syncing to Pinecone.

### Batch Processing

Process all existing documents:

```bash
# Process all documents
python3 backend/scripts/process_all_documents.py

# Process specific document type
python3 backend/scripts/process_all_documents.py --document-type balance_sheet

# Process with limits
python3 backend/scripts/process_all_documents.py --limit 10

# Reprocess documents that already have chunks
python3 backend/scripts/process_all_documents.py --no-skip-processed

# Skip embeddings (faster, for testing)
python3 backend/scripts/process_all_documents.py --no-embeddings
```

## Configuration

Configuration is managed in `app/config/chunking_config.py`:

```python
from app.config.chunking_config import chunking_config

# Chunk size (tokens)
chunking_config.CHUNK_SIZE = 1000

# Overlap size (tokens)
chunking_config.CHUNK_OVERLAP = 100

# Table extraction modes
chunking_config.TABLE_EXTRACTION_MODES = ['lattice', 'stream']

# Header detection
chunking_config.HEADER_DETECTION_ENABLED = True
chunking_config.HEADER_POSITION_TOP_THRESHOLD = 0.15  # Top 15% of page

# Parent-child relationships
chunking_config.PARENT_CHILD_ENABLED = True
chunking_config.MAX_DISTANCE_FOR_PARENT = 500  # characters

# Performance targets
chunking_config.TARGET_PROCESSING_TIME_PER_PAGE = 2.0  # seconds
chunking_config.TARGET_TABLE_EXTRACTION_TIME = 1.0  # seconds
chunking_config.TARGET_CHUNKING_TIME_PER_PAGE = 0.5  # seconds
```

## Performance Targets

- **Processing Speed**: < 2 seconds per page
- **Table Extraction**: < 1 second per table
- **Chunking**: < 0.5 seconds per page
- **Embedding Generation**: Async/batch processing
- **Pinecone Sync**: Batch operations

Performance is automatically validated and warnings are logged if targets are exceeded.

## Database Schema

### DocumentChunk Model

```python
class DocumentChunk(Base):
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('document_uploads.id'))
    chunk_index = Column(Integer)  # Order in document
    chunk_text = Column(Text)  # Content
    chunk_size = Column(Integer)  # Character count
    chunk_type = Column(String(20))  # 'text', 'table', 'header'
    parent_chunk_id = Column(Integer, ForeignKey('document_chunks.id'))
    embedding = Column(JSON)  # Vector embedding
    chunk_metadata = Column(JSON)  # Enriched metadata
    property_id = Column(Integer)
    period_id = Column(Integer)
    document_type = Column(String(50))
```

### Indexes

- `idx_chunk_document_index`: (document_id, chunk_index)
- `idx_chunk_property_period`: (property_id, period_id)
- `idx_chunk_type_document`: (document_id, chunk_type)
- `ix_document_chunks_chunk_type`: (chunk_type)
- `ix_document_chunks_parent_chunk_id`: (parent_chunk_id)

## Error Handling

The processor includes comprehensive error handling:

- **Graceful Degradation**: If Camelot fails, falls back to text-only processing
- **Retry Logic**: Automatic retries for transient errors
- **Transaction Rollback**: Database errors trigger rollback
- **Comprehensive Logging**: All operations logged for debugging

## Example Output

```python
{
    "success": True,
    "document_id": 123,
    "statistics": {
        "total_chunks": 45,
        "text_chunks": 30,
        "table_chunks": 10,
        "header_chunks": 5,
        "tables_extracted": 10,
        "pages_processed": 5
    },
    "performance": {
        "total_time": 8.5,
        "time_per_page": 1.7,
        "table_extraction_time": 2.1,
        "text_extraction_time": 1.2,
        "chunking_time": 2.5,
        "header_detection_time": 0.8,
        "save_time": 0.5,
        "embedding_time": 1.4,
        "validation": {
            "within_target": True,
            "warning": None
        }
    }
}
```

## Troubleshooting

### Tables Not Extracted

- Check Camelot installation: `pip install camelot-py[cv]`
- Verify PDF has actual tables (not just text formatted as tables)
- Check Camelot accuracy scores in logs
- Try different extraction modes (lattice vs stream)

### Chunks Too Large/Small

- Adjust `CHUNK_SIZE` in `chunking_config.py`
- Adjust `CHUNK_OVERLAP` for context preservation
- Check token estimation: `TOKENS_PER_CHAR = 0.25` (1 token ≈ 4 chars)

### Parent-Child Relationships Not Working

- Verify `PARENT_CHILD_ENABLED = True`
- Check header detection thresholds
- Ensure headers are detected (check chunk_type == 'header')
- Verify `MAX_DISTANCE_FOR_PARENT` is appropriate

### Performance Issues

- Check performance validation warnings in logs
- Consider disabling embeddings for testing
- Use batch processing for large document sets
- Monitor database query performance

## Best Practices

1. **Process New Documents**: Enhanced processor runs automatically on new uploads
2. **Batch Process Existing**: Use `process_all_documents.py` for existing documents
3. **Monitor Performance**: Check logs for performance warnings
4. **Validate Results**: Review chunk types and relationships in database
5. **Tune Configuration**: Adjust chunk size and overlap based on document types

## Testing

### Unit Tests

```bash
pytest backend/tests/services/test_document_processor_enhanced.py -v
```

### Integration Tests

```bash
pytest backend/tests/integration/test_document_processor_enhanced.py -v
```

### Performance Tests

```bash
pytest backend/tests/integration/test_document_processor_enhanced.py::TestPerformanceBenchmarks -v
```

## Migration

### Running Database Migration

```bash
cd backend
alembic upgrade head
```

This adds `chunk_type` and `parent_chunk_id` columns to `document_chunks` table.

### Processing Existing Documents

After migration, process existing documents:

```bash
python3 backend/scripts/process_all_documents.py
```

## Dependencies

- `camelot-py==1.0.9`: Table extraction
- `langchain==0.1.9`: Text chunking
- `PyMuPDF==1.26.5`: PDF text extraction
- `pdfplumber==0.11.7`: Alternative PDF extraction
- `pandas`: Table to markdown conversion
- `openai`: Embedding generation
- `pinecone-client`: Vector storage

## Future Enhancements

- Support for more document types
- Improved header detection using ML
- Automatic table type classification
- Enhanced multi-page table merging
- Performance optimizations for large documents

