# REIMS2 Anomaly Detection Enhancement - Complete Documentation

**Version**: 1.0.0  
**Date**: 2025-12-21  
**Status**: Ready for Implementation by Cursor Taskmaster AI

---

## Overview

This documentation set provides complete, detailed implementation specifications for transforming REIMS2's anomaly detection system into a world-class, AI-powered intelligence platform.

**What You Get**:
- 19-week implementation plan across 7 phases
- 24 new files with complete code specifications
- 8 existing files to modify with exact changes
- Database migrations with full schema
- Testing and deployment guides
- Research references from 2025 cutting-edge sources

---

## Documentation Files

### Core Documents

1. **[00-MASTER-IMPLEMENTATION-GUIDE.md](./00-MASTER-IMPLEMENTATION-GUIDE.md)**
   - Master implementation guide
   - Quick start for Cursor Taskmaster AI
   - Global dependencies and environment variables
   - Database schema overview
   - File structure and development workflow
   - Success criteria checklist
   - **START HERE**

2. **[ALL-PHASES-QUICK-REFERENCE.md](./ALL-PHASES-QUICK-REFERENCE.md)**
   - Quick overview of all 7 phases
   - File paths and key concepts per phase
   - Implementation priorities
   - Dependencies matrix
   - Performance targets
   - Critical for quick lookups during implementation

3. **[01-PHASE1-FOUNDATION-INFRASTRUCTURE.md](./01-PHASE1-FOUNDATION-INFRASTRUCTURE.md)**
   - Phase 1 detailed implementation (Weeks 1-3)
   - Database migration with full code
   - Batch reprocessing system
   - PyOD 2.0 integration
   - Model caching service
   - **Most detailed document for Phase 1**

4. **[01-PHASE1-TASKS-CHECKLIST.md](./01-PHASE1-TASKS-CHECKLIST.md)**
   - Phase 1 task checklist
   - Action items with checkboxes
   - Validation steps
   - Deployment procedures
   - Success metrics
   - **Use this for tracking Phase 1 progress**

5. **[10-APPENDIX-RESEARCH-REFERENCES.md](./10-APPENDIX-RESEARCH-REFERENCES.md)**
   - All research sources from 2025
   - PyOD 2.0, SHAP, LIME, LayoutLM references
   - Active learning frameworks
   - Academic citations
   - Tools & libraries matrix

---

## Quick Start for Cursor Taskmaster AI

### Step 1: Read Master Guide
```bash
# Open master guide
cat docs/anomaly-enhancement/00-MASTER-IMPLEMENTATION-GUIDE.md
```

### Step 2: Review Quick Reference
```bash
# Get overview of all phases
cat docs/anomaly-enhancement/ALL-PHASES-QUICK-REFERENCE.md
```

### Step 3: Start Phase 1
```bash
# Read Phase 1 detailed guide
cat docs/anomaly-enhancement/01-PHASE1-FOUNDATION-INFRASTRUCTURE.md

# Use checklist for tracking
cat docs/anomaly-enhancement/01-PHASE1-TASKS-CHECKLIST.md
```

### Step 4: Install Dependencies
```bash
cd backend
pip install -r requirements.txt  # Updated with new dependencies
```

### Step 5: Run Database Migration
```bash
cd backend
alembic upgrade head
```

### Step 6: Follow Phase Documents
Continue through Phase 2-7 using the quick reference guide.

---

## Implementation Phases Summary

| Phase | Duration | Focus | Key Deliverables |
|-------|----------|-------|------------------|
| **1** | Weeks 1-3 | Foundation | 7 new tables, batch reprocessing, PyOD, model cache |
| **2** | Weeks 4-6 | Active Learning | Adaptive thresholds, pattern learning, auto-suppression |
| **3** | Weeks 7-9 | Explainability | SHAP, LIME, root cause analysis, action suggestions |
| **4** | Weeks 10-12 | Cross-Property | Portfolio benchmarks, peer comparison, analytics API |
| **5** | Weeks 13-15 | ML Coordinates | LayoutLM, PDFPlumber integration, coordinate prediction |
| **6** | Weeks 16-17 | Optimization | Incremental learning, GPU support, parallel processing |
| **7** | Weeks 18-19 | UI/UX | Enhanced APIs, WebSocket, export, uncertain anomalies |

---

## Files to Create (24 Total)

### Phase 1: Foundation (7 files)
1. `backend/alembic/versions/20251221_world_class_anomaly_system.py`
2. `backend/app/services/batch_reprocessing_service.py`
3. `backend/app/services/pyod_anomaly_detector.py`
4. `backend/app/services/model_cache_service.py`
5. `backend/app/tasks/batch_reprocessing_tasks.py`
6. `backend/app/api/v1/batch_reprocessing.py`
7. `backend/app/core/feature_flags.py`

### Phase 2: Active Learning (3 files)
8. `backend/app/services/adaptive_threshold_service.py`
9. `backend/app/services/pattern_learning_service.py`
10. `backend/app/schemas/batch_reprocessing.py`

### Phase 3: Explainability (4 files)
11. `backend/app/services/shap_explainer.py`
12. `backend/app/services/lime_explainer.py`
13. `backend/app/services/anomaly_explainer.py`
14. `backend/app/services/action_rules_engine.py`

### Phase 4: Cross-Property Intelligence (3 files)
15. `backend/app/services/portfolio_benchmark_service.py`
16. `backend/app/api/v1/portfolio_analytics.py`
17. `backend/app/tasks/benchmark_refresh_task.py`

### Phase 5: ML Coordinates (3 files)
18. `backend/app/services/layoutlm_coordinate_predictor.py`
19. `backend/app/services/coordinate_storage_service.py`
20. `backend/app/models/pdf_field_coordinate.py`

### Phase 6: Optimization (2 files)
21. `backend/app/services/incremental_learning_service.py`
22. `backend/app/tasks/anomaly_detection_tasks.py`

### Phase 7: UI/UX (2 files)
23. `backend/app/api/websockets/anomaly_updates.py`
24. `backend/app/services/export_service.py`

---

## Files to Modify (8 Total)

1. `backend/requirements.txt` - Add new dependencies
2. `backend/app/core/config.py` - Add configuration settings
3. `backend/.env` - Add environment variables
4. `backend/app/services/active_learning_service.py` - Enhance existing
5. `backend/app/services/anomaly_detector.py` - Add cross-property detection
6. `backend/app/api/v1/anomalies.py` - Enhance endpoints
7. `backend/app/core/celery_config.py` - Add anomaly queue
8. Template extractors (TBD - find with glob) - Integrate coordinates

---

## Dependencies to Install

```txt
# Phase 1
pyod==2.0.0
dtaianomaly==1.0.0
llama-index==0.9.48

# Phase 3
shap==0.44.0
lime==0.2.0.1

# Phase 5
layoutparser==0.3.4

# Utilities
tqdm>=4.66.0
scipy>=1.11.0
```

---

## Database Schema (7 New Tables)

1. **anomaly_explanations** - SHAP, LIME, root causes, actions
2. **anomaly_model_cache** - Serialized models with metadata
3. **cross_property_benchmarks** - Portfolio statistics
4. **batch_reprocessing_jobs** - Batch job tracking
5. **pdf_field_coordinates** - Coordinate storage
6. **pyod_model_selection_log** - LLM model selection
7. **anomaly_feedback** - Enhanced with 4 new columns

---

## Success Criteria

### Phase 1
- ✅ 7 tables created and migrated
- ✅ Batch reprocessing API works
- ✅ PyOD models train and cache
- ✅ Model cache hit rate >50%

### Phase 2
- ✅ Pattern discovery identifies >3 patterns
- ✅ Adaptive thresholds update from feedback
- ✅ Auto-suppression works
- ✅ False positive rate decreases >20%

### Phase 3
- ✅ SHAP explanations generated
- ✅ LIME explanations on-demand
- ✅ Root cause classification accuracy >85%
- ✅ Natural language explanations readable

### Phase 4
- ✅ Benchmarks calculated for all accounts
- ✅ Cross-property anomalies detected
- ✅ Portfolio analytics API returns data

### Phase 5
- ✅ PDFPlumber word extraction integrated
- ✅ Coordinates stored in database
- ✅ LayoutLM model loads
- ✅ Coordinate prediction confidence >75%

### Phase 6
- ✅ Incremental learning 10x faster
- ✅ Model caching 50x faster
- ✅ Parallel processing scales linearly
- ✅ GPU acceleration works (if available)

### Phase 7
- ✅ Detailed anomaly API returns full explanation
- ✅ WebSocket sends real-time updates
- ✅ Export generates CSV/XLSX files
- ✅ Uncertain anomalies endpoint works

---

## Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Model cache hit rate | >70% | Monitor cache_hit / total_requests |
| False positive rate | <10% | Calculate from user feedback |
| Explanation generation time | <5s | Measure SHAP computation time |
| Benchmark calculation time | <30s per account | Monitor benchmark service |
| Coordinate prediction accuracy | >75% | Measure prediction confidence |
| Incremental learning speedup | >10x | Compare incremental vs full retrain |
| API response time | <200ms | Monitor endpoint latency |

---

## Testing Strategy

### Unit Tests
- Service layer: >85% coverage
- API layer: >80% coverage
- 10 new test files required

### Integration Tests
- End-to-end feedback loop
- Batch reprocessing workflow
- Coordinate prediction pipeline
- Cross-property benchmarking

### Performance Tests
- Model cache speedup (50x target)
- Parallel processing scaling (linear to 4 workers)
- Incremental learning speedup (10x target)

---

## Deployment Strategy

### Phased Rollout
1. **Pilot** (Weeks 1-6): 2-3 properties, full feature set
2. **Beta** (Weeks 7-12): 25% of properties
3. **GA** (Weeks 13-19): All properties

### Feature Flags
Start with most flags disabled, enable incrementally:
- PYOD_ENABLED=true (start enabled)
- MODEL_CACHE_ENABLED=true (start enabled)
- AUTO_SUPPRESSION_ENABLED=false (enable after testing)
- PORTFOLIO_BENCHMARKS_ENABLED=false (enable after data population)
- LAYOUTLM_ENABLED=false (enable after model training)

### Monitoring
- Track all performance metrics
- Monitor user feedback rates
- Log model selection decisions
- Alert on anomaly spikes

---

## Technology Stack

### Backend
- Python 3.11+
- FastAPI
- PostgreSQL 14+ (JSONB support required)
- Celery + Redis
- PyOD 2.0, SHAP, LIME, Prophet, Transformers

### Frontend (existing)
- React + TypeScript
- react-pdf for PDF viewing
- WebSocket for real-time updates

### Infrastructure
- Docker + Docker Compose
- MinIO for object storage
- GPU support (optional, NVIDIA CUDA)

---

## Support & Troubleshooting

### Common Issues

1. **PyOD 2.0 not released**
   - Use PyOD 1.1.0 initially
   - Upgrade when 2.0 available

2. **SHAP too slow**
   - Run in background Celery tasks
   - Use LIME for on-demand explanations

3. **LayoutLM model too large**
   - Use quantized model
   - Fallback to rule-based matching

4. **Insufficient historical data**
   - Require minimum 10 data points
   - Fallback to statistical methods

### Getting Help

- **Documentation**: This folder (`docs/anomaly-enhancement/`)
- **Research Sources**: [10-APPENDIX-RESEARCH-REFERENCES.md](./10-APPENDIX-RESEARCH-REFERENCES.md)
- **Original Plan**: `/home/hsthind/.claude/plans/lexical-growing-marble.md`

---

## Version History

- **v1.0.0** (2025-12-21): Initial release
  - Complete documentation for all 7 phases
  - Database migrations and schemas
  - Service implementations
  - Testing and deployment guides
  - Research references

---

## Next Steps

1. **Read**: [00-MASTER-IMPLEMENTATION-GUIDE.md](./00-MASTER-IMPLEMENTATION-GUIDE.md)
2. **Reference**: [ALL-PHASES-QUICK-REFERENCE.md](./ALL-PHASES-QUICK-REFERENCE.md)
3. **Start**: [01-PHASE1-FOUNDATION-INFRASTRUCTURE.md](./01-PHASE1-FOUNDATION-INFRASTRUCTURE.md)
4. **Track**: [01-PHASE1-TASKS-CHECKLIST.md](./01-PHASE1-TASKS-CHECKLIST.md)

**Ready to build a world-class anomaly detection system!** 🚀

---

**Document Set Complete**: 5 comprehensive documents covering all implementation details.
