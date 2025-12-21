# REIMS2 Anomaly Detection Enhancement - Master Implementation Guide

## Document Overview

This is the master guide for implementing a world-class anomaly detection system for REIMS2. The implementation is split into 7 phases over 19 weeks, with each phase documented in detail.

## Documentation Structure

```
docs/anomaly-enhancement/
├── 00-MASTER-IMPLEMENTATION-GUIDE.md (this file)
├── 01-PHASE1-FOUNDATION-INFRASTRUCTURE.md
├── 02-PHASE2-ACTIVE-LEARNING.md
├── 03-PHASE3-EXPLAINABILITY-XAI.md
├── 04-PHASE4-CROSS-PROPERTY-INTELLIGENCE.md
├── 05-PHASE5-ML-COORDINATE-PREDICTION.md
├── 06-PHASE6-MODEL-OPTIMIZATION.md
├── 07-PHASE7-UI-UX-ENHANCEMENTS.md
├── 08-TESTING-VALIDATION-GUIDE.md
├── 09-DEPLOYMENT-ROLLOUT-GUIDE.md
└── 10-APPENDIX-RESEARCH-REFERENCES.md
```

## Quick Start for Cursor Taskmaster AI

1. **Prerequisites Check**: Ensure Python 3.11+, PostgreSQL 14+, Redis, Celery are running
2. **Start with Phase 1**: Begin with `01-PHASE1-FOUNDATION-INFRASTRUCTURE.md`
3. **Follow Order**: Complete phases sequentially (1→2→3→4→5→6→7)
4. **Run Tests**: After each phase, run tests from `08-TESTING-VALIDATION-GUIDE.md`
5. **Deploy Gradually**: Follow `09-DEPLOYMENT-ROLLOUT-GUIDE.md` for rollout strategy

## Implementation Phases Overview

### Phase 1: Foundation & Infrastructure (Weeks 1-3)
**Document**: `01-PHASE1-FOUNDATION-INFRASTRUCTURE.md`

**What to Build**:
- 7 new database tables (migrations)
- Batch reprocessing system (service + API + Celery tasks)
- PyOD 2.0 integration (45+ ML algorithms)
- Model caching service

**Dependencies**:
- pyod==2.0.0
- dtaianomaly==1.0.0
- llama-index==0.9.48

**Output**: Batch reprocessing works, PyOD models can be trained and cached

---

### Phase 2: Active Learning & Feedback Loop (Weeks 4-6)
**Document**: `02-PHASE2-ACTIVE-LEARNING.md`

**What to Build**:
- Enhanced feedback collection (UI + API)
- Adaptive threshold service (ALFred-inspired)
- Pattern learning service (auto-suppression)

**Dependencies**: None (uses existing libraries)

**Output**: System learns from user feedback and auto-suppresses false positives

---

### Phase 3: Explainability (XAI) (Weeks 7-9)
**Document**: `03-PHASE3-EXPLAINABILITY-XAI.md`

**What to Build**:
- SHAP integration (global feature importance)
- LIME integration (local explanations)
- Root cause analysis service
- Natural language explanation generator
- Action suggestion engine

**Dependencies**:
- shap==0.44.0
- lime==0.2.0.1

**Output**: Every anomaly has explanation, root cause, and suggested actions

---

### Phase 4: Cross-Property Intelligence (Weeks 10-12)
**Document**: `04-PHASE4-CROSS-PROPERTY-INTELLIGENCE.md`

**What to Build**:
- Portfolio benchmarking service
- Cross-property anomaly detection
- Comparative analysis API
- Portfolio analytics dashboard backend

**Dependencies**: None (uses existing libraries)

**Output**: Properties compared to portfolio benchmarks, outliers identified

---

### Phase 5: ML-Based Coordinate Prediction (Weeks 13-15)
**Document**: `05-PHASE5-ML-COORDINATE-PREDICTION.md`

**What to Build**:
- LayoutLM v3 integration
- Enhanced coordinate extraction (PDFPlumber word matching)
- Coordinate storage service
- LayoutLM fine-tuning pipeline

**Dependencies**:
- layoutparser==0.3.4
- transformers==4.44.2 (already present)

**Output**: PDF fields highlighted accurately, even when auto-extraction fails

---

### Phase 6: Model Optimization (Weeks 16-17)
**Document**: `06-PHASE6-MODEL-OPTIMIZATION.md`

**What to Build**:
- Incremental learning service
- GPU acceleration support
- Parallel processing (Celery groups)
- Model performance monitoring

**Dependencies**: None (uses existing PyTorch/Celery)

**Output**: 50x faster detection via caching, 10x faster via incremental learning

---

### Phase 7: UI/UX Enhancements (Weeks 18-19)
**Document**: `07-PHASE7-UI-UX-ENHANCEMENTS.md`

**What to Build**:
- Enhanced anomaly detail API
- WebSocket real-time updates
- Export functionality (CSV/XLSX/JSON)
- Uncertain anomalies endpoint

**Dependencies**: None

**Output**: Rich UI with explanations, real-time progress, export capabilities

---

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL 14+ with JSONB support
- **Task Queue**: Celery + Redis
- **ML Libraries**: PyOD 2.0, SHAP, LIME, Prophet, ARIMA, Transformers
- **PDF Processing**: PDFPlumber, PyMuPDF, EasyOCR

### Frontend (existing)
- **Framework**: React + TypeScript
- **PDF Viewing**: react-pdf
- **State Management**: Context API / Redux

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Object Storage**: MinIO
- **Caching**: Redis
- **GPU Support**: NVIDIA CUDA (optional)

---

## Global Dependencies Update

**File**: `backend/requirements.txt`

Add these dependencies:

```txt
# Phase 1: PyOD & Foundation
pyod==2.0.0  # Upgrade from 1.1.0 - 45+ anomaly detection algorithms
dtaianomaly==1.0.0  # New 2025 time series anomaly library
llama-index==0.9.48  # LLM-powered model selection

# Phase 3: Explainability
shap==0.44.0  # SHapley Additive exPlanations (global feature importance)
lime==0.2.0.1  # Local Interpretable Model-agnostic Explanations

# Phase 5: Layout Understanding
layoutparser==0.3.4  # Layout analysis utilities for PDFs

# Utilities
tqdm==4.66.1  # Progress bars for batch operations
scikit-learn>=1.3.0  # Already present, ensure version for PyOD compatibility
```

---

## Global Environment Variables

**File**: `backend/.env`

Add these configuration variables:

```bash
# ============================================================================
# ANOMALY DETECTION ENHANCEMENT CONFIGURATION
# ============================================================================

# ---------- PyOD & ML Configuration ----------
PYOD_ENABLED=true
PYOD_LLM_MODEL_SELECTION=true  # Use LLM for intelligent model selection
OPENAI_API_KEY=sk-...  # Required for LLM model selection (optional feature)

# ---------- GPU Acceleration ----------
ANOMALY_USE_GPU=false  # Set to true if NVIDIA GPU available
GPU_DEVICE_ID=0  # GPU device index (0-based)
PYTORCH_CUDA_AVAILABLE=false  # Auto-detected by PyTorch

# ---------- Model Caching ----------
MODEL_CACHE_ENABLED=true
MODEL_CACHE_TTL_DAYS=30  # Model cache expiration (days)
INCREMENTAL_LEARNING_ENABLED=true
BATCH_SIZE=32  # Batch size for deep learning models
MAX_EPOCHS=50  # Max training epochs for neural networks

# ---------- XAI (Explainability) Configuration ----------
SHAP_ENABLED=true  # Enable SHAP explanations (computationally intensive)
LIME_ENABLED=true  # Enable LIME explanations (fast, on-demand)
XAI_BACKGROUND_SAMPLES=100  # Number of background samples for SHAP

# ---------- Active Learning ----------
ACTIVE_LEARNING_ENABLED=true
ADAPTIVE_THRESHOLDS_ENABLED=true
AUTO_SUPPRESSION_ENABLED=true  # Auto-suppress learned false positives
AUTO_SUPPRESSION_CONFIDENCE_THRESHOLD=0.8  # Confidence threshold for auto-suppression (0-1)
FEEDBACK_LOOKBACK_DAYS=90  # Days to look back for feedback analysis

# ---------- Cross-Property Intelligence ----------
PORTFOLIO_BENCHMARKS_ENABLED=true
BENCHMARK_REFRESH_SCHEDULE='0 2 1 * *'  # Cron: 2 AM on 1st of month
BENCHMARK_MIN_PROPERTIES=3  # Minimum properties required for benchmarking

# ---------- LayoutLM Configuration ----------
LAYOUTLM_ENABLED=true
LAYOUTLM_MODEL_PATH=/models/layoutlmv3-reims-finetuned  # Path to fine-tuned model
LAYOUTLM_CONFIDENCE_THRESHOLD=0.75  # Minimum confidence for coordinate predictions
LAYOUTLM_USE_PRETRAINED=true  # Use pre-trained model if fine-tuned not available

# ---------- Batch Processing ----------
BATCH_PROCESSING_CHUNK_SIZE=10  # Number of documents to process in parallel
BATCH_PROCESSING_MAX_CONCURRENT=3  # Maximum concurrent batch jobs
BATCH_PROCESSING_TIMEOUT_MINUTES=60  # Timeout for batch jobs

# ---------- Feature Flags ----------
FEATURE_FLAG_PYOD=true
FEATURE_FLAG_ACTIVE_LEARNING=true
FEATURE_FLAG_AUTO_SUPPRESSION=false  # Start disabled, enable after testing
FEATURE_FLAG_SHAP=true
FEATURE_FLAG_LIME=true
FEATURE_FLAG_PORTFOLIO_BENCHMARKS=false  # Start disabled, enable after data population
FEATURE_FLAG_LAYOUTLM=false  # Start disabled, enable after model training
```

---

## Database Schema Overview

### New Tables (7 total)

1. **`anomaly_explanations`** - Stores XAI explanations (SHAP, LIME, root causes, actions)
2. **`anomaly_model_cache`** - Serialized trained models with metadata
3. **`cross_property_benchmarks`** - Portfolio statistical benchmarks
4. **`batch_reprocessing_jobs`** - Batch job tracking and progress
5. **`pdf_field_coordinates`** - Dedicated coordinate storage with confidence
6. **`pyod_model_selection_log`** - LLM model selection reasoning
7. **`anomaly_feedback`** (updated) - Enhanced with new columns

**Migration File**: `backend/alembic/versions/20251221_world_class_anomaly_system.py` (created in Phase 1)

---

## File Structure (New Files Created)

```
backend/
├── alembic/versions/
│   └── 20251221_world_class_anomaly_system.py  # Phase 1
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── batch_reprocessing.py  # Phase 1
│   │   │   ├── portfolio_analytics.py  # Phase 4
│   │   │   └── anomalies.py (updated)  # Phase 7
│   │   └── websockets/
│   │       └── anomaly_updates.py  # Phase 7
│   ├── services/
│   │   ├── batch_reprocessing_service.py  # Phase 1
│   │   ├── pyod_anomaly_detector.py  # Phase 1
│   │   ├── model_cache_service.py  # Phase 1
│   │   ├── adaptive_threshold_service.py  # Phase 2
│   │   ├── pattern_learning_service.py  # Phase 2
│   │   ├── shap_explainer.py  # Phase 3
│   │   ├── lime_explainer.py  # Phase 3
│   │   ├── anomaly_explainer.py  # Phase 3
│   │   ├── portfolio_benchmark_service.py  # Phase 4
│   │   ├── layoutlm_coordinate_predictor.py  # Phase 5
│   │   ├── coordinate_storage_service.py  # Phase 5
│   │   └── incremental_learning_service.py  # Phase 6
│   ├── tasks/
│   │   ├── batch_reprocessing_tasks.py  # Phase 1
│   │   └── anomaly_detection_tasks.py  # Phase 6
│   └── core/
│       ├── config.py (updated)  # Phase 1
│       ├── feature_flags.py (new)  # Phase 1
│       └── celery_config.py (updated)  # Phase 6
├── tests/
│   └── services/
│       ├── test_pyod_anomaly_detector.py
│       ├── test_shap_explainer.py
│       ├── test_lime_explainer.py
│       ├── test_anomaly_explainer.py
│       ├── test_pattern_learning_service.py
│       ├── test_adaptive_threshold_service.py
│       ├── test_portfolio_benchmark_service.py
│       ├── test_layoutlm_coordinate_predictor.py
│       ├── test_model_cache_service.py
│       └── test_batch_reprocessing_service.py
└── requirements.txt (updated)
```

---

## Development Workflow for Cursor Taskmaster AI

### Step 1: Environment Setup
```bash
# Ensure virtual environment is active
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install base dependencies (before starting phases)
pip install --upgrade pip
pip install -r backend/requirements.txt

# Verify PostgreSQL is running
psql -U reims_user -d reims_db -c "SELECT version();"

# Verify Redis is running
redis-cli ping  # Should return "PONG"

# Verify Celery is configured
celery -A app.core.celery_app inspect active
```

### Step 2: Phase-by-Phase Implementation

For each phase:

1. **Read the phase document** (e.g., `01-PHASE1-FOUNDATION-INFRASTRUCTURE.md`)
2. **Check dependencies** in the "Dependencies" section
3. **Create database migrations** if required
4. **Implement services** following the detailed specifications
5. **Create API endpoints** with request/response models
6. **Write unit tests** for all services
7. **Run tests** and ensure >85% coverage
8. **Update environment variables** in `.env`
9. **Manual testing** with sample data
10. **Git commit** with descriptive message

### Step 3: Testing After Each Phase

```bash
# Run unit tests
pytest backend/tests/services/test_*.py -v --cov=backend/app/services

# Run integration tests
pytest backend/tests/integration/ -v

# Check code coverage
pytest --cov=backend/app --cov-report=html
```

### Step 4: Database Migration

```bash
# After creating migration file in Phase 1
cd backend
alembic upgrade head

# Verify tables created
psql -U reims_user -d reims_db -c "\dt anomaly*"
```

---

## Success Criteria Checklist

Use this checklist to verify each phase is complete:

### Phase 1 Success Criteria
- [ ] 7 new database tables created and migrated
- [ ] Batch reprocessing API accepts requests
- [ ] PyOD detector can train and cache models
- [ ] Model cache hit rate >50% in tests
- [ ] Batch job progress updates in database

### Phase 2 Success Criteria
- [ ] User feedback API accepts and stores feedback
- [ ] Pattern discovery identifies >3 patterns in test data
- [ ] Adaptive thresholds update based on feedback
- [ ] Auto-suppression suppresses similar anomalies

### Phase 3 Success Criteria
- [ ] SHAP explanations generated for anomalies
- [ ] LIME explanations generated on-demand
- [ ] Root cause classifier works for 6 root cause types
- [ ] Natural language explanations are readable
- [ ] Action suggestions provided for 50+ account codes

### Phase 4 Success Criteria
- [ ] Benchmarks calculated for all properties
- [ ] Cross-property anomalies detected
- [ ] Portfolio analytics API returns data
- [ ] Properties can be grouped by size/location/type

### Phase 5 Success Criteria
- [ ] PDFPlumber word extraction works
- [ ] Coordinates stored in pdf_field_coordinates table
- [ ] LayoutLM model can be loaded
- [ ] Coordinate prediction confidence >75%
- [ ] Anomaly highlighting works in PDF viewer

### Phase 6 Success Criteria
- [ ] Incremental learning reduces training time >10x
- [ ] Model caching reduces detection time >50x
- [ ] Parallel processing scales linearly up to 4 workers
- [ ] GPU acceleration works (if GPU available)

### Phase 7 Success Criteria
- [ ] Detailed anomaly API returns full explanation
- [ ] WebSocket sends real-time batch job updates
- [ ] Export API generates CSV/XLSX files
- [ ] Uncertain anomalies endpoint returns prioritized list

---

## Performance Benchmarks

Target performance metrics:

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Model cache hit rate | >70% | Monitor cache_hit / total_requests |
| Model training speedup | 50x with cache | Compare cached vs non-cached training time |
| Incremental learning speedup | 10x vs full retrain | Compare incremental vs full retrain time |
| Anomaly detection latency | <500ms per document | Measure end-to-end detection time |
| SHAP explanation time | <5s per anomaly | Measure SHAP computation time |
| LIME explanation time | <500ms per anomaly | Measure LIME computation time |
| Batch processing throughput | >100 docs/minute | Measure parallel batch processing rate |
| False positive rate | <10% | Calculate from user feedback |
| Precision | >90% | Calculate from confirmed anomalies |
| Recall | >85% | Calculate from missed anomalies (feedback) |

---

## Risk Mitigation

### Technical Risks

1. **PyOD 2.0 not released yet**
   - **Mitigation**: Use PyOD 1.1.0 initially, upgrade when 2.0 available
   - **Alternative**: Use dtaianomaly for some algorithms

2. **SHAP computation too slow**
   - **Mitigation**: Run SHAP in background Celery tasks, not blocking
   - **Alternative**: Use LIME only for faster explanations

3. **LayoutLM model too large**
   - **Mitigation**: Use quantized models or DistilLayoutLM
   - **Alternative**: Use rule-based coordinate matching only

4. **GPU not available**
   - **Mitigation**: All features work on CPU, just slower
   - **Fallback**: Reduce batch sizes for deep learning models

### Data Risks

1. **Insufficient historical data for ML**
   - **Mitigation**: Require minimum 10 data points, fallback to statistical methods
   - **Alert**: Log warnings when data insufficient

2. **Feedback data sparse**
   - **Mitigation**: Start with rule-based patterns, transition to ML-based when data sufficient
   - **Incentive**: Encourage user feedback with UI prompts

3. **Benchmark calculation fails (too few properties)**
   - **Mitigation**: Require minimum 3 properties for benchmarks
   - **Fallback**: Disable cross-property features if insufficient properties

---

## Monitoring & Observability

### Logging Strategy

Use structured logging throughout:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "anomaly_detected",
    anomaly_id=anomaly.id,
    property_id=property.id,
    account_code=account_code,
    severity=anomaly.severity,
    detection_methods=anomaly.detection_methods,
    ensemble_confidence=anomaly.ensemble_confidence,
    has_explanation=explanation is not None,
    execution_time_ms=execution_time
)
```

### Metrics to Track

**Application Metrics**:
- Anomaly detection requests per minute
- Average detection latency
- Model cache hit/miss ratio
- Feedback submission rate
- Pattern discovery count

**Business Metrics**:
- False positive rate (from feedback)
- Precision and recall scores
- User engagement (feedback percentage)
- Anomaly resolution time

**System Metrics**:
- CPU usage during detection
- Memory usage for model caching
- GPU utilization (if enabled)
- Celery queue length
- Database query performance

---

## Support & Troubleshooting

### Common Issues

1. **Migration fails: "relation already exists"**
   - **Solution**: Check if tables exist: `\dt anomaly*` in psql
   - **Fix**: Drop tables manually or rollback migration

2. **PyOD model training fails**
   - **Check**: Sufficient data points (minimum 10)
   - **Check**: Feature matrix has no NaN/Inf values
   - **Solution**: Add data validation and cleaning

3. **SHAP computation times out**
   - **Solution**: Increase Celery task timeout
   - **Alternative**: Disable SHAP, use LIME only

4. **LayoutLM model not found**
   - **Check**: Model downloaded to correct path
   - **Solution**: Download model: `from transformers import AutoModel; AutoModel.from_pretrained("microsoft/layoutlmv3-base")`

5. **Batch job stuck in "running" status**
   - **Check**: Celery worker is running: `celery -A app.core.celery_app inspect active`
   - **Solution**: Restart Celery workers

---

## Next Steps for Implementation

1. **Start with Phase 1**: Open `01-PHASE1-FOUNDATION-INFRASTRUCTURE.md`
2. **Set up development environment**: Install dependencies, configure `.env`
3. **Run existing tests**: Ensure current system works before modifications
4. **Create feature branch**: `git checkout -b feature/anomaly-enhancement-phase1`
5. **Implement incrementally**: One service at a time, test after each
6. **Commit frequently**: Small, focused commits with descriptive messages

---

## Document Maintenance

**Last Updated**: 2025-12-21
**Version**: 1.0.0
**Maintained By**: REIMS2 Development Team

**Change Log**:
- 2025-12-21: Initial version created

---

## Contact & Support

For questions or issues during implementation:
- **Documentation**: This folder (`docs/anomaly-enhancement/`)
- **Code Reference**: Plan file at `/home/hsthind/.claude/plans/lexical-growing-marble.md`
- **Research Sources**: See `10-APPENDIX-RESEARCH-REFERENCES.md`

---

**Ready to Begin?** Start with [Phase 1: Foundation & Infrastructure](./01-PHASE1-FOUNDATION-INFRASTRUCTURE.md)
