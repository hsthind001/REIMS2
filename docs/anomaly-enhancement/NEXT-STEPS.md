# Next Steps After Cursor Implementation

**Date**: 2025-12-21  
**Phase 1 Status**: 95% Complete  
**Ready for**: Deployment & Testing

---

## Immediate Actions Required

### 1. Add Missing Dependencies to requirements.txt

```bash
cd backend

# Add these lines to requirements.txt:
echo "" >> requirements.txt
echo "# Phase 3: Explainability (XAI)" >> requirements.txt
echo "shap==0.44.0" >> requirements.txt
echo "lime==0.2.0.1" >> requirements.txt
echo "" >> requirements.txt
echo "# Optional: Enhanced time series anomaly detection" >> requirements.txt
echo "dtaianomaly==1.0.0" >> requirements.txt
echo "" >> requirements.txt
echo "# Optional: LLM-powered model selection" >> requirements.txt
echo "llama-index==0.9.48" >> requirements.txt
```

### 2. Install Dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run Database Migration

```bash
cd backend

# Check current migration
alembic current

# Expected output: 20251220_0300

# Run migration
alembic upgrade head

# Verify tables created
psql -U reims_user -d reims_db -c "\dt anomaly*"
psql -U reims_user -d reims_db -c "\dt batch_reprocessing_jobs"
psql -U reims_user -d reims_db -c "\dt cross_property_benchmarks"
psql -U reims_user -d reims_db -c "\dt pdf_field_coordinates"
```

Expected tables:
- anomaly_detections (existing)
- anomaly_feedback (existing, enhanced)
- anomaly_learning_patterns (existing)
- anomaly_explanations (NEW)
- anomaly_model_cache (NEW)
- batch_reprocessing_jobs (NEW)
- cross_property_benchmarks (NEW)
- pdf_field_coordinates (NEW)
- pyod_model_selection_log (NEW)

### 4. Update Environment Variables

Add to `backend/.env`:

```bash
# ============================================================================
# ANOMALY DETECTION ENHANCEMENT CONFIGURATION
# ============================================================================

# ---------- PyOD & ML Configuration ----------
PYOD_ENABLED=true
PYOD_LLM_MODEL_SELECTION=false  # Set to true if you have OpenAI API key
OPENAI_API_KEY=  # Optional - for LLM model selection

# ---------- GPU Acceleration ----------
ANOMALY_USE_GPU=false
GPU_DEVICE_ID=0

# ---------- Model Caching ----------
MODEL_CACHE_ENABLED=true
MODEL_CACHE_TTL_DAYS=30
INCREMENTAL_LEARNING_ENABLED=true
BATCH_SIZE=32
MAX_EPOCHS=50

# ---------- XAI (Explainability) Configuration ----------
SHAP_ENABLED=true
LIME_ENABLED=true
XAI_BACKGROUND_SAMPLES=100

# ---------- Active Learning ----------
ACTIVE_LEARNING_ENABLED=true
ADAPTIVE_THRESHOLDS_ENABLED=true
AUTO_SUPPRESSION_ENABLED=false  # Enable after testing
AUTO_SUPPRESSION_CONFIDENCE_THRESHOLD=0.8
FEEDBACK_LOOKBACK_DAYS=90

# ---------- Cross-Property Intelligence ----------
PORTFOLIO_BENCHMARKS_ENABLED=false  # Enable after data population
BENCHMARK_REFRESH_SCHEDULE='0 2 1 * *'
BENCHMARK_MIN_PROPERTIES=3

# ---------- LayoutLM Configuration ----------
LAYOUTLM_ENABLED=false  # Enable in Phase 5
LAYOUTLM_MODEL_PATH=/models/layoutlmv3-reims-finetuned
LAYOUTLM_CONFIDENCE_THRESHOLD=0.75
LAYOUTLM_USE_PRETRAINED=true

# ---------- Batch Processing ----------
BATCH_PROCESSING_CHUNK_SIZE=10
BATCH_PROCESSING_MAX_CONCURRENT=3
BATCH_PROCESSING_TIMEOUT_MINUTES=60

# ---------- Feature Flags ----------
FEATURE_FLAG_PYOD=true
FEATURE_FLAG_ACTIVE_LEARNING=true
FEATURE_FLAG_AUTO_SUPPRESSION=false
FEATURE_FLAG_SHAP=true
FEATURE_FLAG_LIME=true
FEATURE_FLAG_PORTFOLIO_BENCHMARKS=false
FEATURE_FLAG_LAYOUTLM=false
FEATURE_FLAG_COORDINATE_EXTRACTION=false
```

### 5. Restart Services

```bash
# Stop existing services
pkill -f "uvicorn"
pkill -f "celery"

# Start FastAPI
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# Start Celery worker (with anomaly queue)
celery -A app.core.celery_app worker --loglevel=info -Q anomaly,default &

# Optional: Start Celery Beat (for scheduled tasks)
celery -A app.core.celery_app beat --loglevel=info &
```

---

## Verification Tests

### Test 1: Verify Migration

```bash
psql -U reims_user -d reims_db << SQL
-- Check tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name LIKE 'anomaly%' 
   OR table_name LIKE 'batch%'
   OR table_name LIKE 'cross%'
   OR table_name LIKE 'pdf_field%'
   OR table_name LIKE 'pyod%';

-- Check anomaly_feedback columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'anomaly_feedback'
  AND column_name IN ('feedback_confidence', 'business_context', 'learned_applied', 'similar_anomalies_suppressed');
SQL
```

### Test 2: Verify Feature Flags

```bash
cd backend
python << PYTHON
from app.core.feature_flags import FeatureFlags

# Test feature flags
flags = FeatureFlags.get_all_flags()
print("All Feature Flags:")
for flag, enabled in flags.items():
    print(f"  {flag}: {enabled}")

# Test specific flag
print(f"\nPyOD Enabled: {FeatureFlags.is_pyod_enabled()}")
print(f"SHAP Enabled: {FeatureFlags.is_shap_enabled()}")
PYTHON
```

### Test 3: Test Batch Reprocessing API

```bash
# Create a test batch job
curl -X POST "http://localhost:8000/api/v1/batch-reprocessing/reprocess" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "property_ids": [1],
    "job_name": "Test Batch Job",
    "document_types": ["balance_sheet", "income_statement"]
  }'

# Expected response:
# {
#   "job_id": 1,
#   "task_id": "...",
#   "status": "running",
#   "total_documents": X
# }

# Get job status
curl -X GET "http://localhost:8000/api/v1/batch-reprocessing/jobs/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test 4: Test PyOD Detector

```bash
cd backend
python << PYTHON
from app.services.pyod_anomaly_detector import PyODAnomalyDetector
from app.db.database import SessionLocal

# Initialize detector
db = SessionLocal()
detector = PyODAnomalyDetector(db)

# Get available algorithms
algorithms = detector.get_available_algorithms()
print(f"Available algorithms: {len(algorithms)}")
print(algorithms[:10])  # Print first 10

db.close()
PYTHON
```

### Test 5: Test Model Cache

```bash
cd backend
python << PYTHON
from app.services.model_cache_service import ModelCacheService
from app.db.database import SessionLocal
import numpy as np

db = SessionLocal()
cache_service = ModelCacheService(db)

# Test model key generation
key = cache_service.generate_model_key(
    property_id=1,
    account_code="4010",
    model_type="iforest",
    config={"contamination": 0.1}
)
print(f"Generated cache key: {key}")

db.close()
PYTHON
```

---

## Common Issues & Solutions

### Issue 1: Migration Fails - Table Already Exists

**Error**: `relation "anomaly_explanations" already exists`

**Solution**:
```bash
# Check if tables exist
psql -U reims_user -d reims_db -c "\dt anomaly_explanations"

# If exists, either:
# Option A: Drop tables manually
psql -U reims_user -d reims_db << SQL
DROP TABLE IF EXISTS anomaly_explanations CASCADE;
DROP TABLE IF EXISTS anomaly_model_cache CASCADE;
-- etc...
SQL

# Option B: Mark migration as done without running
alembic stamp 20251221_0000
```

### Issue 2: Import Error - pyod not found

**Error**: `ModuleNotFoundError: No module named 'pyod'`

**Solution**:
```bash
cd backend
pip install pyod>=1.1.0
```

### Issue 3: SHAP/LIME Not Available

**Warning**: `SHAP not available - feature importance explanations disabled`

**Solution**:
```bash
pip install shap==0.44.0 lime==0.2.0.1
# Restart FastAPI server
```

### Issue 4: Celery Task Not Running

**Symptom**: Batch job stuck in "queued" status

**Solution**:
```bash
# Check Celery worker is running
celery -A app.core.celery_app inspect active

# Check if anomaly queue exists
celery -A app.core.celery_app inspect registered

# Restart Celery worker
pkill -f "celery"
celery -A app.core.celery_app worker --loglevel=info -Q anomaly,default
```

---

## Development Workflow

### Adding a New Anomaly Detection

```python
# 1. Create sample data
import numpy as np
sample_data = np.random.randn(100, 5)  # 100 samples, 5 features

# 2. Use PyOD detector
from app.services.pyod_anomaly_detector import PyODAnomalyDetector
detector = PyODAnomalyDetector(db)

# 3. Analyze data characteristics
characteristics = detector.analyze_data_characteristics(sample_data)

# 4. Select optimal algorithm (auto or manual)
model_name = detector.select_optimal_model(characteristics)

# 5. Train model
model, scores = detector.train_and_detect(sample_data, model_name)

# 6. Get anomaly indices
anomaly_indices = np.where(scores > threshold)[0]
```

### Batch Reprocessing Workflow

```python
from app.services.batch_reprocessing_service import BatchReprocessingService

# 1. Create batch job
service = BatchReprocessingService(db)
job = service.create_batch_job(
    user_id=1,
    property_ids=[1, 2, 3],
    date_range_start=date(2024, 1, 1),
    date_range_end=date(2024, 12, 31),
    document_types=["balance_sheet", "income_statement"]
)

# 2. Start job (queues Celery task)
result = service.start_batch_job(job.id)

# 3. Monitor progress
while True:
    status = service.get_job_status(job.id)
    print(f"Progress: {status['progress_pct']}%")
    if status['status'] in ['completed', 'failed', 'cancelled']:
        break
    time.sleep(5)

# 4. Get results
final_status = service.get_job_status(job.id)
print(f"Completed: {final_status['successful_count']} documents")
print(f"Failed: {final_status['failed_count']} documents")
```

---

## Next Phase Preview

### Phase 2: Active Learning & Feedback Loop (Weeks 4-6)

**What to Implement**:
1. `backend/app/services/adaptive_threshold_service.py`
2. `backend/app/services/pattern_learning_service.py`
3. Enhanced feedback endpoints in anomalies API

**Key Features**:
- Adaptive threshold adjustment based on user feedback
- Pattern mining (discover suppression patterns)
- Auto-suppression of learned false positives
- Uncertainty sampling for active learning

**Prerequisites**:
- Phase 1 fully deployed and tested
- User feedback data collected (at least 50 feedback entries)
- Batch reprocessing working correctly

---

## Monitoring & Metrics

### Key Metrics to Track

```bash
# 1. Model cache hit rate
SELECT 
    COUNT(CASE WHEN use_count > 1 THEN 1 END)::float / COUNT(*) * 100 as cache_hit_rate_pct
FROM anomaly_model_cache
WHERE created_at > NOW() - INTERVAL '7 days';

# 2. Batch job statistics
SELECT 
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_duration_minutes
FROM batch_reprocessing_jobs
GROUP BY status;

# 3. Anomaly detection coverage
SELECT 
    document_type,
    COUNT(DISTINCT document_id) as documents_with_anomalies,
    COUNT(*) as total_anomalies
FROM anomaly_detections
WHERE detected_at > NOW() - INTERVAL '7 days'
GROUP BY document_type;

# 4. Feature flag usage
-- Check via application logs or:
SELECT 
    COUNT(*) as pyod_detections
FROM anomaly_detections
WHERE detection_methods @> ARRAY['iforest']::varchar[]
  AND detected_at > NOW() - INTERVAL '7 days';
```

### Logging Best Practices

Monitor these log messages:
- `"PyOD version X.X.X available"` - PyOD loaded successfully
- `"Created batch reprocessing job X with Y documents"` - Batch jobs created
- `"Model cache hit for key X"` - Cache working
- `"SHAP not available"` - Dependencies missing

---

## Success Criteria

Phase 1 is considered **SUCCESSFULLY DEPLOYED** when:

- [x] All 7 database tables created
- [ ] Migration runs without errors
- [ ] Batch reprocessing API returns 200 OK
- [ ] At least one batch job completes successfully
- [ ] PyOD detector can list available algorithms
- [ ] Model cache can store and retrieve a model
- [ ] Feature flags are readable
- [ ] Celery tasks execute without errors
- [ ] No critical errors in logs

**Target Date**: Complete by 2025-12-22

---

## Support

If you encounter issues:
1. Check logs: `docker logs reims2-backend`
2. Review verification report: `docs/anomaly-enhancement/IMPLEMENTATION-VERIFICATION-REPORT.md`
3. Consult master guide: `docs/anomaly-enhancement/00-MASTER-IMPLEMENTATION-GUIDE.md`
4. Check quick reference: `docs/anomaly-enhancement/ALL-PHASES-QUICK-REFERENCE.md`

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-21
