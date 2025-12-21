# All Phases Quick Reference Guide

This document provides a quick overview of all 7 phases with file paths, key concepts, and implementation priorities.

---

## Phase 1: Foundation & Infrastructure (Weeks 1-3) ✓

### Critical Files
1. `backend/alembic/versions/20251221_world_class_anomaly_system.py` - Migration (7 tables)
2. `backend/app/services/batch_reprocessing_service.py` - Batch reprocessing logic
3. `backend/app/tasks/batch_reprocessing_tasks.py` - Celery task
4. `backend/app/api/v1/batch_reprocessing.py` - REST API
5. `backend/app/services/pyod_anomaly_detector.py` - PyOD integration
6. `backend/app/services/model_cache_service.py` - Model caching
7. `backend/app/core/feature_flags.py` - Feature flags

### Dependencies
```txt
pyod==2.0.0
dtaianomaly==1.0.0
llama-index==0.9.48
```

### Success Criteria
- 7 tables created
- Batch reprocessing API works
- Model cache hit rate >50%

---

## Phase 2: Active Learning & Feedback Loop (Weeks 4-6)

### Critical Files
1. `backend/app/services/adaptive_threshold_service.py` - Adaptive thresholds
2. `backend/app/services/pattern_learning_service.py` - Pattern mining
3. `backend/app/services/active_learning_service.py` - Enhanced (existing file)
4. `backend/app/api/v1/anomalies.py` - Enhanced feedback endpoints

### Key Concepts
- **Adaptive Thresholds**: Adjust detection thresholds based on user feedback
- **Pattern Learning**: Discover suppression patterns (e.g., "User always dismisses X for account Y")
- **Auto-Suppression**: Automatically suppress learned false positives
- **Uncertainty Sampling**: Query user on most uncertain anomalies

### Implementation Steps
1. Enhance feedback collection with confidence and business context
2. Implement pattern mining (lookback 90 days, min confidence 80%)
3. Create adaptive threshold calculator (maximize F1 score)
4. Build auto-suppression logic
5. Create "uncertain anomalies" endpoint

### Success Criteria
- Pattern discovery identifies >3 patterns in test data
- Adaptive thresholds update based on feedback
- Auto-suppression suppresses similar anomalies
- False positive rate decreases >20%

---

## Phase 3: Explainability (XAI) (Weeks 7-9)

### Critical Files
1. `backend/app/services/shap_explainer.py` - SHAP explanations
2. `backend/app/services/lime_explainer.py` - LIME explanations
3. `backend/app/services/anomaly_explainer.py` - Unified explainability
4. `backend/app/services/action_rules_engine.py` - Suggested actions

### Dependencies
```txt
shap==0.44.0
lime==0.2.0.1
```

### Key Concepts
- **SHAP**: Global feature importance (accurate but slow, ~10-100x slower than LIME)
- **LIME**: Local explanations (fast, on-demand)
- **Root Cause Types**: trend_break, seasonal_deviation, outlier, cross_account_inconsistency, volatility_spike, missing_data
- **Action Suggestions**: Rule-based recommendations (50+ account codes)

### SHAP vs LIME
| Feature | SHAP | LIME |
|---------|------|------|
| Scope | Global + Local | Local only |
| Speed | Slow (5-10s) | Fast (<500ms) |
| Accuracy | High | Moderate |
| Use Case | Background jobs | On-demand |

### Implementation Steps
1. Create SHAP explainer (TreeExplainer for tree models, KernelExplainer for others)
2. Create LIME explainer (LimeTabularExplainer)
3. Build root cause classifier (6 types)
4. Generate natural language explanations
5. Create action suggestion rules database
6. Store all in anomaly_explanations table

### Natural Language Template
```python
EXPLANATION_TEMPLATE = """
The value for '{field_name}' (${current_value}) is {deviation}% {direction} than expected (${expected_value}).

This anomaly was detected because:
{reasons}

Potential causes:
{causes}

Recommended actions:
{actions}
"""
```

### Success Criteria
- SHAP explanations generated for all anomalies
- LIME explanations available on-demand
- Root cause classification accuracy >85%
- Natural language explanations readable and accurate

---

## Phase 4: Cross-Property Intelligence (Weeks 10-12)

### Critical Files
1. `backend/app/services/portfolio_benchmark_service.py` - Benchmark calculation
2. `backend/app/services/anomaly_detector.py` - Enhanced with cross-property detection
3. `backend/app/api/v1/portfolio_analytics.py` - Portfolio API
4. `backend/app/tasks/benchmark_refresh_task.py` - Scheduled benchmark refresh

### Key Concepts
- **Property Grouping**: By size (<50, 50-200, 200+ units), location, type
- **Benchmarks**: mean, median, std, percentiles (25th, 75th, 90th, 95th)
- **Cross-Property Anomaly**: Property outside 5th-95th percentile range
- **Peer Comparison**: "Above 85% of peers"

### Implementation Steps
1. Create benchmark calculation service
2. Implement property grouping logic
3. Calculate portfolio statistics (percentiles, z-scores)
4. Detect cross-property anomalies
5. Create comparative analysis API
6. Schedule monthly benchmark refresh (Celery Beat)

### Grouping Strategies
```python
def group_properties(properties):
    groups = {
        'small': properties with units < 50,
        'medium': properties with 50 <= units < 200,
        'large': properties with units >= 200
    }
    return groups
```

### Success Criteria
- Benchmarks calculated for all accounts
- Cross-property anomalies detected
- Properties can be grouped by size/location/type
- Portfolio analytics API returns data

---

## Phase 5: ML-Based Coordinate Prediction (Weeks 13-15)

### Critical Files
1. `backend/app/services/layoutlm_coordinate_predictor.py` - LayoutLM integration
2. `backend/app/services/coordinate_storage_service.py` - Coordinate storage
3. `backend/app/services/extraction_orchestrator.py` - Enhanced (existing file)
4. `backend/app/utils/engines/pdfplumber_engine.py` - Word extraction (existing file)

### Dependencies
```txt
layoutparser==0.3.4
transformers==4.44.2  # Already present
```

### Key Concepts
- **PDFPlumber Word Extraction**: `extract_words()` returns {text, x0, y0, x1, y1}
- **Fuzzy Matching**: Match extracted value to word bounding box (tolerance 0.9)
- **LayoutLM v3**: Pre-trained document understanding model
- **Multi-Column Support**: Separate coordinates for period_amount vs ytd_amount

### Implementation Steps
1. Integrate PDFPlumber word extraction into template extractor
2. Create fuzzy value-to-word matcher
3. Store coordinates in pdf_field_coordinates table
4. Implement LayoutLM predictor (fallback when auto-extraction fails)
5. Fine-tune LayoutLM on REIMS PDFs (optional, requires annotated data)
6. Update anomaly coordinate retrieval API

### PDFPlumber Integration
```python
import pdfplumber

def extract_with_coordinates(pdf_path, page_number):
    pdf = pdfplumber.open(pdf_path)
    page = pdf.pages[page_number - 1]
    
    # Extract words with bounding boxes
    words = page.extract_words()
    # words = [{'text': '52,340', 'x0': 123.5, 'y0': 456.2, ...}, ...]
    
    # Extract values using existing logic
    extracted_values = extract_financial_data(page)
    
    # Match values to words
    for item in extracted_values:
        value_str = item['period_amount']
        coords = match_value_to_word(value_str, words)
        if coords:
            item['period_amount_coords'] = coords
    
    return extracted_values
```

### Success Criteria
- PDFPlumber word extraction integrated
- Coordinates stored in database
- LayoutLM model can be loaded
- Coordinate prediction confidence >75%
- Anomaly highlighting works in PDF viewer

---

## Phase 6: Model Optimization (Weeks 16-17)

### Critical Files
1. `backend/app/services/incremental_learning_service.py` - Incremental learning
2. `backend/app/tasks/anomaly_detection_tasks.py` - Parallel processing
3. `backend/app/core/celery_config.py` - Enhanced (existing file)
4. `backend/app/services/pyod_anomaly_detector.py` - GPU support (enhance existing)

### Key Concepts
- **Incremental Learning**: Update model with new data without full retrain (10x faster)
- **Sliding Window**: Keep last N samples for training
- **Model Caching**: Reuse trained models (50x faster than training)
- **GPU Acceleration**: Use CUDA for deep learning models (optional)
- **Parallel Processing**: Celery groups for batch detection

### Implementation Steps
1. Create incremental learning service
2. Implement sliding window update
3. Add GPU support to Autoencoder/LSTM
4. Configure Celery for parallel execution
5. Create parallel batch detection task
6. Monitor performance metrics

### Incremental Learning Support
| Model | Support | Method |
|-------|---------|--------|
| Isolation Forest | Partial | Retrain with sliding window |
| LOF | Partial | Retrain with sliding window |
| Autoencoder | Full | Continue training epochs |
| LSTM | Full | Fine-tune with new sequences |
| Prophet | None | Always full retrain |

### Success Criteria
- Incremental learning reduces training time >10x
- Model caching reduces detection time >50x
- Parallel processing scales linearly up to 4 workers
- GPU acceleration works (if GPU available)

---

## Phase 7: UI/UX Enhancements (Weeks 18-19)

### Critical Files
1. `backend/app/api/v1/anomalies.py` - Enhanced endpoints (modify existing)
2. `backend/app/api/websockets/anomaly_updates.py` - WebSocket for real-time updates
3. `backend/app/services/export_service.py` - Export to CSV/XLSX/JSON

### Key Endpoints

**Enhanced Anomaly Detail**:
```
GET /api/v1/anomalies/{anomaly_id}/detailed
Returns:
- anomaly data
- explanation (root cause, SHAP/LIME, actions)
- coordinates (page, bbox, confidence)
- similar_anomalies
- feedback_stats
- cross_property_context
```

**Feedback Submission**:
```
POST /api/v1/anomalies/{anomaly_id}/feedback
Triggers:
1. Record feedback
2. Update learning patterns
3. Auto-suppress similar anomalies
4. Adjust thresholds
Returns: Count of suppressed anomalies
```

**Uncertain Anomalies**:
```
GET /api/v1/anomalies/uncertain?limit=10
Returns: Anomalies most needing feedback (sorted by uncertainty)
```

**WebSocket Progress**:
```
WS /ws/batch-job/{job_id}
Sends updates every 2 seconds:
- status, progress_pct, processed, total
```

**Export**:
```
GET /api/v1/anomalies/export?format=csv&property_id=1
Exports: CSV/XLSX/JSON with explanations
```

### Implementation Steps
1. Enhance anomaly detail endpoint
2. Create WebSocket endpoint for batch job progress
3. Implement export service (CSV/XLSX/JSON)
4. Create uncertain anomalies endpoint
5. Add feedback trigger logic (pattern learning, suppression)

### Success Criteria
- Detailed anomaly API returns full explanation
- WebSocket sends real-time updates
- Export generates valid CSV/XLSX files
- Uncertain anomalies endpoint returns prioritized list

---

## Testing & Deployment

### Testing Guide
**See**: `08-TESTING-VALIDATION-GUIDE.md`

**Key Tests**:
- Unit tests: >85% coverage
- Integration tests: Critical paths
- Performance tests: Cache speedup, parallel scaling
- End-to-end tests: Full feedback loop

### Deployment Guide
**See**: `09-DEPLOYMENT-ROLLOUT-GUIDE.md`

**Rollout Strategy**:
1. Pilot (Weeks 1-6): 2-3 properties
2. Beta (Weeks 7-12): 25% properties
3. GA (Weeks 13-19): All properties

**Feature Flags**:
- Start with most flags disabled
- Enable incrementally as tested
- Monitor metrics after each enable

---

## Performance Targets

| Metric | Target | Phase |
|--------|--------|-------|
| Model cache hit rate | >70% | 1 |
| False positive rate | <10% | 2 |
| Explanation generation time | <5s | 3 |
| Benchmark calculation time | <30s per account | 4 |
| Coordinate prediction accuracy | >75% | 5 |
| Incremental learning speedup | >10x | 6 |
| API response time | <200ms | 7 |

---

## Critical Dependencies Matrix

| Phase | Libraries | Python Packages |
|-------|-----------|-----------------|
| 1 | pyod, dtaianomaly, llama-index | joblib, scipy |
| 2 | - | scikit-learn (existing) |
| 3 | shap, lime | numpy, pandas |
| 4 | - | - |
| 5 | layoutparser, transformers | easyocr (existing) |
| 6 | - | torch (optional, existing) |
| 7 | - | openpyxl (for XLSX export) |

---

## File Creation Summary

**Total New Files**: 24
**Total Modified Files**: 8

### New Files by Phase
- Phase 1: 7 files
- Phase 2: 3 files
- Phase 3: 4 files
- Phase 4: 3 files
- Phase 5: 3 files
- Phase 6: 2 files
- Phase 7: 2 files

### Modified Files
1. `backend/requirements.txt`
2. `backend/app/core/config.py`
3. `backend/.env`
4. `backend/app/services/active_learning_service.py`
5. `backend/app/services/anomaly_detector.py`
6. `backend/app/api/v1/anomalies.py`
7. `backend/app/core/celery_config.py`
8. Template extractors (TBD - find with glob)

---

## Next Steps for Cursor Taskmaster AI

1. **Start**: Read `00-MASTER-IMPLEMENTATION-GUIDE.md`
2. **Phase 1**: Follow `01-PHASE1-TASKS-CHECKLIST.md`
3. **Testing**: Use `08-TESTING-VALIDATION-GUIDE.md` after each phase
4. **Deploy**: Follow `09-DEPLOYMENT-ROLLOUT-GUIDE.md`
5. **Reference**: Use this document for quick lookups

**Ready to begin!** Start with Phase 1 database migration.
