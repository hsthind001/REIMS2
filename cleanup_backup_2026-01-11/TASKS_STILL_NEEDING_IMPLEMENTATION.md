# Tasks Still Needing Implementation

## Overview
While all 70 tasks in the task-master system are marked as complete, there are several areas identified as incomplete, partial, or deferred based on code analysis and implementation status documents.

## Status Summary
- **Task-Master Tasks**: 70/70 Complete (100%)
- **Code TODOs Found**: 2 major items
- **Placeholder Implementations**: 6 items
- **Deferred Features**: 5 items (from IMPLEMENTATION_STATUS.txt)
- **Partial Implementations**: 2 items

---

## 🔴 High Priority - Code TODOs

### 1. PDF Overlay Creation (pdf_field_locator.py)
- **File**: `backend/app/services/pdf_field_locator.py:291`
- **Status**: TODO - Placeholder
- **Description**: Implement PDF overlay creation for highlighting coordinates
- **Impact**: Needed for visual PDF annotation in review workflows
- **Complexity**: Medium

### 2. LayoutLM Fine-Tuning (layoutlm_coordinator.py)
- **File**: `backend/app/services/layoutlm_coordinator.py:384`
- **Status**: TODO - Placeholder
- **Description**: Implement custom dataset and training loop for LayoutLM model fine-tuning
- **Impact**: Improves PDF coordinate prediction accuracy
- **Complexity**: High (requires ML expertise)

---

## 🟡 Medium Priority - Placeholder Implementations

### 3. Model Runtime Metrics Collection
- **File**: `backend/app/services/model_monitoring_service.py:166-171`
- **Status**: Placeholder values (45.0 seconds, 5.0 seconds, 100 batches)
- **Description**: Replace placeholder runtime metrics with actual timing data collection
- **Impact**: Accurate performance monitoring
- **Complexity**: Medium

### 4. Review Service Placeholders
- **File**: `backend/app/services/review_service.py:410-416`
- **Status**: Placeholder boolean values
- **Description**: Implement actual logic for:
  - `is_covenant_impacting` determination
  - `is_dscr_affecting` determination
- **Impact**: Accurate risk assessment in review workflow
- **Complexity**: Low-Medium

### 5. Review Auto-Suggestion Consistency Factor
- **File**: `backend/app/services/review_auto_suggestion_service.py:163`
- **Status**: Placeholder value (1.0)
- **Description**: Implement actual consistency factor calculation
- **Impact**: Better account mapping suggestions
- **Complexity**: Low

### 6. Accounting Anomaly Detector Placeholders
- **File**: `backend/app/services/accounting_anomaly_detector.py:158-172`
- **Status**: Multiple placeholders
- **Description**: Implement:
  - Transaction date field checking
  - Expected provision accounts validation
  - Currency mismatch detection
- **Impact**: More accurate accounting anomaly detection
- **Complexity**: Medium

---

## 🟢 Low Priority - Deferred Features (from IMPLEMENTATION_STATUS.txt)

### 7. Detailed Review/Correction UI
- **Status**: Deferred (backend ready)
- **Description**: Frontend UI for detailed review and correction of extracted data
- **Impact**: Better user experience for data correction
- **Complexity**: Medium
- **Note**: Backend API is ready, only frontend needed

### 8. Review Workflow Tests
- **Status**: Deferred
- **Description**: Comprehensive test suite for review workflow
- **Impact**: Quality assurance
- **Complexity**: Medium

### 9. Trend Analysis Charts
- **Status**: Deferred
- **Description**: Visual trend analysis charts for financial data
- **Impact**: Better data visualization
- **Complexity**: Low-Medium

### 10. Export Download Buttons in UI
- **Status**: Deferred (works via API)
- **Description**: Add download buttons in frontend for export functionality
- **Impact**: Better UX (currently requires API calls)
- **Complexity**: Low

### 11. Additional Testing Coverage
- **Status**: Partial (50% coverage, target 85%)
- **Description**: Increase test coverage from 50% to 85%
- **Impact**: Production readiness
- **Complexity**: High (time-consuming)

---

## 📊 Summary by Category

### By Priority
- **High Priority**: 2 items (PDF overlay, LayoutLM fine-tuning)
- **Medium Priority**: 4 items (Runtime metrics, Review placeholders, etc.)
- **Low Priority**: 5 items (Deferred features)

### By Type
- **ML/AI Features**: 2 items
- **UI/UX Features**: 3 items
- **Backend Logic**: 4 items
- **Testing**: 1 item
- **Performance Monitoring**: 1 item

### By Complexity
- **Low**: 2 items
- **Medium**: 6 items
- **High**: 2 items

---

## 🎯 Recommended Implementation Order

1. **Quick Wins** (Low complexity, high impact):
   - Export download buttons in UI
   - Review auto-suggestion consistency factor
   - Review service placeholders

2. **Core Features** (Medium complexity):
   - Model runtime metrics collection
   - Detailed review/correction UI
   - Accounting anomaly detector placeholders

3. **Advanced Features** (High complexity):
   - PDF overlay creation
   - LayoutLM fine-tuning
   - Comprehensive test coverage

---

## 📝 Notes

- All critical functionality is implemented and working
- Deferred items are non-blocking for production use
- Placeholders are functional but use default/estimated values
- System is production-ready for pilot deployment
- Remaining work can be prioritized based on user feedback

