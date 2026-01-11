# Forensic Reconciliation Elite System - Quick Reference

**Quick access guide for common tasks and endpoints**

---

## 🚀 Quick Start

### Access the System
- **Frontend:** `http://localhost:5173/forensic-reconciliation`
- **Backend API:** `http://localhost:8000/api/v1/forensic-reconciliation`
- **Health Check:** `http://localhost:8000/health`

---

## 📋 Common API Endpoints

### Materiality & Risk
```bash
# Get materiality configs for a property
GET /api/v1/forensic-reconciliation/materiality-configs/{property_id}

# Create materiality config
POST /api/v1/forensic-reconciliation/materiality-configs
{
  "property_id": 1,
  "statement_type": "balance_sheet",
  "absolute_threshold": 1000.0,
  "relative_threshold_percent": 1.0
}

# Get account risk classes
GET /api/v1/forensic-reconciliation/account-risk-classes
```

### Health Score
```bash
# Get health score (with persona)
GET /api/v1/forensic-reconciliation/health-score/{property_id}/{period_id}?persona=controller

# Get health score trend
GET /api/v1/forensic-reconciliation/health-score/{property_id}/trend?periods=6

# Get/Update health score config
GET /api/v1/forensic-reconciliation/health-score-configs/{persona}
PUT /api/v1/forensic-reconciliation/health-score-configs/{persona}
```

### Exception Tiering
```bash
# Classify match into tier
POST /api/v1/forensic-reconciliation/matches/{match_id}/classify-tier?auto_resolve=true

# Get suggested fix
POST /api/v1/forensic-reconciliation/matches/{match_id}/suggest-fix

# Bulk classify tiers
POST /api/v1/forensic-reconciliation/matches/bulk-tier
{
  "match_ids": [1, 2, 3],
  "auto_resolve": true
}
```

### Alert Workflow
```bash
# Snooze alert
POST /api/v1/alerts/{alert_id}/snooze
{
  "until_period_id": 2,
  "reason": "Waiting for next period"
}

# Suppress alert
POST /api/v1/alerts/{alert_id}/suppress
{
  "reason": "False positive",
  "expires_after_periods": 3
}

# Get workflow status
GET /api/v1/alerts/{alert_id}/workflow-status
```

### Reconciliation
```bash
# Create session
POST /api/v1/forensic-reconciliation/sessions
{
  "property_id": 1,
  "period_id": 1,
  "session_type": "full_reconciliation"
}

# Run reconciliation
POST /api/v1/forensic-reconciliation/sessions/{session_id}/run
{
  "use_exact": true,
  "use_fuzzy": true,
  "use_calculated": true,
  "use_inferred": true,
  "use_rules": true
}

# Get matches
GET /api/v1/forensic-reconciliation/sessions/{session_id}/matches?status_filter=pending

# Approve/Reject match
POST /api/v1/forensic-reconciliation/matches/{match_id}/approve
POST /api/v1/forensic-reconciliation/matches/{match_id}/reject
{
  "reason": "Rejection reason"
}
```

---

## 🎨 Frontend Components

### Main Page
- **Location:** `src/pages/ForensicReconciliation.tsx`
- **Route:** `/forensic-reconciliation`
- **Tabs:** Overview, Cockpit, Matches, Discrepancies

### Cockpit Components
- **Work Queue:** `src/components/forensic/ReconciliationWorkQueue.tsx`
- **Filters:** `src/components/forensic/ReconciliationFilters.tsx`
- **Evidence Panel:** `src/components/forensic/EvidencePanel.tsx`

### Explainability Components
- **Why Flagged:** `src/components/forensic/WhyFlaggedCard.tsx`
- **Resolution Suggestions:** `src/components/forensic/ResolutionSuggestions.tsx`
- **Period Comparison:** `src/components/forensic/PeriodComparison.tsx`
- **Combined Panel:** `src/components/forensic/ExplainabilityPanel.tsx`

---

## 🗄️ Database Tables

### Core Tables
- `forensic_reconciliation_sessions`
- `forensic_matches`
- `forensic_discrepancies`

### Configuration Tables
- `materiality_configs`
- `account_risk_classes`
- `health_score_configs`

### Enhancement Tables
- `auto_resolution_rules`
- `account_synonyms`
- `account_mappings`
- `calculated_rules`
- `alert_suppressions`
- `alert_snoozes`
- `alert_suppression_rules`

---

## 🔧 Services

### Core Services
- `MaterialityService` - Materiality threshold calculation
- `ExceptionTieringService` - Tier classification and auto-resolution
- `HealthScoreService` - Health score calculation with personas
- `ForensicReconciliationService` - Main reconciliation orchestration

### Enhancement Services
- `ChartOfAccountsService` - Account mapping and synonyms
- `CalculatedRulesEngine` - Versioned calculated rules
- `AnomalyEnsembleService` - Ensemble anomaly scoring
- `RealEstateAnomalyRules` - Domain-specific anomaly detection
- `AlertWorkflowService` - Alert snoozing and suppression

---

## 📊 Exception Tiers

| Tier | Confidence | Materiality | Action |
|------|-----------|------------|--------|
| Tier 0 | ≥98% | Immaterial | Auto-close |
| Tier 1 | 90-97% | Material | Auto-suggest fix |
| Tier 2 | 70-89% | Material | Route to committee |
| Tier 3 | <70% | Any | Escalate |

---

## 🎯 Health Score Personas

| Persona | Focus | Blocked Close Rules |
|---------|-------|-------------------|
| Auditor | Approval rate | None |
| Controller | Compliance | Covenant violations, Material discrepancies |
| Analyst | Confidence | Material discrepancies |
| Investor | Trends | Material discrepancies |

---

## 🐛 Troubleshooting

### No Matches Found
1. Check data availability: `GET /data-availability/{property_id}/{period_id}`
2. Verify documents uploaded
3. Verify documents extracted
4. Check account codes match patterns

### Migration Issues
```bash
# Check current migration
docker compose exec backend alembic current

# Apply migrations
docker compose exec backend alembic upgrade head

# Check tables
docker compose exec postgres psql -U reims -d reims -c "\dt"
```

### Service Issues
```bash
# Check backend health
docker compose exec backend curl http://localhost:8000/health

# Check logs
docker compose logs backend | tail -50

# Restart services
docker compose restart backend
```

---

## 📚 Documentation Files

1. **FORENSIC_RECONCILIATION_FINAL_SUMMARY.md** - Complete overview
2. **FORENSIC_RECONCILIATION_ELITE_COMPLETE.md** - Implementation guide
3. **FORENSIC_RECONCILIATION_ELITE_IMPLEMENTATION.md** - Technical details
4. **DEPLOYMENT_STATUS.md** - Deployment checklist
5. **TESTING_GUIDE.md** - Testing procedures
6. **QUICK_REFERENCE.md** - This file

---

## ✅ Verification Commands

```bash
# Verify models
docker compose exec backend python3 -c "from app.models import *; print('✅ Models OK')"

# Verify services
docker compose exec backend python3 -c "from app.services import *; print('✅ Services OK')"

# Verify API routes
docker compose exec backend python3 -c "from app.api.v1.forensic_reconciliation import router; print(f'✅ {len(router.routes)} routes')"

# Verify tables
docker compose exec postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM materiality_configs;"
```

---

**Last Updated:** December 24, 2025

