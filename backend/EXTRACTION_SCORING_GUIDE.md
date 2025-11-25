# Extraction Model Scoring System (1-10 Scale)

## 📊 How Ratings Are Calculated

### Overview
Each extraction model receives a score from **1 to 10** based on its confidence level. The scoring follows a simple linear conversion formula.

### Step-by-Step Process

#### Step 1: Each Model Extracts the PDF
- All available models run extraction on the same PDF
- Each model returns an `ExtractionResult` with a `confidence_score` (0.0 to 1.0)

#### Step 2: Confidence Score Calculation (Per Model)
Each engine calculates its own confidence using different methods:

##### **PyMuPDF** (Rule-Based)
```
Confidence Factors:
- Text Quality (50%): Length, alphanumeric ratio, word coherence, sentence structure
- Page Coverage: Expected chars per page (1000 chars/page)
- Character Adequacy: Minimum 50 characters for valid extraction

Formula:
confidence = text_quality × page_coverage × char_adequacy
```

##### **PDFPlumber** (Rule-Based, Table-Focused)
```
Confidence Factors:
- Text Quality (30%): Same as PyMuPDF
- Table Confidence (70%): If tables detected
  - Table structure (headers + rows)
  - Data completeness (non-empty cells)
  - Expected columns match
- Page Coverage: Same as PyMuPDF
- Character Adequacy: Same as PyMuPDF

Formula:
If tables found:
  confidence = (text_quality × 0.3 + table_confidence × 0.7) × page_coverage × char_adequacy
Else:
  confidence = text_quality × page_coverage × char_adequacy
```

##### **LayoutLMv3** (AI Model)
```
Confidence Factors:
- AI Model Confidence (70%): Token-level confidence from neural network
  - Average confidence across all pages
  - Token-level softmax outputs
- Text Quality (30%): Length, coherence, structure

Formula:
confidence = (avg_page_confidence × 0.7) + (text_quality × 0.3)
```

##### **EasyOCR** (AI Model)
```
Confidence Factors:
- OCR Word Confidence (80%): Word-level confidence from OCR engine
  - Average confidence across all detected words
- Text Quality (20%): Length, coherence, structure

Formula:
confidence = (avg_ocr_confidence × 0.8) + (text_quality × 0.2)
```

##### **Tesseract OCR** (OCR Engine)
```
Confidence Factors:
- OCR Confidence: Word-level confidence (0-100 scale, converted to 0-1)
- Text Quality: Length, coherence checks

Formula:
confidence = (ocr_confidence / 100) × text_quality_multiplier
```

##### **Camelot** (Table Extraction)
```
Confidence Factors:
- Table Structure: Headers, rows, data completeness
- Expected Columns Match: How well detected columns match expected

Formula:
confidence = table_structure_score × column_match_score
```

#### Step 3: Convert Confidence to Score (1-10)
```
Formula: score = 1 + (confidence × 9)

Examples:
- confidence 0.0 → score 1.0  (worst)
- confidence 0.5 → score 5.5  (medium)
- confidence 0.83 → score 8.5  (good)
- confidence 1.0 → score 10.0  (perfect)
```

### Visual Flow

```
PDF Document
    ↓
┌─────────────────────────────────────┐
│  Run All Available Models           │
│  - PyMuPDF                          │
│  - PDFPlumber                       │
│  - Camelot                          │
│  - Tesseract OCR                    │
│  - LayoutLMv3 (AI)                  │
│  - EasyOCR (AI)                     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Each Model Calculates Confidence   │
│  (0.0 to 1.0)                       │
│                                     │
│  Based on:                          │
│  - Text quality                     │
│  - Table detection                  │
│  - OCR confidence                   │
│  - AI model outputs                 │
│  - Page coverage                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Convert to Score (1-10)           │
│  score = 1 + (confidence × 9)       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Return Results                     │
│  - Model name                       │
│  - Score (1-10)                     │
│  - Confidence (0.0-1.0)             │
│  - Text length                      │
│  - Processing time                  │
│  - Best model identification        │
└─────────────────────────────────────┘
```

## 🧪 Test Steps

### Prerequisites
1. Backend service running on `http://localhost:8000`
2. At least one PDF document available for testing
3. API testing tool (curl, Postman, or browser)

### Test 1: New PDF Upload with All Models Scoring

**Endpoint:** `POST /api/v1/extract/all-models-scored`

**Steps:**
1. Prepare a test PDF file (balance sheet, income statement, or any PDF)
2. Send POST request with PDF file:

```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored?lang=eng" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_document.pdf"
```

**Expected Response:**
```json
{
  "success": true,
  "results": [
    {
      "model": "PyMuPDF",
      ",
      "score": 8.5,
      "confidence": 0.83,
      "success": true,
      "text_length": 5000,
      "processing_time_ms": 120.0,
      "page_count": 5,
      "text_quality_score": 0.85,
      "error": null
    },
    {
      "model": "PDFPlumber",
      "score": 7.8,
      "confidence": 0.76,
      "success": true,
      "text_length": 4800,
      "processing_time_ms": 250.0,
      "page_count": 5,
      "error": null
    },
    {
      "model": "LayoutLMv3",
      "score": 9.2,
      "confidence": 0.91,
      "success": true,
      "text_length": 5200,
      "processing_time_ms": 3500.0,
      "error": null
    },
    {
      "model": "EasyOCR",
      "score": 7.5,
      "confidence": 0.72,
      "success": true,
      "text_length": 4500,
      "processing_time_ms": 2800.0,
      "error": null
    }
  ],
  "best_model": "LayoutLMv3",
  "best_score": 9.2,
  "total_models": 6,
  "successful_models": 5,
  "average_score": 8.3
}
```

**Validation Checklist:**
- ✅ Response has `success: true`
- ✅ `results` array contains entries for all available models
- ✅ Each result has `score` between 1.0-10.0`
- ✅ Each result has `confidence: 0.0-1.0`
- ✅ `best_model` identifies highest scoring model
- ✅ `best_score` matches the highest score in results
- ✅ `total_models` matches number of models attempted
- ✅ `successful_models` ≤ `total_models`

### Test 2: Re-Score Existing Extraction

**Endpoint:** `POST /api/v1/extract/all-models-scored/{upload_id}`

**Steps:**
1. Find an existing document upload ID:
   ```bash
   curl "http://localhost:8000/api/v1/documents/uploads?limit=1"
   ```
   Note the `id` field (this is the `upload_id`)

2. Re-score the existing extraction:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored/123?lang=eng"
   ```
   (Replace `123` with actual `upload_id`)

**Expected Response:**
Same format as Test 1

**Validation Checklist:**
- ✅ Response format matches Test 1
- ✅ All models run successfully
- ✅ Scores are calculated correctly
- ✅ Best model is identified

### Test 3: View Existing Extraction Logs

**Endpoint:** `GET /api/v1/extract/logs`

**Steps:**
```bash
curl "http://localhost:8000/api/v1/extract/logs?limit=10"
```

**Expected Response:**
```json
[
  {
    "extraction_id": 1,
    "filename": "balance_sheet_2024.pdf",
    "confidence_score": 85.5,
    "quality_level": "good",
    "passed_checks": 8,
    "total_checks": 10,
    "issues": [],
    "warnings": [],
    "recommendations": [],
    "needs_review": false
  }
]
```

**Note:** This shows historical extractions but NOT individual model scores. Use the re-score endpoint to get model-by-model breakdown.

### Test 4: Error Handling

**Test 4a: Invalid Upload ID**
```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored/99999?lang=eng"
```
**Expected:** `404 Not Found` with message "Upload 99999 not found"

**Test 4b: Missing PDF File**
```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored/123?lang=eng"
```
(Where upload exists but PDF is missing from MinIO)
**Expected:** `404 Not Found` with message about PDF not found in storage

**Test 4c: Invalid File Type**
```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored?lang=eng" \
  -F "file=@test.txt"
```
**Expected:** `400 Bad Request` with message "File must be a PDF"

### Test 5: Performance Testing

**Steps:**
1. Measure response time for each model
2. Compare processing times:
   - Rule-based models (PyMuPDF, PDFPlumber): Should be fast (< 1 second)
   - AI models (LayoutLMv3, EasyOCR): May take longer (3-10 seconds)

**Expected Behavior:**
- Fast models complete quickly
- AI models may take longer but provide higher scores
- Total time = sum of all model processing times

### Test 6: Score Validation

**Verify Score Formula:**
For each model result, verify:
```
score = 1 + (confidence × 9)
```

**Example:**
- If confidence = 0.83, then score = 1 + (0.83 × 9) = 1 + 7.47 = 8.47 ≈ 8.5 ✅
- If confidence = 0.91, then score = 1 + (0.91 × 9) = 1 + 8.19 = 9.19 ≈ 9.2 ✅

### Test 7: Model Availability

**Check which models are available:**
```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored?lang=eng" \
  -F "file=@test.pdf" | jq '.results[].model'
```

**Expected Models (if all installed):**
- PyMuPDF
- PDFPlumber
- Camelot (if available)
- Tesseract OCR (if available)
- LayoutLMv3 (if available)
- EasyOCR (if available)

**Note:** Models may not be available if:
- Dependencies not installed
- GPU not available (for AI models)
- Model files not downloaded

## 📈 Understanding Scores

### Score Interpretation

| Score Range | Quality Level | Meaning |
|------------|---------------|---------|
| 9.0 - 10.0 | Excellent | Very high confidence, minimal errors expected |
| 7.0 - 8.9 | Good | High confidence, minor issues possible |
| 5.0 - 6.9 | Acceptable | Moderate confidence, some review recommended |
| 3.0 - 4.9 | Poor | Low confidence, significant review needed |
| 1.0 - 2.9 | Failed | Very low confidence, extraction likely failed |

### Factors Affecting Scores

**High Scores (8-10):**
- Clean, digital PDFs
- Well-structured documents
- Good text quality
- Tables properly detected
- AI models with high confidence

**Low Scores (1-5):**
- Scanned PDFs (unless OCR is good)
- Poor image quality
- Handwritten text
- Complex layouts
- Missing or corrupted pages

## 🔍 Debugging

### Check Model Logs
```bash
# View backend logs
docker logs reims-backend | grep -i "extract\|model\|score"
```

### Verify Confidence Calculation
Each model's `calculate_confidence()` method can be inspected:
- `backend/app/utils/engines/pymupdf_engine.py`
- `backend/app/utils/engines/pdfplumber_engine.py`
- `backend/app/utils/engines/layoutlm_engine.py`
- `backend/app/utils/engines/easyocr_engine.py`

### Common Issues

**Issue:** All models return score 0 or 1
- **Cause:** PDF extraction failed for all models
- **Fix:** Check PDF file integrity, verify it's not corrupted

**Issue:** AI models (LayoutLM/EasyOCR) not appearing
- **Cause:** Models not installed or GPU unavailable
- **Fix:** Check backend logs for import errors

**Issue:** Scores seem inconsistent
- **Cause:** Different models excel at different document types
- **Fix:** This is expected - use `best_model` to identify optimal model

## 📝 Example Test Script

```bash
#!/bin/bash

# Test script for extraction scoring

BASE_URL="http://localhost:8000"
PDF_FILE="test_document.pdf"

echo "🧪 Testing Extraction Scoring System"
echo "====================================="

# Test 1: New extraction
echo ""
echo "Test 1: New PDF Upload"
echo "----------------------"
curl -X POST "${BASE_URL}/api/v1/extract/all-models-scored?lang=eng" \
  -F "file=@${PDF_FILE}" \
  -w "\nHTTP Status: %{http_code}\n" \
  | jq '.'

# Test 2: Get existing uploads
echo ""
echo "Test 2: Get Existing Uploads"
echo "----------------------------"
UPLOAD_ID=$(curl -s "${BASE_URL}/api/v1/documents/uploads?limit=1" | jq -r '.[0].id // empty')
echo "Found upload_id: ${UPLOAD_ID}"

if [ ! -z "$UPLOAD_ID" ]; then
  # Test 3: Re-score existing
  echo ""
  echo "Test 3: Re-Score Existing Extraction"
  echo "--------------------------------------"
  curl -X POST "${BASE_URL}/api/v1/extract/all-models-scored/${UPLOAD_ID}?lang=eng" \
    -w "\nHTTP Status: %{http_code}\n" \
    | jq '.'
fi

# Test 4: View logs
echo ""
echo "Test 4: View Extraction Logs"
echo "----------------------------"
curl -s "${BASE_URL}/api/v1/extract/logs?limit=5" | jq '.'

echo ""
echo "✅ Tests Complete"
```

## 🎯 Key Takeaways

1. **Scores are calculated independently** for each model
2. **Confidence (0-1) is converted to score (1-10)** using linear formula
3. **Each model uses different confidence calculation methods**
4. **Best model is automatically identified** based on highest score
5. **Scores help compare model performance** on the same document
6. **Both new and existing extractions can be scored**

