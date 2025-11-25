# Concordance Table Implementation

## Overview

The Concordance Table system automatically generates field-by-field comparison tables for every document upload, showing extraction results from all models side-by-side with agreement percentages. This enables quality assurance, model performance analysis, and client reporting.

## Features

✅ **Automatic Generation**: Concordance tables are generated automatically on every document upload  
✅ **Field-by-Field Comparison**: Shows values from all 6 extraction models side-by-side  
✅ **Agreement Metrics**: Calculates agreement percentage per field (0-100%)  
✅ **Consensus Detection**: Identifies fields with perfect (100%), partial (≥75%), or no agreement  
✅ **Conflict Identification**: Lists which models disagree on each field  
✅ **Export Functionality**: CSV and Excel export for reporting  
✅ **Database Storage**: Persistent storage for historical comparison  
✅ **API Endpoints**: RESTful API for retrieving concordance tables  

## Architecture

### Database Model

**File**: `backend/app/models/concordance_table.py`

Stores field-by-field comparison data:
- Field identification (name, display name, account code)
- Model values (JSON with values from each model)
- Agreement metrics (count, percentage, consensus flags)
- Final value and model (from ensemble voting)

### Service Layer

**File**: `backend/app/services/concordance_service.py`

`ConcordanceService` class provides:
- `generate_concordance_table()`: Runs all models and generates comparison table
- `get_concordance_table()`: Retrieves stored concordance table
- `export_concordance_table_csv()`: Exports as CSV
- `_extract_field_values_from_db()`: Extracts field values from database records
- `_calculate_agreement()`: Calculates agreement metrics per field

### API Endpoints

**File**: `backend/app/api/v1/concordance.py`

- `GET /api/v1/concordance/{upload_id}`: Get concordance table
- `GET /api/v1/concordance/{upload_id}/export/csv`: Export as CSV
- `GET /api/v1/concordance/{upload_id}/export/excel`: Export as Excel

### Integration

**File**: `backend/app/services/extraction_orchestrator.py`

Concordance generation is integrated into the extraction workflow:
- Runs automatically after successful data extraction
- Non-critical (won't fail extraction if concordance fails)
- Logs results for monitoring

## Database Migration

**File**: `backend/alembic/versions/20251124_add_concordance_tables.py`

Creates `concordance_tables` table with:
- Foreign keys to `document_uploads`, `properties`, `financial_periods`
- Indexes for performance (upload_id, field_name, agreement metrics)
- JSON columns for flexible model value storage

## How It Works

### 1. Document Upload Flow

```
1. User uploads PDF document
2. ExtractionOrchestrator extracts data using all models
3. Data is stored in database (balance_sheet_data, income_statement_data, etc.)
4. ConcordanceService.generate_concordance_table() is called automatically
5. All models are run again to get extraction results
6. Field values are extracted from database records
7. Model extraction results are matched to database fields
8. Agreement metrics are calculated for each field
9. Concordance records are stored in database
```

### 2. Field Value Matching

The system uses a two-step approach:

1. **Database Records as Source of Truth**: Uses already-extracted data from database tables (IncomeStatementData, BalanceSheetData, etc.) as the reference values.

2. **Model Result Matching**: For each model's extraction result, searches for matching values:
   - Searches extracted text for account codes and amounts
   - Searches extracted tables for matching rows
   - Uses normalized value comparison (handles formatting differences)

### 3. Agreement Calculation

For each field:
- Normalizes all model values (removes formatting, handles negatives)
- Finds most common normalized value (consensus)
- Calculates agreement percentage: `(agreeing_models / total_models) * 100`
- Flags consensus: `≥75%` = has consensus, `100%` = perfect agreement
- Identifies conflicting models (those that disagree)

## API Usage Examples

### Get Concordance Table

```bash
curl -X GET "http://localhost:8000/api/v1/concordance/45"
```

**Response:**
```json
{
  "success": true,
  "upload_id": 45,
  "concordance_table": [
    {
      "field": "account_4010_0000",
      "field_name": "account_4010_0000",
      "field_display_name": "Base Rentals",
      "account_code": "4010-0000",
      "values": {
        "pymupdf": "$215,671.29",
        "pdfplumber": "$215,671.29",
        "camelot": "$215,671.29",
        "layoutlm": "$215,671.29",
        "easyocr": "$215,671.29",
        "tesseract": "$215,671.29"
      },
      "normalized_value": "215671.29",
      "agreement_count": 6,
      "total_models": 6,
      "agreement_percentage": 100.0,
      "has_consensus": true,
      "is_perfect_agreement": true,
      "conflicting_models": [],
      "final_value": "215671.29",
      "final_model": "pymupdf"
    }
  ],
  "summary": {
    "total_fields": 45,
    "perfect_agreement": 40,
    "partial_agreement": 5,
    "no_agreement": 0,
    "overall_agreement_percentage": 95.5
  }
}
```

### Export as CSV

```bash
curl -X GET "http://localhost:8000/api/v1/concordance/45/export/csv" -o concordance.csv
```

### Export as Excel

```bash
curl -X GET "http://localhost:8000/api/v1/concordance/45/export/excel" -o concordance.xlsx
```

## Supported Document Types

- ✅ Income Statement
- ✅ Balance Sheet
- ✅ Cash Flow Statement
- ⚠️ Rent Roll (partial support - uses generic parsing)

## Model Coverage

All 6 extraction models are compared:
1. **PyMuPDF**: Fast digital PDF extraction
2. **PDFPlumber**: Excellent for tables
3. **Camelot**: Best for complex tables
4. **LayoutLMv3**: AI-powered document understanding
5. **EasyOCR**: Enhanced OCR for scanned documents
6. **Tesseract OCR**: Baseline OCR

## Agreement Thresholds

- **Perfect Agreement**: 100% of models agree → `is_perfect_agreement = true`
- **Consensus**: ≥75% of models agree → `has_consensus = true`
- **Partial Agreement**: 50-74% of models agree → `has_consensus = false`
- **No Agreement**: <50% of models agree → `has_consensus = false`

## Performance Considerations

- **Non-Critical**: Concordance generation won't fail the extraction if it errors
- **Async-Friendly**: Can be moved to background task in future
- **Indexed**: Database indexes on upload_id, field_name, and agreement metrics for fast queries
- **Cached**: Can add Redis caching for frequently accessed tables

## Future Enhancements

- [ ] Background task processing for large documents
- [ ] Historical trend analysis (agreement over time)
- [ ] Model performance dashboard
- [ ] Automatic alerts for low agreement fields
- [ ] Field-level confidence scores integration
- [ ] Support for more document types (rent roll, lease agreements)

## Testing

To test the concordance table system:

1. **Upload a document**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -F "file=@income_statement.pdf" \
     -F "property_id=1" \
     -F "period_id=1" \
     -F "document_type=income_statement"
   ```

2. **Wait for extraction to complete** (check extraction_status)

3. **Get concordance table**:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/concordance/{upload_id}"
   ```

4. **Export for analysis**:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/concordance/{upload_id}/export/excel" -o concordance.xlsx
   ```

## Database Schema

```sql
CREATE TABLE concordance_tables (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER NOT NULL REFERENCES document_uploads(id) ON DELETE CASCADE,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES financial_periods(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    field_display_name VARCHAR(255),
    account_code VARCHAR(50),
    model_values JSON NOT NULL,
    normalized_value VARCHAR(255),
    agreement_count INTEGER DEFAULT 0,
    total_models INTEGER DEFAULT 0,
    agreement_percentage DECIMAL(5,2) DEFAULT 0.0,
    has_consensus BOOLEAN DEFAULT FALSE,
    is_perfect_agreement BOOLEAN DEFAULT FALSE,
    conflicting_models JSON,
    final_value VARCHAR(255),
    final_model VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_concordance_tables_upload_id ON concordance_tables(upload_id);
CREATE INDEX ix_concordance_upload_field ON concordance_tables(upload_id, field_name);
CREATE INDEX ix_concordance_agreement ON concordance_tables(has_consensus, agreement_percentage);
```

## Files Created/Modified

### New Files
- `backend/app/models/concordance_table.py` - Database model
- `backend/app/services/concordance_service.py` - Service layer
- `backend/app/api/v1/concordance.py` - API endpoints
- `backend/alembic/versions/20251124_add_concordance_tables.py` - Migration

### Modified Files
- `backend/app/services/extraction_orchestrator.py` - Added concordance generation
- `backend/app/models/document_upload.py` - Added relationship
- `backend/app/models/__init__.py` - Added import
- `backend/app/main.py` - Registered router

## Summary

The Concordance Table system provides comprehensive model comparison capabilities, automatically generating comparison tables for every document upload. This enables:

- **Quality Assurance**: Identify fields with low agreement for manual review
- **Model Performance**: Track which models perform best for different document types
- **Client Reporting**: Export comparison tables for client review
- **Continuous Improvement**: Historical data for model tuning and validation

The system is production-ready, non-blocking, and fully integrated into the extraction workflow.

