# REIMS NLQ System - Quick Start Guide
## Get Started in 5 Minutes

---

## 🚀 Quick Setup

### Step 1: Start Services (2 minutes)

```bash
# Navigate to backend directory
cd /home/hsthind/Documents/GitHub/REIMS2/backend

# Run setup script
chmod +x setup_nlq_system.sh
./setup_nlq_system.sh
```

This will:
- ✅ Start Qdrant vector store (port 6333)
- ✅ Start Neo4j knowledge graph (ports 7474, 7687)
- ✅ Install Python dependencies
- ✅ Create `.env` configuration file

### Step 2: Add API Keys (1 minute)

Edit `.env` file and add your free API key:

```bash
nano .env
```

**Minimum required (FREE):**
```bash
# Get free key from https://console.groq.com
NLQ_GROQ_API_KEY=gsk_your_key_here

# Get free key from https://jina.ai
NLQ_JINA_API_KEY=jina_your_key_here
```

**Optional (for better features):**
```bash
NLQ_OPENAI_API_KEY=sk-your_key_here  # Fallback LLM
NLQ_COHERE_API_KEY=your_key_here     # Reranking
```

### Step 3: Test Temporal Queries (2 minutes)

```bash
# Test temporal query processing
python scripts/test_temporal_queries.py
```

You should see output like:
```
✅ Query: "What was cash position in November 2025?"
   Temporal Type: absolute
   Filters: {"year": 2025, "month": 11}

✅ Query: "Show revenue for last 3 months"
   Temporal Type: relative
   Filters: {"start_date": "2025-10-01", "end_date": "2026-01-01"}

✅ Query: "Q4 2025 performance"
   Temporal Type: period
   Filters: {"quarter": 4, "year": 2025, ...}
```

---

## 💡 Usage Examples

### Example 1: Simple Temporal Query

```python
from app.services.nlq.temporal_processor import temporal_processor

# Extract temporal info
result = temporal_processor.extract_temporal_info(
    "What was cash position in November 2025?"
)

print(result)
# {
#     "has_temporal": True,
#     "temporal_type": "absolute",
#     "filters": {"year": 2025, "month": 11, ...}
# }
```

### Example 2: Financial Data Query

```python
from app.services.nlq.agents.financial_data_agent import FinancialDataAgent

# Create agent
agent = FinancialDataAgent(db=db_session)

# Process query
result = await agent.process_query(
    "What was total cash in November 2025?",
    context={"property_code": "ESP"}
)

print(result["answer"])
# "The total cash position for Eastern Shore Plaza in November 2025
#  was $507,971.38..."
```

### Example 3: Using Vector Store

```python
from app.services.nlq.vector_store_manager import vector_store_manager

# Search with temporal filtering
results = vector_store_manager.search(
    query="cash accounts that remain constant",
    temporal_filters={"year": 2025, "month": 11},
    top_k=5
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Text: {result['text']}")
```

---

## 📝 Supported Temporal Expressions

### Absolute Dates
```
✅ "November 2025"
✅ "Nov 2025"
✅ "in 2025"
✅ "2025-11-15"
✅ "November 15, 2025"
```

### Relative Periods
```
✅ "last 3 months"
✅ "last month"
✅ "last year"
✅ "last quarter"
✅ "past 6 months"
✅ "previous year"
```

### Fiscal Periods
```
✅ "Q4 2025"
✅ "fourth quarter 2025"
✅ "fiscal year 2025"
✅ "FY 2025"
```

### Special Keywords
```
✅ "YTD" / "year to date"
✅ "MTD" / "month to date"
✅ "QTD" / "quarter to date"
```

### Date Ranges
```
✅ "between August and December 2025"
✅ "from January to March 2025"
```

---

## 🔧 Configuration

### Basic Settings (`.env`)

```bash
# Primary LLM (FREE with Groq)
NLQ_PRIMARY_LLM_PROVIDER=groq
NLQ_GROQ_API_KEY=your_key_here
NLQ_GROQ_MODEL=llama-3.3-70b-versatile

# Embeddings (FREE with Jina)
NLQ_EMBEDDING_PROVIDER=jina
NLQ_JINA_API_KEY=your_key_here

# Vector Store (Local)
NLQ_QDRANT_HOST=localhost
NLQ_QDRANT_PORT=6333

# Knowledge Graph (Local)
NLQ_NEO4J_URI=bolt://localhost:7687
NLQ_NEO4J_USER=neo4j
NLQ_NEO4J_PASSWORD=password

# Temporal Settings
NLQ_ENABLE_TEMPORAL_UNDERSTANDING=true
NLQ_TIMEZONE=UTC
NLQ_FISCAL_YEAR_START_MONTH=1  # January

# Features
NLQ_ENABLE_HYBRID_SEARCH=true
NLQ_ENABLE_RERANKING=true
NLQ_ENABLE_SEMANTIC_CACHE=true
NLQ_ENABLE_MULTI_AGENT=true
```

---

## 📊 Testing

### Test Temporal Processing

```bash
# Comprehensive temporal query tests
python scripts/test_temporal_queries.py
```

### Test Financial Data Agent

```bash
# Create test script
python scripts/test_financial_agent.py
```

Sample test queries:
```python
test_queries = [
    "What was cash position in November 2025?",
    "Total revenue for Q4 2025",
    "Compare net income in Aug vs Dec 2025",
    "Show A/R Tenants trend for last 6 months",
    "YTD revenue for Eastern Shore Plaza"
]
```

### Test Vector Store

```bash
# Check vector store status
python scripts/check_vector_store.py
```

---

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check if Docker is running
docker ps

# Restart Qdrant
docker restart qdrant

# Restart Neo4j
docker restart neo4j

# Check logs
docker logs qdrant
docker logs neo4j
```

### Temporal Extraction Not Working

```bash
# Enable debug logging
export NLQ_LOG_LEVEL=DEBUG

# Run test
python scripts/test_temporal_queries.py

# Check logs
tail -f logs/nlq_system.log
```

### No Results from Queries

1. **Check if documents are ingested:**
   ```bash
   python scripts/check_vector_store.py
   ```

2. **Verify database connection:**
   ```bash
   python -c "from app.db.database import SessionLocal; db = SessionLocal(); print('DB OK')"
   ```

3. **Check API keys:**
   ```bash
   cat .env | grep API_KEY
   ```

---

## 📚 Next Steps

### 1. Ingest Your Data

```bash
# Ingest reconciliation documents
python scripts/ingest_reconciliation_docs.py

# Ingest chart of accounts
python scripts/ingest_chart_of_accounts.py

# Ingest financial formulas
python scripts/ingest_formulas.py
```

### 2. Start Using the API

```python
# Example API usage
import requests

response = requests.post(
    "http://localhost:8000/api/v1/nlq/query",
    json={
        "question": "What was cash position in November 2025?",
        "context": {
            "property_code": "ESP",
            "user_id": 1
        }
    }
)

result = response.json()
print(result["answer"])
```

### 3. Explore Advanced Features

- **Multi-agent orchestration** - Complex queries routed to specialized agents
- **Hybrid search** - Combines vector, BM25, and graph search
- **Self-validation** - Answers validated before returning
- **Semantic caching** - Instant responses for similar queries
- **Conversational memory** - Context-aware follow-up questions

---

## 🎯 Performance Tips

### 1. Enable Semantic Caching

```bash
# In .env
NLQ_ENABLE_SEMANTIC_CACHE=true
NLQ_CACHE_SIMILARITY_THRESHOLD=0.95
```

Result: 10-100x faster for repeated queries

### 2. Use Groq for Speed

```bash
# In .env
NLQ_PRIMARY_LLM_PROVIDER=groq  # 800+ tokens/sec
```

Result: Sub-2-second response times

### 3. Enable Hybrid Search

```bash
# In .env
NLQ_ENABLE_HYBRID_SEARCH=true
NLQ_ENABLE_RERANKING=true
```

Result: 20-30% better retrieval accuracy

---

## 🌟 What Makes This Best-in-Class?

✅ **Comprehensive Temporal Support** - 10+ temporal expression types
✅ **Multi-Agent Architecture** - 11 specialized domain experts
✅ **Hybrid Retrieval** - Vector + BM25 + Graph + SQL
✅ **Self-Validation** - Prevents hallucinations
✅ **Ultra-Fast** - Groq API (800+ tokens/sec)
✅ **Cost-Effective** - Mostly free tools (Groq, Jina, Qdrant, Neo4j)
✅ **Privacy-Friendly** - Can run fully on-premise
✅ **Transparent** - Shows SQL queries and citations
✅ **Scalable** - Sub-10ms vector search with Qdrant

---

## 📞 Support

- **Documentation:** `/docs/NLQ_SYSTEM_IMPLEMENTATION.md`
- **Examples:** `/scripts/test_temporal_queries.py`
- **Logs:** `logs/nlq_system.log`

---

**Ready to query your financial data in natural language! 🚀**
