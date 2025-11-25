# PDF Regeneration Guide

## Overview

This feature allows you to regenerate income statement PDFs from database data, matching the original format. This enables verification that extracted values match the original PDF.

## How It Works

1. **Upload** an income statement PDF (e.g., ESP 2023 Income Statement)
2. **Extract** data using the extraction system (already done)
3. **Regenerate** PDF from database using the new endpoint
4. **Compare** original vs regenerated PDF to verify extraction accuracy

## API Endpoint

### Regenerate Income Statement PDF

```
GET /api/v1/documents/uploads/{upload_id}/regenerate-pdf
```

**Parameters:**
- `upload_id` (path): Document upload ID

**Response:**
- PDF file (application/pdf)
- Filename: `regenerated_{original_filename}.pdf`

**Example:**

```bash
# Get upload_id from your uploaded document
curl -X GET "http://localhost:8000/api/v1/documents/uploads/123/regenerate-pdf" \
  --output regenerated_income_statement.pdf
```

## Usage Example

### Step 1: Find Your Upload ID

```bash
# List all uploads
curl "http://localhost:8000/api/v1/documents/uploads?property_code=esp&limit=10"
```

Look for the upload_id of your ESP 2023 Income Statement.

### Step 2: Regenerate PDF

```bash
curl -X GET "http://localhost:8000/api/v1/documents/uploads/{upload_id}/regenerate-pdf" \
  --output regenerated_esp_2023_income_statement.pdf
```

### Step 3: Compare PDFs

Open both PDFs side-by-side:
- **Original PDF**: Your uploaded file
- **Regenerated PDF**: Generated from database

Compare:
- ✅ Account codes match
- ✅ Account names match
- ✅ Period amounts match
- ✅ YTD amounts match
- ✅ Percentages match
- ✅ Totals match

## Features

### Format Matching

The regenerated PDF matches the original format:
- **Header**: Property name, "Income Statement", Period, Accounting Basis
- **Columns**: Account Code | Account Name | Period to Date (%) | Year to Date (%)
- **Sections**: INCOME, EXPENSES (with proper headers)
- **Styling**: Subtotals and totals are bold with borders
- **Amounts**: Formatted without commas (e.g., `229422.31` not `229,422.31`)

### Data Source

All data comes from the database:
- `income_statement_headers` table (header info)
- `income_statement_data` table (line items)
- Ordered by `line_number` to maintain original sequence

## Implementation Details

### Service: `PDFGeneratorService`

**Location:** `backend/app/services/pdf_generator_service.py`

**Methods:**
- `generate_income_statement_pdf(upload_id, db)` - Main method to generate PDF
- `_generate_income_statement_html(header, items, property_info, period_info)` - HTML generation

### Technology Stack

- **WeasyPrint**: Converts HTML/CSS to PDF
- **HTML/CSS**: Styling matches original PDF format
- **SQLAlchemy**: Database queries

## Error Handling

The endpoint handles:
- ✅ Missing upload (404)
- ✅ Wrong document type (400 - only income statements supported)
- ✅ Missing header data (404)
- ✅ Missing line items (404)
- ✅ Generation errors (500)

## Testing

### Test Steps

1. **Upload Test Document**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -F "file=@ESP_2023_Income_Statement.pdf" \
     -F "property_code=esp" \
     -F "period_year=2023" \
     -F "period_month=12" \
     -F "document_type=income_statement"
   ```

2. **Wait for Extraction** (check status)
   ```bash
   curl "http://localhost:8000/api/v1/documents/uploads/{upload_id}"
   ```

3. **Regenerate PDF**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/documents/uploads/{upload_id}/regenerate-pdf" \
     --output test_regenerated.pdf
   ```

4. **Verify Data**
   - Open both PDFs
   - Compare line by line
   - Check totals match

## Future Enhancements

Potential improvements:
- [ ] Support for balance sheets
- [ ] Support for cash flow statements
- [ ] Support for rent rolls
- [ ] Custom formatting options
- [ ] Multi-page support with page breaks
- [ ] Watermark indicating "Regenerated from Database"
- [ ] Side-by-side comparison view

## Troubleshooting

### PDF Not Generating

**Check:**
1. Upload exists: `GET /api/v1/documents/uploads/{upload_id}`
2. Document type is `income_statement`
3. Extraction completed successfully
4. Data exists in database

**Debug:**
```bash
# Check extracted data
curl "http://localhost:8000/api/v1/documents/uploads/{upload_id}/data"
```

### Format Doesn't Match

**Common Issues:**
- Amount formatting (commas vs no commas)
- Font differences
- Column widths
- Section headers

**Solution:** Adjust CSS in `_generate_income_statement_html()` method

### Missing Data

**Check:**
- Line items exist: Query `income_statement_data` table
- Header exists: Query `income_statement_headers` table
- Line numbers are set: Check `line_number` column

## Code Structure

```
backend/
├── app/
│   ├── services/
│   │   └── pdf_generator_service.py  # PDF generation service
│   └── api/
│       └── v1/
│           └── documents.py          # API endpoint
```

## Related Endpoints

- `GET /api/v1/documents/uploads/{upload_id}` - Get upload details
- `GET /api/v1/documents/uploads/{upload_id}/data` - Get extracted data
- `GET /api/v1/documents/uploads/{upload_id}/download` - Download original PDF

