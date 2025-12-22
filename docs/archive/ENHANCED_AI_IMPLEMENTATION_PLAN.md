# Enhanced AI Assistant Implementation Plan

## Goal
Make the AI Assistant answer **ANY question** related to your financial files accurately by combining:
1. **Structured Data Queries** (current database queries)
2. **Document Content Search** (RAG - Retrieval Augmented Generation)
3. **LLM-Powered Understanding** (intent detection and answer generation)

## Current State
- ✅ Basic intent detection (rule-based)
- ✅ Specific query handlers (DSCR, trends, portfolio value)
- ✅ LLM integration (OpenAI/Claude) for answer generation
- ✅ Database queries for structured financial data
- ⚠️ Limited to predefined query patterns
- ❌ Cannot answer questions about document content/text

## Proposed Enhancements

### Phase 1: Enhanced Intent Detection with LLM
**Goal**: Better understand user intent using LLM instead of just rules

**Implementation**:
- Use LLM to classify queries into:
  - Structured data queries (metrics, calculations)
  - Document content queries (text-based questions)
  - Hybrid queries (need both)
- Extract entities (properties, metrics, dates) more accurately
- Understand complex questions with multiple parts

### Phase 2: Document Content Retrieval (RAG)
**Goal**: Answer questions about actual file content

**Implementation**:
1. **Store Extracted Text**: Already available in `extraction_log.extracted_text`
2. **Chunk Documents**: Split large documents into manageable chunks (500-1000 tokens)
3. **Create Embeddings**: Generate vector embeddings for each chunk (using OpenAI/Claude)
4. **Semantic Search**: When user asks a question:
   - Generate embedding for the question
   - Find most relevant document chunks
   - Retrieve context from those chunks
5. **Generate Answer**: Use LLM with retrieved context to answer

### Phase 3: Hybrid Query System
**Goal**: Combine structured data + document content

**Implementation**:
- Detect if query needs:
  - Only structured data → Use current SQL queries
  - Only document content → Use RAG retrieval
  - Both → Combine results intelligently

### Phase 4: SQL Query Generation with LLM
**Goal**: Generate SQL queries from natural language automatically

**Implementation**:
- Use LLM to convert natural language to SQL
- Validate SQL before execution
- Handle complex queries (joins, aggregations, filters)

## Technical Architecture

```
User Question
    ↓
[LLM Intent Detection]
    ↓
    ├─→ Structured Data Query → SQL Generation → Database → Results
    ├─→ Document Content Query → RAG Retrieval → Document Chunks → LLM Answer
    └─→ Hybrid Query → Both Above → Combine Results → LLM Answer
```

## Database Schema Additions Needed

1. **Document Chunks Table**:
```sql
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES document_uploads(id),
    chunk_index INTEGER,
    chunk_text TEXT,
    embedding VECTOR(1536), -- OpenAI embedding dimension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

2. **Query Cache Enhancement**:
- Store LLM-generated SQL queries
- Cache RAG retrieval results

## Implementation Steps

### Step 1: Enhanced Intent Detection (Quick Win)
- Modify `_detect_intent()` to use LLM when available
- Fallback to rule-based if LLM unavailable

### Step 2: Document Chunking Service
- Create service to chunk documents from `extraction_log.extracted_text`
- Store chunks in database

### Step 3: Embedding Generation
- Generate embeddings for chunks using OpenAI/Claude
- Store in `document_chunks` table

### Step 4: RAG Retrieval
- Implement semantic search using vector similarity
- Retrieve top-k relevant chunks

### Step 5: Answer Generation Enhancement
- Use retrieved chunks as context for LLM
- Combine with structured data results

### Step 6: SQL Query Generation
- Use LLM to generate SQL from natural language
- Validate and execute safely

## Benefits

1. **Accurate Answers**: Answers based on actual file content
2. **Flexible Queries**: No need to predefine query patterns
3. **Context-Aware**: Understands relationships between data
4. **Scalable**: Works with any number of documents
5. **Citable**: Can show which documents/chunks were used

## Example Queries After Enhancement

**Current (Limited)**:
- ✅ "What is the total portfolio value?"
- ✅ "Show me NOI trends"
- ❌ "What did the income statement say about operating expenses?"

**After Enhancement**:
- ✅ "What is the total portfolio value?" (structured data)
- ✅ "Show me NOI trends" (structured data)
- ✅ "What did the income statement say about operating expenses?" (document content)
- ✅ "Compare the operating expenses mentioned in the Q3 2024 income statement with the calculated metrics" (hybrid)
- ✅ "What were the main concerns mentioned in the financial notes?" (document content)
- ✅ "Find all mentions of 'debt restructuring' across all documents" (document content)

## Dependencies

- **Vector Database**: PostgreSQL with pgvector extension (or separate vector DB)
- **Embedding Model**: OpenAI `text-embedding-3-small` or similar
- **LLM**: OpenAI GPT-4 or Claude 3 (already integrated)

## Cost Considerations

- **Embedding Generation**: One-time cost per document chunk (~$0.0001 per 1K tokens)
- **Query Embedding**: Per query (~$0.0001 per query)
- **LLM Usage**: Per answer generation (~$0.01-0.10 per query depending on model)

## Timeline

- **Phase 1** (Enhanced Intent): 1-2 days
- **Phase 2** (RAG Setup): 3-5 days
- **Phase 3** (Hybrid System): 2-3 days
- **Phase 4** (SQL Generation): 2-3 days

**Total**: ~2 weeks for full implementation

