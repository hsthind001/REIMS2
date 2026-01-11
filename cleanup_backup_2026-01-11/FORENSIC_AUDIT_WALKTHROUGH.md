# Forensic Audit Framework - Quick Demo & Walkthrough

## Overview

The **Big 5 Forensic Audit Framework** is a comprehensive real estate financial analysis system that performs automated auditing across five critical dimensions:

1. **Fraud Detection** - Benford's Law, duplicate payments, round numbers
2. **Covenant Compliance** - DSCR, LTV, Interest Coverage monitoring
3. **Reconciliation Results** - 9 cross-document reconciliations
4. **Tenant Risk** - Concentration, rollover, occupancy analysis
5. **Collections Quality** - DSO, A/R aging, cash conversion

## Access the Framework

### Step 1: Navigate to the CEO Dashboard

1. Log in to REIMS2
2. Go to **Data Control Center** (main navigation)
3. Click the **🛡️ Forensic Audit** button (blue gradient button in the top section)
4. You'll be taken to the **CEO Forensic Audit Dashboard**

### Step 2: Select Property and Period

On the CEO Dashboard (and all sub-dashboards):

1. **Select Property** - Choose from the dropdown (top-right)
2. **Select Financial Period** - Choose the period to analyze
3. The dashboard will automatically load audit results

If you see an error like "Failed to load audit results. Run audit first":
- You need to execute the forensic audit for this property/period first
- See "Running the Audit" section below

## Running the Audit

### Backend API Endpoint

The audit is executed via the backend API:

```bash
POST /api/v1/forensic-audit/run-audit/{property_id}/{period_id}
```

### Using the API Directly

```bash
# Example: Run audit for property 1, period 5
curl -X POST "http://localhost:8000/api/v1/forensic-audit/run-audit/1/5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### What the Audit Does

When you run the audit, the backend:

1. **Loads financial data** from 4 source documents:
   - Operating Statement (actuals)
   - Budget
   - Rent Roll
   - T12 (trailing 12 months)

2. **Executes 25+ audit tests** including:
   - 9 cross-document reconciliations
   - 4 fraud detection tests
   - 5 covenant compliance checks
   - 4 tenant risk analyses
   - 5 collections quality metrics

3. **Generates audit results** with:
   - Overall health score (0-100)
   - Traffic light status (GREEN/YELLOW/RED)
   - Detailed findings and recommendations
   - Audit opinion (UNQUALIFIED/QUALIFIED/ADVERSE)

4. **Stores results** in the database for fast retrieval

## Dashboard Walkthrough

### 1. CEO Forensic Audit Dashboard

**Purpose**: Executive summary with overall health and key metrics

**What you'll see**:
- **Overall Health Score Gauge** (0-100)
  - 90-100: Excellent (GREEN)
  - 70-89: Good (YELLOW)
  - <70: Poor (RED)

- **Audit Opinion Badge**
  - UNQUALIFIED: Clean audit, no material issues
  - QUALIFIED: Some concerns, review sub-dashboards
  - ADVERSE: Significant issues requiring immediate attention

- **5 Quick Links** to detailed dashboards:
  - Fraud Detection
  - Covenant Compliance
  - Reconciliation Results
  - Tenant Risk
  - Collections Quality

- **Key Findings Section**
  - Top 3-5 most important issues
  - Color-coded by severity (HIGH/MODERATE/LOW)
  - Quick summary of what was found

**What to do**:
1. Check the overall health score
2. Review the audit opinion
3. Read the key findings
4. Click on any dashboard link to drill down

---

### 2. Fraud Detection Dashboard

**Purpose**: Detect anomalies in financial data using statistical tests

**Tests Performed**:

#### Benford's Law Analysis
- **What it checks**: First digit distribution of transaction amounts
- **Why it matters**: Fraudulent data often violates Benford's Law
- **What you'll see**:
  - Chi-square test result
  - Expected vs. Actual distribution chart
  - GREEN: Follows natural distribution
  - RED: Significant deviation (investigate further)

#### Round Number Detection
- **What it checks**: % of transactions with round amounts ($100, $500, etc.)
- **Why it matters**: Too many round numbers suggest manual manipulation
- **What you'll see**:
  - Percentage of round numbers
  - GREEN: <5%, YELLOW: 5-10%, RED: >10%

#### Duplicate Payment Detection
- **What it checks**: Same vendor + same amount on same/nearby dates
- **Why it matters**: Indicates potential duplicate processing or fraud
- **What you'll see**:
  - Count of suspicious duplicates
  - Table with vendor, amount, dates
  - Investigate each one

#### Cash Conversion Ratio
- **What it checks**: Cash collected / Revenue recognized
- **Why it matters**: Low ratio suggests collection issues
- **What you'll see**:
  - Ratio percentage
  - GREEN: >95%, YELLOW: 85-95%, RED: <85%

**What to do**:
1. Check overall fraud risk status (top card)
2. Review Benford's Law chart - look for major deviations
3. Scan duplicate payments table - investigate any high-value duplicates
4. Check cash conversion - if low, go to Collections Quality Dashboard

---

### 3. Covenant Compliance Dashboard

**Purpose**: Monitor lender covenant compliance and cushion

**Key Metrics**:

#### DSCR (Debt Service Coverage Ratio)
- **Formula**: NOI / Debt Service
- **Covenant**: Typically ≥1.25x
- **What you'll see**:
  - Current DSCR value (e.g., 1.32x)
  - Covenant threshold line on gauge
  - Cushion amount (how much above covenant)
  - Trend vs. previous period
  - Lender notification flag (if close to breach)

#### LTV (Loan-to-Value Ratio)
- **Formula**: Loan Balance / Property Value
- **Covenant**: Typically ≤75%
- **What you'll see**:
  - Current LTV percentage
  - Lower is better for this metric
  - GREEN: Well below covenant
  - RED: At or above covenant

#### Interest Coverage Ratio
- **Formula**: EBITDA / Interest Expense
- **What you'll see**:
  - How many times interest is covered
  - Higher is better

#### Liquidity Ratios
- **Current Ratio**: Current Assets / Current Liabilities
- **Quick Ratio**: (Current Assets - Inventory) / Current Liabilities
- **Target**: Both >1.0

**What to do**:
1. Check overall covenant compliance status
2. Review DSCR gauge - ensure adequate cushion
3. Check "Lender Notification Required" flag
4. If any covenants are yellow/red, review recommendations
5. Look at trends - improving or deteriorating?

---

### 4. Reconciliation Results Dashboard

**Purpose**: Verify consistency across 4 financial documents

**9 Reconciliations Performed**:

1. **Total Revenue** (Operating Statement ↔ Budget)
2. **Total Expenses** (Operating Statement ↔ Budget)
3. **NOI** (Operating Statement ↔ Budget)
4. **Gross Rent** (Operating Statement ↔ Rent Roll)
5. **Occupancy %** (Operating Statement ↔ Rent Roll)
6. **Total Revenue** (Operating Statement ↔ T12)
7. **Total Expenses** (Operating Statement ↔ T12)
8. **NOI** (Operating Statement ↔ T12)
9. **Occupancy %** (Operating Statement ↔ T12)

**What you'll see**:

- **Summary Card**:
  - Total reconciliations: 9
  - Passed: X, Warnings: Y, Failed: Z
  - Pass rate percentage

- **Expandable Reconciliation Cards** (click to expand):
  - Rule code (e.g., REC-001)
  - Status badge (PASS/WARNING/FAIL)
  - Reconciliation type
  - Source → Target documents
  - Difference amount (highlighted if material)
  - When expanded:
    - Source value
    - Target value
    - Difference
    - Materiality threshold
    - Explanation of what's being compared
    - Recommendations if failed

**What to do**:
1. Check overall pass rate
2. Click on any FAIL or WARNING cards to expand
3. Review the difference amounts
4. Read the explanation and recommendations
5. Investigate source data if differences exceed materiality

---

### 5. Tenant Risk Dashboard

**Purpose**: Assess tenant concentration and lease rollover risk

**Key Sections**:

#### Tenant Concentration Risk
- **What it checks**: % of rent from top tenants
- **Why it matters**: High concentration = high risk if tenant leaves
- **What you'll see**:
  - Top 1 Tenant % (target: <20%)
  - Top 3 Tenants % (target: <50%)
  - Top 5 and Top 10 for monitoring
  - List of top tenants with monthly rent amounts
  - RED if top 1 >20% or top 3 >50%

#### Lease Rollover Risk
- **What it checks**: % of rent expiring in 12/24/36 months
- **Why it matters**: High near-term rollover requires proactive leasing
- **What you'll see**:
  - 12-month rollover (target: <25%)
  - 24-month rollover (target: <50%)
  - 36-month rollover (monitoring only)
  - RED if 12-mo >25%

#### Occupancy Metrics
- **Physical Occupancy**: % of space leased
- **Economic Occupancy**: % of potential rent being collected
- **What you'll see**:
  - Both percentages with progress bars
  - Occupied SF / Total SF

#### Credit Quality
- **What it checks**: % of tenants investment grade vs. non-investment grade
- **What you'll see**:
  - Investment grade %
  - Non-investment grade %
  - Total tenant count

#### Rent per SF Statistics
- **What you'll see**:
  - Average rent/SF
  - Median rent/SF
  - Min and max values
  - Standard deviation (consistency)

**What to do**:
1. Check overall tenant risk status
2. Review top tenant concentration - diversify if needed
3. Check 12-month rollover - start leasing efforts if high
4. Review credit quality - higher investment grade is better
5. Look at rent/SF stats - identify outliers

---

### 6. Collections Quality Dashboard

**Purpose**: Monitor revenue quality and cash collection efficiency

**Key Metrics**:

#### Revenue Quality Score
- **What it shows**: Composite 0-100 score
- **Based on**:
  - DSO
  - A/R aging distribution
  - Cash conversion
  - Collection rate
- **What you'll see**:
  - Circular gauge (0-100)
  - Total revenue
  - Collectible revenue (GREEN)
  - At-risk revenue (RED)
  - Collectible percentage

#### Days Sales Outstanding (DSO)
- **Formula**: (A/R / Revenue) × Days in Period
- **What it shows**: Average days to collect payment
- **What you'll see**:
  - Current DSO (e.g., 45 days)
  - Target DSO (typically 30-45 days)
  - Previous DSO with trend arrow
  - GREEN if ≤target, RED if >target

#### Cash Conversion Ratio
- **Formula**: (Cash Collected / Revenue Recognized) × 100
- **What you'll see**:
  - Revenue recognized
  - Cash collected
  - Conversion ratio %
  - Progress bar
  - GREEN: ≥95%, YELLOW: 85-95%, RED: <85%

#### A/R Aging Analysis
- **What it shows**: Distribution of outstanding receivables by age
- **Buckets**:
  - 0-30 days (current - GREEN)
  - 31-60 days (YELLOW)
  - 61-90 days (ORANGE)
  - 90+ days (overdue - RED)
- **What you'll see**:
  - Amount and % for each bucket
  - Visual stacked bar chart
  - Total A/R amount
  - Traffic light status for each bucket

#### Collections Efficiency
- **Collection Rate**: % collected on time
- **Write-Off Rate**: % of revenue written off
- **Recovery Rate**: % of overdue amounts recovered

**What to do**:
1. Check revenue quality score - aim for >80
2. Review DSO - compare to target and trend
3. Check cash conversion - investigate if <95%
4. Look at A/R aging - too much in 60+ days is concerning
5. Review write-off rate - should be <2%
6. Check recovery rate - higher is better

## Interpreting Results

### Traffic Light System

**🟢 GREEN**: Meets all standards
- No action required
- Continue monitoring

**🟡 YELLOW**: Some concerns
- Review details
- Monitor closely
- Consider preventive action

**🔴 RED**: Critical issues
- Immediate attention required
- Review recommendations
- Take corrective action

### Health Scores

**90-100**: Excellent
- All metrics strong
- Minimal risk

**70-89**: Good
- Most metrics acceptable
- Some areas for improvement

**50-69**: Fair
- Several areas of concern
- Action plan recommended

**<50**: Poor
- Significant issues
- Immediate intervention needed

### Audit Opinions

**UNQUALIFIED (Clean)**
- All tests passed
- No material misstatements
- High confidence in financials

**QUALIFIED**
- Some issues found
- Not material enough to reject
- Review specific findings

**ADVERSE**
- Material issues found
- Financials may be unreliable
- Comprehensive review needed

## Common Workflows

### Monthly Executive Review

1. Navigate to **CEO Dashboard**
2. Check overall health score and opinion
3. Review key findings
4. If anything is RED:
   - Click the relevant dashboard link
   - Review detailed metrics
   - Read recommendations
   - Take action

### Lender Reporting

1. Go to **Covenant Compliance Dashboard**
2. Check all covenant metrics
3. Document cushion amounts
4. If "Lender Notification Required" flag is set:
   - Prepare explanation
   - Contact lender proactively
   - Provide action plan

### Fraud Investigation

1. Go to **Fraud Detection Dashboard**
2. Review Benford's Law results
3. Check duplicate payments table
4. Export suspicious transactions
5. Investigate with accounting team

### Collections Management

1. Go to **Collections Quality Dashboard**
2. Check DSO and A/R aging
3. Identify tenants in 60+ day buckets
4. Prioritize collection efforts
5. Monitor cash conversion weekly

### Lease Management

1. Go to **Tenant Risk Dashboard**
2. Review 12-month rollover
3. Identify expiring leases
4. Start renewal negotiations early
5. Plan for potential vacancies

## Best Practices

### 1. Run Audits Regularly

- **Monthly**: After financials are closed
- **Pre-Lender Reporting**: Before quarterly/annual reports
- **Ad-hoc**: When investigating issues

### 2. Monitor Trends

- Compare current period to previous
- Look for deteriorating metrics
- Identify patterns early

### 3. Take Proactive Action

- Don't wait for metrics to turn RED
- Address YELLOW status items
- Implement recommendations

### 4. Document Findings

- Export audit results
- Keep notes on actions taken
- Track resolution progress

### 5. Use in Combination

- CEO Dashboard for overview
- Drill into specific areas as needed
- Cross-reference findings across dashboards

## Troubleshooting

### "Failed to load audit results"

**Cause**: Audit hasn't been run for this property/period

**Solution**: Execute the audit API endpoint first:
```bash
POST /api/v1/forensic-audit/run-audit/{property_id}/{period_id}
```

### Unexpected Values

**Possible causes**:
1. Source data quality issues
2. Missing transactions
3. Incorrect account codes
4. Budget not entered

**Solution**:
1. Review source documents
2. Check data upload process
3. Verify account code mapping
4. Re-run audit after corrections

### Slow Dashboard Loading

**Causes**:
1. Large dataset
2. First-time audit run
3. Server load

**Solution**:
1. Wait for audit to complete (can take 1-2 minutes for large properties)
2. Subsequent loads are fast (results are cached)
3. Use the Refresh button to reload data

## Technical Details

### Architecture

**Backend**:
- FastAPI REST API
- SQLAlchemy ORM
- Pydantic models
- PostgreSQL database

**Frontend**:
- React with TypeScript
- Tailwind CSS styling
- Lucide icons
- Hash-based routing

**API Endpoints**:
```
POST   /api/v1/forensic-audit/run-audit/{property_id}/{period_id}
GET    /api/v1/forensic-audit/{property_id}/{period_id}
GET    /api/v1/forensic-audit/fraud-detection/{property_id}/{period_id}
GET    /api/v1/forensic-audit/covenant-compliance/{property_id}/{period_id}
GET    /api/v1/forensic-audit/reconciliation/{property_id}/{period_id}
GET    /api/v1/forensic-audit/tenant-risk/{property_id}/{period_id}
GET    /api/v1/forensic-audit/collections-quality/{property_id}/{period_id}
```

### Data Flow

1. **User selects property/period** → Frontend makes API call
2. **Backend checks cache** → Returns if available
3. **If not cached** → Executes audit logic
4. **Loads source data** → Operating Statement, Budget, Rent Roll, T12
5. **Runs tests** → All 25+ audit procedures
6. **Calculates scores** → Health score, traffic lights
7. **Stores results** → Database
8. **Returns JSON** → Frontend renders dashboard

### Performance

- **First audit run**: 1-2 minutes (depending on data size)
- **Subsequent loads**: <1 second (cached results)
- **Dashboard switching**: Instant (client-side routing)
- **Data refresh**: Click Refresh button to re-run audit

## Support & Feedback

For issues or questions:
1. Check this walkthrough first
2. Review backend logs for API errors
3. Check browser console for frontend errors
4. Contact development team with specific error messages

---

## Quick Reference Card

| Dashboard | Primary Use | Key Metric | Red Flag |
|-----------|-------------|------------|----------|
| CEO Dashboard | Executive overview | Health Score | Score <70 |
| Fraud Detection | Anomaly detection | Benford's Law | Chi-square >20 |
| Covenant Compliance | Lender reporting | DSCR | DSCR <1.25x |
| Reconciliation | Data integrity | Pass Rate | Pass rate <90% |
| Tenant Risk | Lease management | 12-mo Rollover | Rollover >25% |
| Collections Quality | Cash management | DSO | DSO >45 days |

**Traffic Lights**: 🟢 GREEN = Good | 🟡 YELLOW = Caution | 🔴 RED = Action Required

**Audit Opinions**: UNQUALIFIED = Clean | QUALIFIED = Some Issues | ADVERSE = Major Problems

---

*Last Updated: 2025-12-28*
*REIMS2 Forensic Audit Framework v1.0*
