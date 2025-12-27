# Forensic Reconciliation Elite System - Testing Guide

**Date:** December 24, 2025  
**Status:** Ready for Testing

---

## 🧪 Testing Checklist

### 1. Backend API Testing

#### Test Materiality Configuration
```bash
# Get account risk classes
curl http://localhost:8000/api/v1/forensic-reconciliation/account-risk-classes

# Create materiality config
curl -X POST http://localhost:8000/api/v1/forensic-reconciliation/materiality-configs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "property_id": 1,
    "statement_type": "balance_sheet",
    "absolute_threshold": 1000.0,
    "relative_threshold_percent": 1.0
  }'
```

#### Test Health Score
```bash
# Get health score for controller persona
curl "http://localhost:8000/api/v1/forensic-reconciliation/health-score/1/1?persona=controller"

# Get health score config
curl http://localhost:8000/api/v1/forensic-reconciliation/health-score-configs/controller
```

#### Test Exception Tiering
```bash
# Classify match tier
curl -X POST http://localhost:8000/api/v1/forensic-reconciliation/matches/1/classify-tier?auto_resolve=true

# Get suggested fix
curl -X POST http://localhost:8000/api/v1/forensic-reconciliation/matches/1/suggest-fix
```

#### Test Alert Workflow
```bash
# Snooze an alert
curl -X POST http://localhost:8000/api/v1/alerts/1/snooze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "until_period_id": 2,
    "reason": "Waiting for next period"
  }'

# Suppress an alert
curl -X POST http://localhost:8000/api/v1/alerts/1/suppress \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "reason": "False positive",
    "expires_after_periods": 3
  }'
```

---

### 2. Frontend Testing

#### Access Forensic Reconciliation Page
1. Navigate to: `http://localhost:5173/forensic-reconciliation`
2. Verify page loads without errors
3. Check property and period dropdowns populate

#### Test Cockpit View
1. Select a property and period
2. Click "Start Reconciliation" (if data available)
3. Navigate to "Cockpit" tab
4. Verify three-panel layout:
   - **Left:** Filters panel
   - **Center:** Work queue with severity grouping
   - **Right:** Evidence panel

#### Test Work Queue
1. Verify exceptions are grouped by severity (Critical → High → Medium → Info)
2. Check tier indicators are displayed
3. Test bulk selection (checkboxes)
4. Test bulk approve/reject buttons
5. Verify materiality badges
6. Check age tracking (days old)

#### Test Explainability Features
1. Select a match from work queue
2. Verify evidence panel shows:
   - **Why Flagged:** Top 3 reasons
   - **What Would Resolve:** Suggested actions
   - **What Changed:** Period comparison (if prior period data exists)
3. Test "Apply Suggestion" button (if available)

#### Test Filters
1. Test property filter
2. Test period filter
3. Test severity filter
4. Test tier filter
5. Test "Needs My Review" checkbox
6. Test "SLA Due" checkbox
7. Test "Clear Filters" button

---

### 3. Integration Testing

#### End-to-End Reconciliation Flow
1. **Create Session**
   - Select property and period
   - Click "Start Reconciliation"
   - Verify session is created

2. **Run Reconciliation**
   - Wait for reconciliation to complete
   - Verify matches are found
   - Check exception tiering is applied

3. **Review in Cockpit**
   - Navigate to Cockpit tab
   - Verify matches appear in work queue
   - Check tier classification (Tier 0, 1, 2, 3)
   - Verify materiality indicators

4. **Review Match**
   - Select a match from work queue
   - Verify evidence panel populates
   - Check explainability features
   - Test approve/reject actions

5. **Bulk Operations**
   - Select multiple matches
   - Test bulk approve
   - Test bulk reject
   - Verify status updates

---

### 4. Data Verification

#### Verify Seeded Data
```bash
# Check account risk classes
docker compose exec backend python3 -c "
from app.db.database import SessionLocal
from app.models.account_risk_class import AccountRiskClass
db = SessionLocal()
print('Account Risk Classes:', db.query(AccountRiskClass).count())
db.close()
"

# Check health score configs
docker compose exec backend python3 -c "
from app.db.database import SessionLocal
from app.models.health_score_config import HealthScoreConfig
db = SessionLocal()
configs = db.query(HealthScoreConfig).all()
for c in configs:
    print(f'{c.persona}: {c.weights_json}')
db.close()
"
```

#### Verify Database Tables
```bash
# List all forensic-related tables
docker compose exec postgres psql -U reims -d reims -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE '%forensic%' 
     OR table_name LIKE '%materiality%' 
     OR table_name LIKE '%alert_suppression%'
     OR table_name LIKE '%account_synonym%'
     OR table_name LIKE '%calculated_rule%'
     OR table_name LIKE '%health_score%')
ORDER BY table_name;
"
```

---

### 5. Performance Testing

#### Test Large Dataset
1. Create reconciliation session with large property portfolio
2. Run reconciliation with 1000+ matches
3. Verify work queue performance
4. Test filtering performance
5. Test bulk operations performance

#### Test Concurrent Users
1. Simulate multiple users accessing Cockpit
2. Test concurrent match approvals
3. Verify no race conditions

---

### 6. Error Handling Testing

#### Test Error Scenarios
1. **No Data Available**
   - Select property/period with no financial data
   - Verify helpful error message
   - Check troubleshooting tips appear

2. **Invalid API Calls**
   - Test with invalid property_id
   - Test with invalid period_id
   - Verify appropriate error responses

3. **Network Errors**
   - Simulate backend downtime
   - Verify frontend handles gracefully
   - Check error messages are user-friendly

---

## 📊 Test Results Template

### Backend API Tests
- [ ] Materiality configuration endpoints
- [ ] Health score endpoints
- [ ] Exception tiering endpoints
- [ ] Alert workflow endpoints
- [ ] Chart of accounts endpoints
- [ ] Calculated rules endpoints

### Frontend Tests
- [ ] Page loads successfully
- [ ] Property/period selection works
- [ ] Cockpit view displays correctly
- [ ] Work queue groups by severity
- [ ] Filters work correctly
- [ ] Evidence panel populates
- [ ] Explainability features display
- [ ] Bulk operations work

### Integration Tests
- [ ] End-to-end reconciliation flow
- [ ] Match approval/rejection
- [ ] Discrepancy resolution
- [ ] Health score calculation
- [ ] Exception tiering application

### Data Tests
- [ ] Seeded data exists
- [ ] Tables are accessible
- [ ] Queries return correct results

---

## 🐛 Known Issues

1. **Migration Conflict:** There's a conflict with `20251219_add_extraction_task_id` migration. This doesn't affect new tables.

2. **Prior Period Data:** Period comparison requires historical data to be loaded.

3. **PDF Integration:** PDF viewer links are placeholders (need actual PDF viewer integration).

---

## ✅ Success Criteria

- All API endpoints return 200/201 status codes
- Frontend loads without errors
- Cockpit view displays correctly
- Work queue groups exceptions properly
- Explainability features work
- Bulk operations function correctly
- No console errors in browser
- No backend errors in logs

---

## 📝 Reporting Issues

When reporting issues, include:
1. **Steps to Reproduce**
2. **Expected Behavior**
3. **Actual Behavior**
4. **Screenshots/Logs**
5. **Environment Details** (browser, OS, etc.)

---

**Happy Testing!** 🚀

