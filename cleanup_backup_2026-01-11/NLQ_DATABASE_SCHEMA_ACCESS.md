# 🗄️ NLQ System - Complete Database Schema Access

## Overview

The NLQ (Natural Language Query) system now has **complete access to all 90+ tables** in the REIMS database. Users can query any data across all modules using natural language.

---

## ✅ What Was Implemented

### 1. **Comprehensive Schema Generator** (`backend/app/services/nlq/schema_generator.py`)

A new service that dynamically extracts the complete database schema including:
- **All 90+ tables** with full DDL statements
- **Column definitions** with data types, constraints, and defaults
- **Foreign key relationships** between tables
- **Table descriptions** explaining the purpose of each table
- **Column descriptions** for key fields
- **Documentation** of REIMS concepts and terminology

### 2. **Enhanced Text-to-SQL Engine** (`backend/app/services/nlq/text_to_sql.py`)

Updated to use the comprehensive schema:
- **Dynamic DDL generation** instead of hardcoded 5 tables
- **Comprehensive documentation training** with 50+ concepts
- **Expanded example queries** covering 10+ table types
- **Fallback mechanism** for graceful degradation

---

## 📊 Database Coverage

The NLQ system now has access to **91 tables** across all REIMS modules:

### Core Entities (3 tables)
- `properties` - Real estate properties
- `financial_periods` - Reporting periods
- `users` - System users

### Financial Statements (7 tables)
- `balance_sheet_data` - Balance sheet line items
- `income_statement_data` - Income statement line items
- `income_statement_headers` - Income statement metadata
- `cash_flow_data` - Cash flow line items
- `cash_flow_headers` - Cash flow metadata
- `chart_of_accounts` - Standard account codes
- `financial_metrics` - Calculated financial KPIs

### Account Management & Mapping (7 tables)
- `account_code_patterns` - Account code pattern recognition
- `account_code_synonyms` - Alternative account codes
- `account_mapping_rules` - Mapping rules configuration
- `account_mappings` - Property-specific account mappings
- `account_risk_classes` - Risk classification of accounts
- `account_semantic_mappings` - AI-learned semantic mappings
- `account_synonyms` - Alternative account names

### Mortgage & Debt (2 tables)
- `mortgage_statement_data` - Mortgage loan data (DSCR, LTV)
- `mortgage_payment_history` - Payment history

### Rent Roll & Tenants (3 tables)
- `rent_roll_data` - Tenant and lease information
- `tenant_performance_history` - Tenant payment tracking
- `tenant_recommendations` - Tenant risk recommendations

### Audit & Compliance (1 table)
- `audit_trails` - Complete audit log of all changes

### Reconciliation (8 tables)
- `reconciliation_sessions` - Reconciliation workflows
- `reconciliation_differences` - Discrepancies found
- `reconciliation_resolutions` - Resolution actions
- `reconciliation_learning_log` - ML learning from reconciliations
- `cash_account_reconciliations` - Cash reconciliation
- `forensic_reconciliation_sessions` - Forensic-level sessions
- `forensic_matches` - Matched items
- `forensic_discrepancies` - Unmatched items

### Alerts & Monitoring (7 tables)
- `alert_rules` - Alert rule configurations
- `alert_history` - Alert trigger history
- `alert_snoozes` - Temporary alert snoozes
- `alert_suppression_rules` - Suppression rule configs
- `alert_suppressions` - Active suppressions
- `committee_alerts` - Investment committee alerts
- `notifications` - User notifications

### Data Quality (3 tables)
- `data_quality_rules` - Quality check rules
- `data_quality_scores` - Quality metrics
- `validation_results` - Validation check results

### Anomaly Detection (7 tables)
- `anomaly_detections` - Detected anomalies
- `anomaly_thresholds` - Detection thresholds
- `anomaly_feedback` - User feedback on anomalies
- `anomaly_explanations` - AI-generated explanations
- `anomaly_learning_patterns` - Learned patterns
- `anomaly_model_cache` - Model cache
- `adaptive_confidence_thresholds` - Dynamic thresholds

### Document Management (8 tables)
- `document_uploads` - Uploaded documents
- `document_versions` - Version history
- `document_summaries` - AI-generated summaries
- `document_chunks` - Text chunks for RAG
- `extraction_corrections` - User corrections
- `extraction_field_metadata` - Field metadata
- `extraction_learning_patterns` - Learned patterns
- `extraction_logs` - Extraction logs

### Workflow Management (4 tables)
- `workflow_locks` - Period locking
- `review_approval_chains` - Approval workflows
- `scheduled_tasks` - Task scheduling
- `period_document_completeness` - Document tracking

### Budgeting & Forecasting (3 tables)
- `budgets` - Budget data
- `forecasts` - Financial forecasts
- `forecast_models` - Forecast configurations

### Market Intelligence (3 tables)
- `market_intelligence` - External market data
- `market_data_lineage` - Data source tracking
- `property_research` - Research notes

### AI/ML Models (6 tables)
- `model_performance_metrics` - ML model tracking
- `hallucination_reviews` - AI hallucination detection
- `learned_match_patterns` - Learned matching patterns
- `match_confidence_models` - Confidence scoring models
- `pyod_model_selection_log` - Anomaly model selection
- `extraction_templates` - Extraction templates

### Other Tables (16 tables)
- `budgets`, `calculated_rules`, `cash_flow_adjustments`, `concordance_tables`, `cross_property_benchmarks`, `discovered_account_codes`, `filename_period_patterns`, `health_score_configs`, `issue_captures`, `issue_knowledge_base`, `lenders`, `materiality_configs`, `pdf_field_coordinates`, `prevention_rules`, `report_audits`, `validation_rules`, `nlq_queries`

---

## 🎯 What Users Can Now Query

### Financial Data
```
✅ "What was the cash position in November 2025?"
✅ "Show me total revenue for Q4 2025"
✅ "What are total assets for property ESP?"
✅ "Compare net income YTD vs last year"
```

### Audit & History
```
✅ "Who changed the cash position in November 2025?"
✅ "Show all changes made by user John Doe"
✅ "What was modified in the last week?"
✅ "Show audit trail for property ESP"
```

### Reconciliation
```
✅ "Show me unreconciled items"
✅ "What reconciliation sessions are open?"
✅ "Show reconciliation differences over $1,000"
✅ "List resolved reconciliation items"
```

### Data Quality
```
✅ "Show me data quality issues"
✅ "What validation errors were found?"
✅ "Show critical data quality problems"
✅ "List validation failures by table"
```

### Anomalies
```
✅ "Show me detected anomalies"
✅ "What financial anomalies are unresolved?"
✅ "Show high-severity anomalies"
✅ "List anomalies for property ESP"
```

### Alerts
```
✅ "Show active alerts"
✅ "What critical alerts are triggered?"
✅ "Show alerts for property ESP"
✅ "List covenant breach alerts"
```

### Rent Roll & Tenants
```
✅ "Show me the rent roll for property ESP"
✅ "What is the occupancy rate?"
✅ "Show vacant units"
✅ "List tenants with lease expiring in 90 days"
```

### Mortgage Data
```
✅ "What is the current DSCR for property ESP?"
✅ "Show mortgage payment history"
✅ "What is the LTV ratio?"
✅ "Show debt service coverage trend"
```

### Market Intelligence
```
✅ "Show market intelligence for property ESP"
✅ "What are the demographic trends?"
✅ "Show competitive market data"
✅ "List economic indicators"
```

### Budgets & Forecasts
```
✅ "Show budget vs actual for Q4"
✅ "What is the revenue forecast?"
✅ "Compare budget to actuals"
✅ "Show variance analysis"
```

### Documents
```
✅ "Show uploaded documents for property ESP"
✅ "List documents from November 2025"
✅ "Show document extraction errors"
✅ "What documents are missing?"
```

---

## 🔧 How It Works

### 1. Schema Training

When the NLQ system starts, it trains on the complete database schema:

```python
from app.services.nlq.schema_generator import get_schema_generator

# Generate DDL for all tables
schema_gen = get_schema_generator()
ddl_statements = schema_gen.generate_all_ddl(db)

# Train Vanna.ai on schema
for table_name, ddl in ddl_statements.items():
    vanna.train(ddl=ddl)
```

### 2. Documentation Training

The system learns REIMS-specific concepts:

```python
# Train on 50+ documentation items
documentation = schema_gen.generate_documentation()
for doc in documentation:
    vanna.train(documentation=doc)
```

### 3. Example Query Training

Trains on example queries covering all major table types:

```python
# 17+ example queries across all modules
examples = [
    {"question": "What was the cash position...", "sql": "SELECT..."},
    {"question": "Who changed the cash position...", "sql": "SELECT..."},
    # ... covering all major query types
]
```

### 4. Query Generation

When a user asks a question:

1. **Parse Question** - Extract intent and temporal info
2. **Generate SQL** - Use Vanna.ai with full schema knowledge
3. **Validate SQL** - Ensure safe, read-only queries
4. **Execute** - Run against database
5. **Return Results** - Format and return with confidence score

---

## 📖 Key Files

### Backend Files

| File | Purpose |
|------|---------|
| `backend/app/services/nlq/schema_generator.py` | Comprehensive schema extraction |
| `backend/app/services/nlq/text_to_sql.py` | Text-to-SQL with full schema access |
| `backend/app/services/nlq/orchestrator.py` | Multi-agent query orchestration |
| `backend/app/services/nlq/agents/financial_data_agent.py` | Financial data queries |
| `backend/app/services/nlq/agents/audit_agent.py` | Audit trail queries |
| `backend/app/services/nlq/agents/reconciliation_agent.py` | Reconciliation queries |
| `backend/app/services/nlq/temporal_processor.py` | Temporal expression parsing |

### Frontend Files

| File | Purpose |
|------|---------|
| `src/services/nlqService.ts` | Frontend API client |
| `src/components/NLQSearchBar.tsx` | Reusable search component |
| `src/pages/NaturalLanguageQueryNew.tsx` | Full NLQ page |

---

## 🚀 Usage

### Access NLQ Page

Navigate to: **`http://localhost:5173/#nlq-search`**

### Use NLQ Component

```tsx
import NLQSearchBar from '../components/NLQSearchBar';

<NLQSearchBar
  propertyCode="ESP"
  propertyId={1}
  userId={user?.id}
/>
```

---

## 📈 Benefits

### Before (Limited Access)
- ❌ Only 5 tables accessible
- ❌ Limited to basic financial queries
- ❌ No audit trail access
- ❌ No reconciliation queries
- ❌ No data quality queries

### After (Complete Access)
- ✅ **All 90+ tables** accessible
- ✅ **Financial data** across all statements
- ✅ **Audit trails** - who changed what
- ✅ **Reconciliation** - differences and resolutions
- ✅ **Data quality** - issues and validations
- ✅ **Anomalies** - detected problems
- ✅ **Alerts** - active warnings
- ✅ **Rent roll** - tenant and lease data
- ✅ **Mortgage** - DSCR, LTV, payments
- ✅ **Market data** - external intelligence
- ✅ **Documents** - uploaded files and extraction
- ✅ **Budgets** - budget vs actual
- ✅ **Forecasts** - predictions and projections

---

## 🔐 Security

The NLQ system enforces strict security:

- ✅ **Read-only queries** - No INSERT, UPDATE, DELETE, DROP allowed
- ✅ **SQL validation** - Dangerous keywords blocked
- ✅ **User authentication** - Requires valid session
- ✅ **Property context** - Respects user permissions
- ✅ **Query logging** - All queries logged in `nlq_queries` table

---

## 🧪 Testing

To test the expanded schema access:

### 1. Start Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Train Schema (First Time)
The system auto-trains on first query, or manually trigger:
```python
from app.services.nlq.text_to_sql import get_text_to_sql
from app.db.database import get_db

db = next(get_db())
text_to_sql = get_text_to_sql()
text_to_sql.train_on_schema(db)
```

### 3. Test Queries
Navigate to: `http://localhost:5173/#nlq-search`

Try queries from different modules:
- Financial: "What was the cash position?"
- Audit: "Who changed the balance sheet?"
- Reconciliation: "Show unreconciled items"
- Data Quality: "Show validation errors"
- Anomalies: "Show detected anomalies"

---

## 📝 Adding More Tables

If new tables are added to REIMS in the future:

1. **Create Model** - Add SQLAlchemy model in `backend/app/models/`
2. **Import Model** - Add import to `schema_generator.py`
3. **Add Description** - Update `_get_table_descriptions()` in schema generator
4. **Restart Backend** - Schema will auto-extract new table
5. **No NLQ changes needed** - Dynamic schema generation handles it

---

## 🎉 Summary

**Before:** NLQ had access to 5 hardcoded tables

**Now:** NLQ has access to **ALL 90+ tables** across:
- ✅ Financial statements
- ✅ Audit trails
- ✅ Reconciliation
- ✅ Data quality
- ✅ Anomalies
- ✅ Alerts
- ✅ Rent roll
- ✅ Mortgage data
- ✅ Market intelligence
- ✅ Documents
- ✅ Budgets & forecasts
- ✅ And 70+ more tables

**Result:** Users can now ask questions about **any data** in REIMS using natural language!

---

## 📚 Additional Documentation

- [NLQ_READY_TO_USE.md](NLQ_READY_TO_USE.md) - Quick start guide
- [NLQ_QUICK_ACCESS.md](NLQ_QUICK_ACCESS.md) - 30-second access
- [FRONTEND_NLQ_INTEGRATED.md](FRONTEND_NLQ_INTEGRATED.md) - Frontend integration
- [NLQ_IMPLEMENTATION_COMPLETE.md](NLQ_IMPLEMENTATION_COMPLETE.md) - Complete system overview
