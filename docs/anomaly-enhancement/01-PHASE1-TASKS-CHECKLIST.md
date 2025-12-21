# Phase 1: Implementation Tasks Checklist

## Quick Reference
- **Duration**: Weeks 1-3
- **Files to Create**: 18 new files
- **Files to Modify**: 3 existing files
- **Database Tables**: 7 new tables

## Task 1.1: Database Migration ✓
**File**: `backend/alembic/versions/20251221_world_class_anomaly_system.py`

**Action Items**:
- [ ] Create migration file (see 01-PHASE1-FOUNDATION-INFRASTRUCTURE.md for full code)
- [ ] Update `down_revision` to last migration ID
- [ ] Run `alembic upgrade head`
- [ ] Verify 7 tables created in database

**Tables Created**:
1. anomaly_explanations
2. anomaly_model_cache
3. cross_property_benchmarks
4. batch_reprocessing_jobs
5. pdf_field_coordinates
6. pyod_model_selection_log
7. anomaly_feedback (4 new columns)

---

## Task 1.2: Batch Reprocessing System

### File 1: Service
**Path**: `backend/app/services/batch_reprocessing_service.py`

**Key Methods**:
- `create_batch_job()` - Create job with filters
- `start_batch_job()` - Queue Celery task
- `get_job_status()` - Return progress
- `cancel_job()` - Cancel running job
- `list_jobs()` - List all jobs

**Dependencies**: BatchReprocessingJob model, DocumentUpload model

---

### File 2: Celery Task
**Path**: `backend/app/tasks/batch_reprocessing_tasks.py`

**Key Task**:
```python
@celery_app.task(bind=True, max_retries=3)
def reprocess_documents_batch(self, job_id: int):
    # Process documents in chunks of 10
    # Update job progress after each chunk
    # Handle errors gracefully
    pass
```

**Logic Flow**:
1. Load job from database
2. Query documents matching filters
3. Process in chunks (10 at a time)
4. For each document: detect anomalies
5. Update job progress every chunk
6. Mark job complete/failed

---

### File 3: API Endpoints
**Path**: `backend/app/api/v1/batch_reprocessing.py`

**Endpoints**:
- `POST /api/v1/batch-reprocessing/reprocess` - Create and start job
- `GET /api/v1/batch-reprocessing/jobs/{job_id}` - Get job status
- `POST /api/v1/batch-reprocessing/jobs/{job_id}/cancel` - Cancel job
- `GET /api/v1/batch-reprocessing/jobs` - List jobs

**Request/Response Models** (create in same file):
- BatchJobCreate
- BatchJobResponse
- BatchJobStatusResponse

---

### File 4: Pydantic Models
**Path**: `backend/app/schemas/batch_reprocessing.py`

**Models**:
```python
class BatchJobCreate(BaseModel):
    property_ids: Optional[List[int]] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    document_types: Optional[List[str]] = None
    extraction_status_filter: str = 'all'
    job_name: Optional[str] = None

class BatchJobResponse(BaseModel):
    job_id: int
    job_name: str
    status: str
    total_documents: int
    created_at: datetime
    # ... other fields

class BatchJobStatusResponse(BaseModel):
    # ... detailed status fields
    progress_pct: int
    estimated_completion_at: Optional[datetime]
```

---

## Task 1.3: PyOD 2.0 Integration

### File 1: PyOD Detector Service
**Path**: `backend/app/services/pyod_anomaly_detector.py`

**Key Methods**:
- `select_optimal_model_llm()` - LLM-powered model selection
- `train_model()` - Train PyOD model
- `detect_anomalies()` - Detect using trained model
- `get_available_algorithms()` - List 45+ algorithms

**PyOD Algorithms to Support**:
- Isolation Forest (IForest)
- Local Outlier Factor (LOF)
- One-Class SVM (OCSVM)
- ECOD (Empirical Cumulative Distribution)
- COPOD (Copula-based)
- And 40+ more...

**Integration Points**:
- Use ModelCacheService for caching
- Log model selection to pyod_model_selection_log table
- Feature engineering from AnomalyFeatureEngineer

---

### File 2: Model Selection Logic
**Include in pyod_anomaly_detector.py**

**LLM Prompt Template**:
```python
PROMPT = """
Given the following data characteristics:
- Sample size: {sample_size}
- Features: {feature_count}
- Seasonality detected: {has_seasonality}
- Trend detected: {has_trend}
- Distribution: {distribution_type}
- Volatility: {volatility_level}

Recommend the top 3 PyOD anomaly detection algorithms from this list:
{available_algorithms}

For each recommendation, provide:
1. Algorithm name
2. Why it's suitable for this data
3. Expected performance
4. Computational cost

Format as JSON.
"""
```

---

## Task 1.4: Model Caching Service

### File: Model Cache Service
**Path**: `backend/app/services/model_cache_service.py`

**Key Methods**:
- `get_or_train_model()` - Retrieve cached or train new
- `cache_model()` - Serialize and store model
- `invalidate_cache()` - Force retrain
- `should_invalidate()` - Check cache validity

**Cache Key Generation**:
```python
import hashlib
import json

def generate_model_key(property_id, account_code, model_type, config):
    key_data = {
        'property_id': property_id,
        'account_code': account_code,
        'model_type': model_type,
        'config': sorted(config.items())
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_str.encode()).hexdigest()
```

**Cache Invalidation Rules**:
- Age > 30 days
- Model accuracy < threshold
- New data distribution differs (KS test p < 0.05)
- Manual user request

**Serialization**:
```python
import joblib
import io

def serialize_model(model):
    buffer = io.BytesIO()
    joblib.dump(model, buffer, compress=3)
    return buffer.getvalue()

def deserialize_model(model_bytes):
    buffer = io.BytesIO(model_bytes)
    return joblib.load(buffer)
```

---

## Task 1.5: Feature Flags Module

### File: Feature Flags
**Path**: `backend/app/core/feature_flags.py`

**Content**:
```python
"""
Feature Flags for Anomaly Enhancement

Allows gradual rollout of new features.
"""
import os
from typing import Dict

class FeatureFlags:
    """Global feature flags for anomaly detection enhancements."""
    
    # Phase 1
    PYOD_ENABLED = os.getenv('FEATURE_FLAG_PYOD', 'true').lower() == 'true'
    MODEL_CACHE_ENABLED = os.getenv('MODEL_CACHE_ENABLED', 'true').lower() == 'true'
    BATCH_REPROCESSING_ENABLED = os.getenv('BATCH_REPROCESSING_ENABLED', 'true').lower() == 'true'
    
    # Phase 2
    ACTIVE_LEARNING_ENABLED = os.getenv('ACTIVE_LEARNING_ENABLED', 'true').lower() == 'true'
    AUTO_SUPPRESSION_ENABLED = os.getenv('AUTO_SUPPRESSION_ENABLED', 'false').lower() == 'true'
    
    # Phase 3
    SHAP_ENABLED = os.getenv('SHAP_ENABLED', 'true').lower() == 'true'
    LIME_ENABLED = os.getenv('LIME_ENABLED', 'true').lower() == 'true'
    
    # Phase 4
    PORTFOLIO_BENCHMARKS_ENABLED = os.getenv('PORTFOLIO_BENCHMARKS_ENABLED', 'false').lower() == 'true'
    
    # Phase 5
    LAYOUTLM_ENABLED = os.getenv('LAYOUTLM_ENABLED', 'false').lower() == 'true'
    
    # Phase 6
    INCREMENTAL_LEARNING_ENABLED = os.getenv('INCREMENTAL_LEARNING_ENABLED', 'true').lower() == 'true'
    GPU_ACCELERATION_ENABLED = os.getenv('ANOMALY_USE_GPU', 'false').lower() == 'true'
    
    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        """Return all feature flags as dictionary."""
        return {
            attr: getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith('_') and attr.isupper()
        }
    
    @classmethod
    def is_enabled(cls, flag_name: str) -> bool:
        """Check if specific flag is enabled."""
        return getattr(cls, flag_name, False)
```

---

## Task 1.6: Configuration Updates

### File: Settings
**Path**: `backend/app/core/config.py`

**Add to Settings class**:
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # ========== ANOMALY DETECTION ENHANCEMENT ==========
    
    # PyOD Configuration
    PYOD_ENABLED: bool = True
    PYOD_LLM_MODEL_SELECTION: bool = False  # Requires OpenAI API key
    
    # Model Caching
    MODEL_CACHE_ENABLED: bool = True
    MODEL_CACHE_TTL_DAYS: int = 30
    
    # GPU Acceleration
    ANOMALY_USE_GPU: bool = False
    GPU_DEVICE_ID: int = 0
    
    # Active Learning
    ACTIVE_LEARNING_ENABLED: bool = True
    AUTO_SUPPRESSION_CONFIDENCE_THRESHOLD: float = 0.8
    FEEDBACK_LOOKBACK_DAYS: int = 90
    
    # XAI
    SHAP_ENABLED: bool = True
    LIME_ENABLED: bool = True
    XAI_BACKGROUND_SAMPLES: int = 100
    
    # Batch Processing
    BATCH_PROCESSING_CHUNK_SIZE: int = 10
    BATCH_PROCESSING_MAX_CONCURRENT: int = 3
    BATCH_PROCESSING_TIMEOUT_MINUTES: int = 60
    
    # LayoutLM
    LAYOUTLM_ENABLED: bool = False
    LAYOUTLM_MODEL_PATH: str = "/models/layoutlmv3-reims-finetuned"
    LAYOUTLM_CONFIDENCE_THRESHOLD: float = 0.75
```

---

## Testing Requirements

### Unit Tests to Create

1. `backend/tests/services/test_batch_reprocessing_service.py`
2. `backend/tests/services/test_pyod_anomaly_detector.py`
3. `backend/tests/services/test_model_cache_service.py`
4. `backend/tests/api/test_batch_reprocessing.py`

### Test Coverage Goals
- Service layer: >85%
- API layer: >80%
- Integration tests: Critical paths

### Sample Test Structure
```python
import pytest
from sqlalchemy.orm import Session
from app.services.batch_reprocessing_service import BatchReprocessingService

def test_create_batch_job(db_session: Session):
    service = BatchReprocessingService(db_session)
    job = service.create_batch_job(
        user_id=1,
        property_ids=[1, 2, 3],
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2024, 12, 31)
    )
    assert job.id is not None
    assert job.status == 'queued'
    assert job.total_documents > 0
```

---

## Validation Checklist

### Database
- [ ] All 7 tables exist in database
- [ ] Indexes created on all specified columns
- [ ] Foreign key constraints work
- [ ] JSONB columns accept valid JSON
- [ ] Migration can be rolled back successfully

### Batch Reprocessing
- [ ] Can create batch job via API
- [ ] Job queues Celery task
- [ ] Progress updates in database
- [ ] Can cancel running job
- [ ] Results summary populated on completion

### PyOD Integration
- [ ] Can list available algorithms
- [ ] Can train Isolation Forest model
- [ ] Model detection returns anomaly scores
- [ ] LLM model selection works (if OpenAI key configured)

### Model Caching
- [ ] Model serializes/deserializes correctly
- [ ] Cache hit reduces training time >50x
- [ ] Cache invalidation works
- [ ] Expired models cleaned up

### Feature Flags
- [ ] Flags readable from environment
- [ ] Flags control feature availability
- [ ] Can toggle flags without code changes

---

## Deployment Steps

1. **Update Dependencies**
```bash
pip install -r backend/requirements.txt
```

2. **Run Migration**
```bash
cd backend
alembic upgrade head
```

3. **Update Environment Variables**
```bash
# Add to .env
PYOD_ENABLED=true
MODEL_CACHE_ENABLED=true
# ... see 00-MASTER-IMPLEMENTATION-GUIDE.md for full list
```

4. **Restart Services**
```bash
# Restart FastAPI server
# Restart Celery workers
celery -A app.core.celery_app worker --loglevel=info -Q anomaly,default
```

5. **Verify Deployment**
```bash
# Test batch reprocessing endpoint
curl -X POST http://localhost:8000/api/v1/batch-reprocessing/reprocess \
  -H "Content-Type: application/json" \
  -d '{"property_ids": [1], "job_name": "Test Job"}'
```

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Migration Success | 100% | All 7 tables exist |
| API Response Time | <200ms | Test batch job creation |
| Model Cache Hit Rate | >50% | Monitor cache_hit / total_requests |
| Batch Job Throughput | >10 docs/min | Monitor completed jobs |
| Test Coverage | >85% | pytest --cov |

---

## Next Steps

After Phase 1 completion:
1. Verify all validation checklist items
2. Run full test suite
3. Deploy to staging environment
4. Proceed to Phase 2: Active Learning

**Continue to**: [Phase 2: Active Learning & Feedback Loop](./02-PHASE2-ACTIVE-LEARNING.md)
