# Client-Configurable Model Scoring System

## 🎯 Overview

**Models NO LONGER calculate their own confidence.** Instead, all models are scored externally based on **client-defined factors**. This gives you complete control over how models are evaluated.

## 🔄 How It Works

### Old System (Removed)
```
Model extracts → Model calculates confidence → Score assigned
❌ Models controlled their own scores
```

### New System (Current)
```
Model extracts → External scoring service evaluates → Score assigned
✅ Client controls scoring criteria
```

## 📊 Scoring Factors (Client-Defined)

You can customize these factors to prioritize what matters most for your use case:

### Available Factors

| Factor | Default Weight | Description |
|--------|---------------|-------------|
| `text_length_weight` | 0.20 | How much text length matters |
| `text_quality_weight` | 0.25 | How much text quality (coherence, structure) matters |
| `table_detection_weight` | 0.15 | How much table detection matters |
| `table_structure_weight` | 0.10 | How much table structure quality matters |
| `processing_speed_weight` | 0.10 | How much speed matters (faster = better) |
| `accuracy_weight` | 0.15 | How much accuracy matters (if available) |
| `model_type_bonus` | {} | Bonus points for specific model types |

### Thresholds

| Threshold | Default | Description |
|-----------|---------|-------------|
| `min_text_length` | 100 | Minimum expected text length |
| `max_processing_time_ms` | 10000.0 | Maximum acceptable processing time (ms) |

## 🚀 Usage Examples

### Example 1: Default Scoring (No Custom Factors)

```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored?lang=eng" \
  -F "file=@document.pdf"
```

**Uses default weights:**
- Text length: 20%
- Text quality: 25%
- Table detection: 15%
- Table structure: 10%
- Speed: 10%
- Accuracy: 15%

### Example 2: Prioritize Speed

```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored?lang=eng" \
  -F "file=@document.pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "scoring_factors": {
      "text_length_weight": 0.10,
      "text_quality_weight": 0.20,
      "table_detection_weight": 0.10,
      "table_structure_weight": 0.05,
      "processing_speed_weight": 0.50,
      "accuracy_weight": 0.05
    }
  }'
```

**Result:** Faster models get higher scores, even if quality is slightly lower.

### Example 3: Prioritize Table Extraction

```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored?lang=eng" \
  -F "file=@document.pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "scoring_factors": {
      "text_length_weight": 0.10,
      "text_quality_weight": 0.15,
      "table_detection_weight": 0.35,
      "table_structure_weight": 0.30,
      "processing_speed_weight": 0.05,
      "accuracy_weight": 0.05
    }
  }'
```

**Result:** Models that detect and structure tables well get higher scores.

### Example 4: Prioritize AI Models

```bash
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored?lang=eng" \
  -F "file=@document.pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "scoring_factors": {
      "text_length_weight": 0.20,
      "text_quality_weight": 0.30,
      "table_detection_weight": 0.15,
      "table_structure_weight": 0.10,
      "processing_speed_weight": 0.05,
      "accuracy_weight": 0.20,
      "model_type_bonus": {
        "layoutlmv3": 0.15,
        "easyocr": 0.10
      }
    }
  }'
```

**Result:** AI models (LayoutLMv3, EasyOCR) get bonus points, making them rank higher.

### Example 5: Re-Score Existing Extraction

```bash
# Get upload_id first
curl "http://localhost:8000/api/v1/documents/uploads?limit=1"

# Re-score with custom factors
curl -X POST "http://localhost:8000/api/v1/extract/all-models-scored/123?lang=eng" \
  -H "Content-Type: application/json" \
  -d '{
    "scoring_factors": {
      "text_quality_weight": 0.50,
      "text_length_weight": 0.30,
      "processing_speed_weight": 0.20
    }
  }'
```

## 📋 Response Format

```json
{
  "success": true,
  "results": [
    {
      "model": "PyMuPDF",
      "score": 8.5,
      "confidence": 0.83,
      "success": true,
      "text_length": 5000,
      "processing_time_ms": 120.0,
      "page_count": 5,
      "score_breakdown": {
        "text_length_score": 1.0,
        "text_quality_score": 0.85,
        "table_detection_score": 0.0,
        "table_structure_score": 0.0,
        "speed_score": 0.99,
        "accuracy_score": 0.0,
        "model_bonus": 0.0
      }
    },
    {
      "model": "LayoutLMv3",
      "score": 9.2,
      "confidence": 0.91,
      "success": true,
      "text_length": 5200,
      "processing_time_ms": 3500.0,
      "score_breakdown": {
        "text_length_score": 1.0,
        "text_quality_score": 0.92,
        "table_detection_score": 0.0,
        "table_structure_score": 0.0,
        "speed_score": 0.65,
        "accuracy_score": 0.0,
        "model_bonus": 0.15
      }
    }
  ],
  "best_model": "LayoutLMv3",
  "best_score": 9.2,
  "total_models": 6,
  "successful_models": 5,
  "average_score": 8.3,
  "scoring_factors_used": {
    "text_length_weight": 0.20,
    "text_quality_weight": 0.25,
    "table_detection_weight": 0.15,
    "table_structure_weight": 0.10,
    "processing_speed_weight": 0.10,
    "accuracy_weight": 0.15,
    "model_type_bonus": {
      "layoutlmv3": 0.15
    }
  }
}
```

## 🔍 Score Breakdown Explanation

Each model's `score_breakdown` shows how it scored on each factor:

- **text_length_score**: 0.0-1.0 based on minimum text length threshold
- **text_quality_score**: 0.0-1.0 based on coherence, structure, special chars
- **table_detection_score**: 0.0-1.0 based on number of tables detected
- **table_structure_score**: 0.0-1.0 based on table structure quality
- **speed_score**: 0.0-1.0 based on processing time (faster = higher)
- **accuracy_score**: 0.0-1.0 if accuracy data is available
- **model_bonus**: Bonus points for specific model types

**Final Score Calculation:**
```
confidence = (
    text_length_score × text_length_weight +
    text_quality_score × text_quality_weight +
    table_detection_score × table_detection_weight +
    table_structure_score × table_structure_weight +
    speed_score × processing_speed_weight +
    accuracy_score × accuracy_weight +
    model_bonus
)

score = 1 + (confidence × 9)  # Convert to 1-10 scale
```

## ⚙️ Configuration Tips

### For Fast Processing
```json
{
  "processing_speed_weight": 0.50,
  "text_quality_weight": 0.30,
  "text_length_weight": 0.20
}
```

### For High Quality
```json
{
  "text_quality_weight": 0.50,
  "accuracy_weight": 0.30,
  "text_length_weight": 0.20
}
```

### For Table-Heavy Documents
```json
{
  "table_detection_weight": 0.40,
  "table_structure_weight": 0.35,
  "text_quality_weight": 0.25
}
```

### For AI Model Preference
```json
{
  "text_quality_weight": 0.30,
  "accuracy_weight": 0.25,
  "model_type_bonus": {
    "layoutlmv3": 0.20,
    "easyocr": 0.15
  }
}
```

## 🎓 Key Benefits

1. **Client Control**: You decide what matters most
2. **Transparency**: See exactly how each model scored
3. **Flexibility**: Different factors for different document types
4. **Consistency**: All models evaluated by same criteria
5. **No Model Bias**: Models can't inflate their own scores

## 📝 Important Notes

1. **Weights should sum to ~1.0** (will be auto-normalized if not)
2. **Model bonuses are added directly** (can exceed 1.0 confidence)
3. **Scores are recalculated** each time - no caching
4. **All models use same factors** - ensures fair comparison
5. **Models don't know their scores** - prevents gaming

## 🔧 API Endpoints

### New Extraction with Custom Scoring
```
POST /api/v1/extract/all-models-scored
Body: multipart/form-data (file) + JSON (scoring_factors)
```

### Re-Score Existing Extraction
```
POST /api/v1/extract/all-models-scored/{upload_id}
Body: JSON (scoring_factors)
```

## 🧪 Testing

See `EXTRACTION_SCORING_GUIDE.md` for comprehensive test steps.

