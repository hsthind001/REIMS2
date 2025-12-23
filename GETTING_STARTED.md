# Forensic Reconciliation Elite System - Getting Started Guide

**Welcome to the Forensic Reconciliation Elite System!**

This guide will help you get started with using the system for forensic financial document reconciliation.

---

## 🚀 Quick Start

### 1. Access the System

**Frontend URL:** `http://localhost:5173/forensic-reconciliation`

**Backend API:** `http://localhost:8000/api/v1/forensic-reconciliation`

### 2. Verify System Status

All services should be running:
```bash
docker compose ps
```

You should see:
- ✅ `reims-backend` - Up and healthy
- ✅ `reims-frontend` - Up and healthy  
- ✅ `reims-postgres` - Up and healthy

---

## 📖 Step-by-Step Usage

### Step 1: Navigate to Forensic Reconciliation

1. Open your browser
2. Navigate to: `http://localhost:5173/forensic-reconciliation`
3. You should see the Forensic Reconciliation page

### Step 2: Select Property and Period

1. **Select Property:** Choose a property from the dropdown
2. **Select Period:** Choose a financial period (month/year)
3. **Verify Data:** The system will check if financial documents are available

### Step 3: Start Reconciliation

1. Click **"Start Reconciliation"** button
2. The system will:
   - Create a reconciliation session
   - Run matching algorithms (exact, fuzzy, calculated, inferred)
   - Apply materiality thresholds
   - Classify exceptions into tiers
   - Calculate health score

### Step 4: Review in Cockpit View

1. Click on the **"Cockpit"** tab
2. You'll see a three-panel layout:
   - **Left:** Filters (property, period, severity, tier, etc.)
   - **Center:** Work Queue (exceptions grouped by severity)
   - **Right:** Evidence Panel (details for selected match)

### Step 5: Review Matches

1. **Work Queue** shows exceptions grouped by severity:
   - 🔴 **Critical** - Requires immediate attention
   - 🟠 **High** - Important discrepancies
   - 🟡 **Medium** - Standard review items
   - 🔵 **Info** - Low priority items

2. Each exception shows:
   - Issue type
   - Amount impact
   - Confidence score
   - Materiality indicator
   - Detector agreement
   - Age (days old)
   - Exception tier

### Step 6: Use Explainability Features

1. **Select a match** from the work queue
2. **Evidence Panel** will show:
   - **Why Flagged:** Top 3 reasons why this match was flagged
   - **What Would Resolve:** Suggested actions to resolve
   - **What Changed:** Period comparison (if prior period data exists)

### Step 7: Take Action

1. **Approve Match:**
   - Click "Approve" button
   - Match status changes to "approved"

2. **Reject Match:**
   - Click "Reject" button
   - Provide rejection reason
   - Match status changes to "rejected"

3. **Bulk Operations:**
   - Select multiple matches using checkboxes
   - Click "Bulk Approve" or "Bulk Reject"
   - All selected matches are processed

### Step 8: Review Health Score

1. The **Health Score** gauge shows overall reconciliation health (0-100)
2. Different personas have different weightings:
   - **Controller:** Focuses on compliance and blocked close rules
   - **Auditor:** Focuses on approval rates
   - **Analyst:** Focuses on confidence scores
   - **Investor:** Focuses on trends

---

## 🎯 Key Features

### Materiality-Based Reconciliation

The system uses materiality thresholds to prioritize exceptions:
- **Absolute thresholds:** Fixed dollar amounts (e.g., $1,000)
- **Relative thresholds:** Percentage of revenue/assets (e.g., 1%)
- **Risk-based:** Tighter tolerances for critical accounts

### Tiered Exception Management

Exceptions are automatically classified into 4 tiers:

| Tier | Description | Action |
|------|-------------|--------|
| **Tier 0** | High confidence, immaterial | Auto-close |
| **Tier 1** | Good confidence, fixable | Auto-suggest fix |
| **Tier 2** | Needs review | Route to committee |
| **Tier 3** | Low confidence or critical | Escalate |

### Enhanced Matching

The system uses multiple matching algorithms:
- **Exact Match:** Perfect matches on account codes and amounts
- **Fuzzy Match:** Similar account names using string similarity
- **Calculated Match:** Validates financial formulas
- **Inferred Match:** ML-based pattern matching

### Explainability

Every match includes:
- **Why Flagged:** Reasons for flagging
- **What Would Resolve:** Suggested actions
- **What Changed:** Period comparison

---

## 🔧 Configuration

### Setting Materiality Thresholds

1. Navigate to API or use frontend (if available)
2. Create materiality config:
```json
{
  "property_id": 1,
  "statement_type": "balance_sheet",
  "absolute_threshold": 1000.0,
  "relative_threshold_percent": 1.0,
  "risk_class": "high"
}
```

### Configuring Health Score

1. Get current config:
```bash
GET /api/v1/forensic-reconciliation/health-score-configs/controller
```

2. Update config:
```bash
PUT /api/v1/forensic-reconciliation/health-score-configs/controller
{
  "weights_json": {
    "approval_score": 0.5,
    "confidence_score": 0.3,
    "discrepancy_penalty": 0.2
  },
  "trend_weight": 0.1,
  "volatility_weight": 0.05,
  "blocked_close_rules": ["covenant_violation", "material_discrepancy"]
}
```

---

## 📊 Understanding the Work Queue

### Severity Levels

- **🔴 Critical:** High-impact discrepancies requiring immediate attention
- **🟠 High:** Important discrepancies that need review
- **🟡 Medium:** Standard review items
- **🔵 Info:** Low-priority informational items

### Exception Tiers

- **Tier 0 (Auto-Close):** High confidence, immaterial - automatically closed
- **Tier 1 (Auto-Suggest):** Good confidence - fix suggested automatically
- **Tier 2 (Route):** Needs review - routed to appropriate committee
- **Tier 3 (Escalate):** Low confidence or critical - escalated for manual review

### Materiality Indicators

- **Material:** Amount exceeds materiality threshold
- **Immaterial:** Amount below materiality threshold

---

## 🐛 Troubleshooting

### No Matches Found

**Possible Causes:**
1. No financial data for selected property/period
2. Documents not uploaded
3. Documents not extracted
4. Account codes don't match expected patterns

**Solutions:**
1. Check data availability: Use the data availability check
2. Upload documents: Go to Data Control Center
3. Extract documents: Run extraction process
4. Verify account codes: Check Chart of Accounts

### Period Filter Empty

**Solution:**
1. Ensure property is selected first
2. Create financial periods if none exist
3. Check that periods are associated with the property

### Start Reconciliation Button Disabled

**Solution:**
1. Select both property and period
2. Verify periods are available
3. Check that data exists for the period

### Health Score Not Calculating

**Solution:**
1. Ensure reconciliation has been run
2. Verify matches exist
3. Check health score config exists for your persona

---

## 📚 Additional Resources

### Documentation
- **Final Summary:** `FORENSIC_RECONCILIATION_FINAL_SUMMARY.md`
- **Implementation Guide:** `FORENSIC_RECONCILIATION_ELITE_COMPLETE.md`
- **Technical Details:** `FORENSIC_RECONCILIATION_ELITE_IMPLEMENTATION.md`
- **Testing Guide:** `TESTING_GUIDE.md`
- **Quick Reference:** `QUICK_REFERENCE.md`

### API Documentation
- All endpoints are documented in the API router
- Use Swagger UI (if available): `http://localhost:8000/docs`

### Support
- Check troubleshooting sections in documentation
- Review error messages for specific guidance
- Check system logs: `docker compose logs backend`

---

## ✅ Best Practices

### 1. Regular Reconciliation
- Run reconciliation monthly for each property
- Review matches promptly
- Resolve discrepancies before period close

### 2. Materiality Configuration
- Set appropriate thresholds per property
- Adjust for property size and type
- Review and update periodically

### 3. Exception Review
- Start with Critical and High severity
- Use bulk operations for similar exceptions
- Document resolution notes

### 4. Health Score Monitoring
- Monitor health score trends
- Address blocked close rules promptly
- Review volatility indicators

### 5. Explainability Usage
- Use "Why Flagged" to understand issues
- Follow "What Would Resolve" suggestions
- Review "What Changed" for trends

---

## 🎓 Training Tips

### For New Users
1. Start with a test property/period
2. Review matches in Cockpit view
3. Use explainability features to learn
4. Practice with bulk operations

### For Auditors
1. Focus on approval rates
2. Review tier classifications
3. Use explainability for documentation
4. Monitor health score trends

### For Controllers
1. Monitor blocked close rules
2. Review materiality thresholds
3. Ensure compliance requirements met
4. Complete close checklist

---

## 🚀 Next Steps

1. **Explore the Cockpit:** Familiarize yourself with the three-panel layout
2. **Review Matches:** Start with a property that has data
3. **Test Features:** Try approve/reject, bulk operations, explainability
4. **Configure Settings:** Set up materiality thresholds and health score configs
5. **Monitor Health:** Track health scores over time

---

**Welcome to Forensic Reconciliation Elite System!** 🎉

For questions or issues, refer to the documentation or check the troubleshooting guide.

