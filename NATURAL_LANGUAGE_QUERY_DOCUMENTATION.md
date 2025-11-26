# Natural Language Query (NLQ) Feature Documentation

## Overview

The Natural Language Query (NLQ) feature enables users to query financial data using plain English questions. The system uses a combination of Large Language Models (LLMs), RAG (Retrieval-Augmented Generation), and rule-based fallbacks to understand user intent, retrieve relevant data, and generate natural language answers.

**Key Capabilities:**
- Query financial metrics (NOI, revenue, expenses, DSCR, etc.)
- Compare properties and analyze trends
- Retrieve document content from uploaded PDFs
- Generate actionable insights with citations
- Support property-specific context filtering

---

## Architecture

### High-Level Flow

```
User Question
    ↓
Intent Detection (LLM or Rule-based)
    ↓
Data Retrieval (Structured + Document Content)
    ↓
Answer Generation (LLM with Context)
    ↓
Response with Citations & Confidence
```

### Components

1. **API Layer** (`backend/app/api/v1/nlq.py`)
2. **Service Layer** (`backend/app/services/nlq_service.py`)
3. **RAG Services** (`backend/app/services/rag_retrieval_service.py`, `backend/app/services/embedding_service.py`)
4. **Database Models** (`backend/app/models/nlq_query.py`)
5. **Frontend** (`src/pages/NaturalLanguageQuery.tsx`)

---

## Backend Implementation

### 1. API Endpoints

**File:** `backend/app/api/v1/nlq.py`

#### POST `/api/v1/nlq/query`

Processes a natural language query and returns an answer with data, citations, and metadata.

**Request:**
```json
{
  "question": "What was the NOI for Eastern Shore Plaza in Q3 2024?",
  "context": {
    "property_id": 1,
    "property_code": "ESP001",
    "property_name": "Eastern Shore Plaza"
  }
}
```

**Response:**
```json
{
  "success": true,
  "question": "What was the NOI for Eastern Shore Plaza in Q3 2024?",
  "answer": "The NOI for Eastern Shore Plaza in Q3 2024 was $1,234,567.89...",
  "data": [...],
  "document_chunks": [...],
  "citations": [...],
  "confidence": 0.95,
  "sql_query": "SELECT ...",
  "suggested_follow_ups": [...],
  "execution_time_ms": 234,
  "query_id": 123
}
```

**Features:**
- Supports property context filtering
- Returns structured data and document chunks
- Includes SQL query for transparency
- Provides suggested follow-up questions

#### GET `/api/v1/nlq/suggestions`

Returns example questions users can ask.

**Response:**
```json
{
  "suggestions": [
    "What was the NOI for each property last quarter?",
    "Show me occupancy trends over the last year",
    ...
  ],
  "total": 10
}
```

#### GET `/api/v1/nlq/history`

Retrieves user's query history.

**Query Parameters:**
- `limit` (default: 20): Number of queries to return

**Response:**
```json
{
  "history": [
    {
      "id": 123,
      "question": "...",
      "answer": "...",
      "confidence_score": 0.95,
      "created_at": "2025-11-25T10:00:00Z"
    }
  ],
  "total": 5
}
```

#### GET `/api/v1/nlq/insights/portfolio`

Generates AI-powered portfolio insights.

**Response:**
```json
{
  "insights": [
    {
      "id": "dscr_stress",
      "type": "risk",
      "title": "DSCR Stress Pattern Detected",
      "description": "2 properties showing DSCR stress - refinancing window optimal",
      "confidence": 0.85
    }
  ],
  "total": 3,
  "generated_at": "2025-11-25T10:00:00Z"
}
```

---

### 2. Service Layer

**File:** `backend/app/services/nlq_service.py`

#### NaturalLanguageQueryService

Main service class that orchestrates query processing.

**Key Methods:**

##### `query(question: str, user_id: int, context: Optional[Dict] = None) -> Dict`

Main entry point for processing queries.

**Process:**
1. Check cache (24-hour window)
2. Use LLM if available, otherwise fallback to rule-based
3. Detect intent and extract entities
4. Retrieve structured data and/or document content
5. Generate answer using LLM or templates
6. Extract citations and calculate confidence
7. Store query in database
8. Return result

**Intent Types:**
- `metric_query`: Single metric value queries
- `comparison`: Compare properties/metrics
- `trend_analysis`: Historical trends
- `aggregation`: Sum/average across properties
- `ranking`: Top/bottom properties
- `loss_query`: Properties with losses
- `profit_query`: Profitable properties
- `dscr_query`: DSCR-related queries
- `document_query`: PDF content queries
- `hybrid_query`: Both structured and document data

##### `_query_with_llm(question: str, user_id: int, start_time: datetime, ...) -> Dict`

Uses LLM to understand query and generate answer.

**Steps:**
1. **Query Understanding**: LLM analyzes question and determines:
   - Query type
   - Whether structured data is needed
   - Whether document content is needed
   - Key entities (properties, metrics, filters)

2. **Data Retrieval**:
   - Structured data: Queries database based on understanding
   - Document content: Uses RAG to retrieve relevant PDF chunks

3. **Answer Generation**: LLM generates answer with full context

##### `_query_loss_profit(entities: Dict, question: str) -> tuple`

Queries properties with losses or profits.

**SQL Query:**
```sql
SELECT 
    p.property_name,
    p.property_code,
    fm.net_income,
    fm.net_operating_income as noi,
    fm.total_revenue,
    fm.total_expenses,
    fp.period_year,
    fp.period_month,
    CONCAT(fp.period_year, '-', LPAD(fp.period_month::text, 2, '0')) as period
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE fm.net_income IS NOT NULL
  AND fm.net_income < 0  -- For losses
  AND fp.id IN (
      SELECT MAX(fp2.id)
      FROM financial_periods fp2
      JOIN financial_metrics fm2 ON fp2.id = fm2.period_id
      WHERE fp2.property_id = p.id
        AND fm2.net_income IS NOT NULL
  )
ORDER BY fm.net_income ASC
```

##### `_query_dscr(entities: Dict, question: str) -> tuple`

Queries DSCR (Debt Service Coverage Ratio) data.

**Features:**
- Extracts threshold from question (e.g., "below 1.25")
- Calculates DSCR using `DSCRMonitoringService`
- Filters by threshold if specified
- Returns NOI, debt service, and gap analysis

##### `_query_rent_roll_metrics(entities: Dict, question: str) -> tuple`

Queries rent roll metrics (occupied area, vacant area, etc.).

**Returns:**
- Total area, occupied area, vacant area
- Occupied/vacant unit counts
- Occupancy rate

##### `_query_document_content(entities: Dict, question: str, property_id: Optional[int] = None) -> List[Dict]`

Retrieves relevant document chunks using RAG.

**Process:**
1. Extracts property/period/document type from entities
2. Uses `RAGRetrievalService` to find relevant chunks
3. Returns top 5 chunks with similarity scores

##### `_generate_llm_answer_with_context(...) -> str`

Generates answer using LLM with full context from structured data and documents.

**Prompt Structure:**
- User question
- Property context (if provided)
- Query understanding
- Structured financial data (JSON)
- Relevant document excerpts
- Instructions for formatting

##### `_generate_dscr_answer(question: str, data: List[Dict]) -> str`

Specialized answer generator for DSCR queries.

**Format:**
- Status icons (🔴/🟡/🟢)
- DSCR value with percentage below threshold
- NOI and debt service formatted
- Gap analysis if below threshold
- Recommendations

##### `_generate_loss_profit_answer(question: str, data: List[Dict], intent: Dict) -> str`

Specialized answer generator for loss/profit queries.

**Format:**
- Property list with status icons
- Net income, NOI, revenue, expenses
- Period information
- Total loss/profit summary
- Recommendations

##### `_generate_rent_roll_area_answer(question: str, data: List[Dict], intent: Dict) -> str`

Specialized answer generator for rent roll area queries.

**Format:**
- Property name and period
- Occupied/vacant/total area
- Occupancy rate
- Unit counts

##### `_generate_trend_answer(question: str, data: List[Dict], intent: Dict) -> str`

Generates answer for trend queries.

**Format:**
- Property-wise trends
- Latest value
- Change over time (absolute and percentage)
- Period range

---

### 3. RAG Integration

**Files:**
- `backend/app/services/rag_retrieval_service.py`
- `backend/app/services/embedding_service.py`

The NLQ service integrates with RAG to retrieve relevant document content from uploaded PDFs.

**Process:**
1. User asks question about document content
2. `_query_document_content` extracts entities
3. `RAGRetrievalService.retrieve_relevant_chunks()`:
   - Generates embedding for question
   - Searches document chunks using vector similarity
   - Filters by property/period/document type
   - Returns top K chunks with similarity scores
4. Chunks are included in answer generation context

**Example:**
```
Question: "What does the rent roll say about occupied area for Hammond Aire?"
→ Retrieves relevant chunks from rent roll PDFs
→ LLM generates answer based on chunk content
```

---

### 4. Database Models

**File:** `backend/app/models/nlq_query.py`

#### NLQQuery Model

Stores all NLQ queries with answers, data, and metadata.

**Table:** `nlq_queries`

**Columns:**
- `id` (Integer, Primary Key)
- `user_id` (Integer, Foreign Key → `users.id`)
- `question` (Text): User's natural language question
- `intent` (JSONB): Detected intent and entities
- `answer` (Text): Generated answer
- `data_retrieved` (JSONB): Data retrieved from database
- `citations` (JSONB): Citations/sources for answer
- `confidence_score` (Numeric(5,4)): Confidence in answer (0-1)
- `sql_query` (Text): SQL query executed (for transparency)
- `execution_time_ms` (Integer): Query execution time
- `created_at` (DateTime): Timestamp

**Indexes:**
- `idx_nlq_user`: On `user_id`
- `idx_nlq_date`: On `created_at`

**Methods:**
- `to_dict()`: Convert to dictionary
- `was_successful`: Check if query was successful (confidence > 0.7)

---

## Frontend Implementation

**File:** `src/pages/NaturalLanguageQuery.tsx`

### Component Structure

```typescript
interface QueryResult {
  id: number
  query_text: string
  natural_language_result: string
  sql_query: string
  result_data: any
  confidence_score: number
  execution_time_ms: number
  created_at: string
  status: string
}
```

### Features

1. **Query Input**
   - Textarea for entering questions
   - Keyboard shortcut: Cmd+Enter / Ctrl+Enter
   - Example queries as clickable chips

2. **Query Execution**
   - POST to `/api/v1/nlq/query`
   - Loading state with spinner
   - Error handling and display

3. **Results Display**
   - Natural language answer
   - Structured data (table or grid format)
   - SQL query (expandable)
   - Confidence score and execution time
   - Query metadata (timestamp, status)

4. **Example Queries**
   - Pre-defined example questions
   - Click to populate input

5. **Recent Queries**
   - Fetches recent queries on mount
   - Displays query history

### API Integration

**Base URL:** `import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'`

**Endpoints Used:**
- `POST /nlq/query`: Execute query
- `GET /nlq/queries/recent?limit=10`: Fetch recent queries

---

## Database Tables Used

The NLQ feature queries the following database tables:

### 1. Core Financial Tables

#### `properties`
- **Purpose**: Property information
- **Columns Used**: `id`, `property_name`, `property_code`, `status`
- **Usage**: Filter queries by property, display property names

#### `financial_periods`
- **Purpose**: Financial reporting periods
- **Columns Used**: `id`, `property_id`, `period_year`, `period_month`, `period_end_date`
- **Usage**: Filter by time period, join with metrics

#### `financial_metrics`
- **Purpose**: Aggregated financial metrics
- **Columns Used**: 
  - `property_id`, `period_id`
  - `net_operating_income` (NOI)
  - `net_income`
  - `total_revenue`
  - `total_expenses`
  - `total_assets` (portfolio value)
  - `total_liabilities`
  - `total_equity`
  - `dscr` (Debt Service Coverage Ratio)
  - `occupancy_rate`
- **Usage**: Primary source for metric queries, aggregations, trends

#### `income_statement_data`
- **Purpose**: Detailed income statement line items
- **Columns Used**: 
  - `property_id`, `period_id`, `upload_id`
  - `account_code`, `account_name`
  - `period_amount`
- **Usage**: Revenue/expense queries, account-level analysis

#### `balance_sheet_data`
- **Purpose**: Balance sheet line items
- **Columns Used**: 
  - `property_id`, `period_id`, `upload_id`
  - `account_code`, `account_name`
  - `amount`
- **Usage**: Asset/liability queries

#### `cash_flow_data`
- **Purpose**: Cash flow statement line items
- **Columns Used**: 
  - `property_id`, `period_id`, `upload_id`
  - `account_code`, `account_name`
  - `period_amount`
- **Usage**: Cash flow queries

#### `rent_roll_data`
- **Purpose**: Tenant and lease information
- **Columns Used**: 
  - `property_id`, `period_id`
  - `unit_area_sqft`
  - `occupancy_status` ('occupied', 'vacant')
  - `monthly_rent`, `annual_rent`
  - `tenant_name`, `lease_start_date`, `lease_end_date`
- **Usage**: Occupancy queries, area calculations, lease expiration analysis

### 2. Supporting Tables

#### `chart_of_accounts`
- **Purpose**: Account code mappings
- **Columns Used**: `account_code`, `account_name`, `document_types`
- **Usage**: Account name lookups, document type filtering

#### `document_uploads`
- **Purpose**: Uploaded document metadata
- **Columns Used**: `id`, `property_id`, `period_id`, `document_type`, `file_name`
- **Usage**: Document content queries, citations

#### `document_chunks`
- **Purpose**: Chunked PDF content for RAG
- **Columns Used**: `id`, `document_id`, `chunk_text`, `embedding`
- **Usage**: RAG-based document content retrieval

#### `nlq_queries`
- **Purpose**: Query log and cache
- **Columns Used**: All columns
- **Usage**: Query history, caching, analytics

#### `users`
- **Purpose**: User information
- **Columns Used**: `id`
- **Usage**: User authentication, query ownership

### 3. Query Patterns

#### Metric Queries
```sql
SELECT 
    p.property_name,
    fp.period_year,
    fp.period_month,
    fm.net_operating_income
FROM financial_metrics fm
JOIN properties p ON fm.property_id = p.id
JOIN financial_periods fp ON fm.period_id = fp.id
WHERE p.property_name = 'Eastern Shore Plaza'
  AND fp.period_year = 2024
  AND fp.period_month IN (7, 8, 9)  -- Q3
```

#### Loss/Profit Queries
```sql
SELECT 
    p.property_name,
    p.property_code,
    fm.net_income,
    fm.net_operating_income as noi,
    fm.total_revenue,
    fm.total_expenses,
    fp.period_year,
    fp.period_month
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE fm.net_income IS NOT NULL
  AND fm.net_income < 0  -- For losses
  AND fp.id IN (
      SELECT MAX(fp2.id)
      FROM financial_periods fp2
      JOIN financial_metrics fm2 ON fp2.id = fm2.period_id
      WHERE fp2.property_id = p.id
        AND fm2.net_income IS NOT NULL
  )
ORDER BY fm.net_income ASC
```

#### DSCR Queries
```sql
SELECT 
    p.property_name,
    p.property_code,
    fm.dscr,
    fm.net_operating_income as noi,
    fp.period_year,
    fp.period_month
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE fm.dscr IS NOT NULL
  AND fm.dscr < 1.25  -- Threshold
ORDER BY fm.dscr ASC
```

#### Rent Roll Area Queries
```sql
SELECT 
    p.property_name,
    p.property_code,
    fp.period_year,
    fp.period_month,
    SUM(CASE WHEN rr.occupancy_status = 'occupied' THEN rr.unit_area_sqft ELSE 0 END) as occupied_area,
    SUM(CASE WHEN rr.occupancy_status = 'vacant' THEN rr.unit_area_sqft ELSE 0 END) as vacant_area,
    SUM(rr.unit_area_sqft) as total_area,
    COUNT(CASE WHEN rr.occupancy_status = 'occupied' THEN 1 END) as occupied_units,
    COUNT(CASE WHEN rr.occupancy_status = 'vacant' THEN 1 END) as vacant_units
FROM rent_roll_data rr
JOIN properties p ON rr.property_id = p.id
JOIN financial_periods fp ON rr.period_id = fp.id
WHERE p.property_code = 'HMND001'
  AND fp.period_year = 2024
  AND fp.period_month = 12
GROUP BY p.property_name, p.property_code, fp.period_year, fp.period_month
```

#### Portfolio Value Queries
```sql
WITH latest_periods AS (
    SELECT p.id as property_id, MAX(fp.id) as period_id
    FROM properties p
    JOIN financial_periods fp ON p.id = fp.property_id
    JOIN financial_metrics fm ON fp.id = fm.period_id
    WHERE fm.total_assets IS NOT NULL
    GROUP BY p.id
)
SELECT
    COUNT(DISTINCT p.id) as property_count,
    SUM(fm.total_assets) as total_portfolio_value,
    AVG(fm.total_assets) as avg_property_value,
    SUM(fm.total_equity) as total_equity,
    SUM(fm.total_liabilities) as total_liabilities,
    SUM(fm.net_operating_income) as total_noi,
    MAX(fp.period_end_date) as latest_period_date
FROM properties p
JOIN latest_periods lp ON p.id = lp.property_id
JOIN financial_periods fp ON lp.period_id = fp.id
JOIN financial_metrics fm ON fp.id = fm.period_id
WHERE fm.total_assets IS NOT NULL
```

#### Trend Queries
```sql
SELECT 
    p.property_name,
    p.property_code,
    fp.period_year as year,
    fp.period_month as month,
    CONCAT(fp.period_year, '-', LPAD(fp.period_month::text, 2, '0')) as period_name,
    fm.net_operating_income as value
FROM financial_metrics fm
JOIN properties p ON fm.property_id = p.id
JOIN financial_periods fp ON fm.period_id = fp.id
WHERE fm.net_operating_income IS NOT NULL
  AND fp.period_end_date >= CURRENT_DATE - INTERVAL '12 months'
ORDER BY p.property_name, fp.period_year DESC, fp.period_month DESC
LIMIT 24
```

---

## LLM Integration

### Supported Providers

1. **OpenAI** (Primary)
   - Model: `gpt-4-turbo-preview`
   - Used for: Query understanding, answer generation

2. **Anthropic Claude** (Fallback)
   - Model: `claude-3-5-sonnet-20241022`
   - Used when OpenAI is unavailable

3. **Rule-Based Fallback**
   - Used when no LLM is available
   - Template-based answer generation

### Configuration

**Environment Variables:**
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key

**Settings:**
- `OPENAI_MODEL`: Model name (default: `gpt-4-turbo-preview`)
- `ANTHROPIC_MODEL`: Model name (default: `claude-3-5-sonnet-20241022`)

### LLM Usage

1. **Query Understanding**
   - Analyzes user question
   - Determines query type and data needs
   - Extracts entities (properties, metrics, filters)

2. **Answer Generation**
   - Combines structured data and document chunks
   - Generates natural language answer
   - Formats currency, percentages, dates
   - Includes citations and recommendations

---

## Caching

### Cache Strategy

- **Duration**: 24 hours
- **Key**: Question text (or `property_id:question` for property-specific queries)
- **Storage**: Database (`nlq_queries` table)
- **Lookup**: Exact question match within 24-hour window

### Cache Benefits

- Faster response for repeated questions
- Reduced LLM API costs
- Consistent answers for same questions

---

## Error Handling

### Error Types

1. **No Data Found**
   - Returns: `{"success": false, "error": "No data found for query"}`
   - Handled gracefully with user-friendly message

2. **LLM Failure**
   - Falls back to rule-based system
   - Logs error for debugging

3. **Database Errors**
   - Transaction rollback
   - Error logged, user notified

4. **Invalid Query**
   - Returns error with suggestion to rephrase
   - Provides example queries

---

## Performance

### Execution Time

- **Typical**: 200-500ms
- **With LLM**: 500-2000ms
- **With RAG**: 1000-3000ms
- **Cached**: <50ms

### Optimization

1. **Caching**: 24-hour cache for repeated queries
2. **Query Limits**: Limits data rows to 50 for serialization
3. **Chunk Limits**: Limits document chunks to top 5
4. **Parallel Processing**: Structured data and document retrieval can be parallelized

---

## Security

### Authentication

- All endpoints require authentication via `get_current_user` dependency
- User ID is tracked for query history

### Authorization

- Users can only see their own query history
- Property context filtering respects user permissions (if implemented)

### Data Privacy

- SQL queries are logged for transparency
- Sensitive data is not exposed in error messages
- Citations include source information

---

## Testing

### Example Queries

1. **Metric Queries**
   - "What was the NOI for Eastern Shore Plaza in Q3 2024?"
   - "Show me the total revenue for all properties in 2024"

2. **Comparison Queries**
   - "Compare revenue for all properties in 2024"
   - "Which property has the highest operating expense ratio?"

3. **Trend Queries**
   - "Show me occupancy trends over the last 2 years"
   - "What are the NOI trends for Hammond Aire?"

4. **Loss/Profit Queries**
   - "Which property is making losses for me?"
   - "Show me properties with losses"
   - "Which properties are profitable?"

5. **DSCR Queries**
   - "Show me properties with DSCR below 1.25"
   - "Which properties have DSCR stress?"

6. **Rent Roll Queries**
   - "What is the occupied area for Hammond Aire in December 2024?"
   - "Show me the vacant area for Wendover Commons"

7. **Portfolio Queries**
   - "What is the total portfolio value?"
   - "Show me the average property value"

8. **Document Queries**
   - "What does the rent roll say about occupied area?"
   - "What is mentioned in the balance sheet about total assets?"

---

## Future Enhancements

### Planned Features

1. **Multi-turn Conversations**
   - Context preservation across queries
   - Follow-up question handling

2. **Advanced RAG**
   - Better chunking strategies
   - Multi-modal retrieval (tables, images)

3. **Query Suggestions**
   - AI-generated suggestions based on data
   - Personalized recommendations

4. **Export Capabilities**
   - Export query results to CSV/Excel
   - Generate reports from queries

5. **Visualizations**
   - Auto-generate charts for trend queries
   - Interactive data exploration

---

## Troubleshooting

### Common Issues

1. **No LLM Available**
   - Check API keys in environment variables
   - Verify LLM client initialization in logs
   - System falls back to rule-based queries

2. **Empty Results**
   - Verify data exists in database
   - Check property/period filters
   - Review SQL query in response

3. **Low Confidence**
   - May indicate ambiguous query
   - Try rephrasing with specific property/metric names
   - Check if data exists for requested period

4. **Slow Performance**
   - Check if query is using RAG (document content)
   - Review execution time in response
   - Consider caching frequently asked questions

---

## Conclusion

The Natural Language Query feature provides a powerful, user-friendly interface for querying financial data. It combines LLM intelligence with structured database queries and RAG-based document retrieval to deliver accurate, contextual answers with citations and confidence scores.

**Key Strengths:**
- Natural language interface
- Multiple query types supported
- Property context filtering
- Document content integration
- Transparent SQL queries
- Comprehensive error handling

**Technical Highlights:**
- LLM-powered query understanding
- RAG integration for document queries
- Efficient caching strategy
- Robust fallback mechanisms
- Comprehensive database integration

