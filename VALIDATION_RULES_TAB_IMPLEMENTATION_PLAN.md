# Validation Rules Tab - Implementation Plan

## Overview
The Validation Rules tab in Data Control Center should provide a comprehensive dashboard for monitoring, analyzing, and managing validation rule performance across all document uploads.

## Current State
- ✅ Backend API exists: `/api/v1/validations/rules`
- ✅ Validation results are stored in database
- ✅ Validation rules are seeded (8+ rules)
- ❌ Frontend table is empty (not fetching data)
- ❌ No statistics or analytics
- ❌ No filtering or search capabilities

---

## Phase 1: Core Functionality (Essential)

### 1.1 Rule Statistics Dashboard
**Purpose:** Show high-level overview of validation rule performance

**Components:**
- **Summary Cards:**
  - Total Rules (active/inactive)
  - Rules by Severity (Error/Warning/Info counts)
  - Overall Pass Rate (across all validations)
  - Failed Validations Today/This Week/This Month

- **Rule Performance Table:**
  - Rule Name
  - Document Type (Balance Sheet, Income Statement, etc.)
  - Rule Type (balance_check, range_check, required_field)
  - Severity (Error, Warning, Info) with color coding
  - Total Tests (how many times rule was executed)
  - Passed Count
  - Failed Count
  - Pass Rate % (with progress bar)
  - Status (Active/Inactive) with toggle
  - Last Run Date

**API Endpoint:** `GET /api/v1/validations/rules` (already exists)
**Additional Endpoint Needed:** `GET /api/v1/validations/rules/statistics` (aggregate pass/fail counts)

### 1.2 Rule Details Modal
**Purpose:** View detailed information about a specific rule

**Content:**
- Rule Name & Description
- Document Type & Rule Type
- Rule Formula (e.g., "total_assets = total_liabilities + total_equity")
- Severity Level
- Tolerance (if applicable)
- Recent Validation Results (last 10-20)
  - Upload ID, Property Code, Date
  - Passed/Failed status
  - Expected vs Actual values
  - Difference & Percentage
  - Error Message (if failed)

**API Endpoint:** `GET /api/v1/validations/rules/{rule_id}/results`

### 1.3 Filtering & Search
**Purpose:** Find specific rules quickly

**Filters:**
- Document Type (Balance Sheet, Income Statement, Cash Flow, Rent Roll, All)
- Severity (Error, Warning, Info, All)
- Status (Active, Inactive, All)
- Pass Rate Range (slider: 0-100%)
- Search by Rule Name

---

## Phase 2: Analytics & Insights (Enhanced)

### 2.1 Rule Performance Charts
**Purpose:** Visualize validation trends

**Charts:**
1. **Pass Rate Over Time** (Line Chart)
   - X-axis: Date (last 30 days)
   - Y-axis: Pass Rate %
   - Multiple lines for different rules or document types

2. **Failure Distribution** (Pie/Donut Chart)
   - Breakdown by Severity (Error/Warning/Info)
   - Breakdown by Document Type
   - Breakdown by Rule Type

3. **Top Failing Rules** (Bar Chart)
   - Rules with highest failure rates
   - Sortable by failure count or failure rate

4. **Validation Volume** (Area Chart)
   - Number of validations run per day
   - Stacked by document type

**Library:** Chart.js or Recharts (already used in TaskCharts)

### 2.2 Rule Health Score
**Purpose:** Quick indicator of rule reliability

**Calculation:**
- Health Score = (Pass Rate * 0.7) + (Recent Activity * 0.3)
- Color coding:
  - Green: 90-100% (Healthy)
  - Yellow: 70-89% (Needs Attention)
  - Red: <70% (Critical)

**Display:**
- Badge next to each rule in table
- Tooltip showing breakdown

### 2.3 Trend Analysis
**Purpose:** Identify improving or deteriorating rules

**Indicators:**
- ↑ Improving (pass rate increasing)
- ↓ Declining (pass rate decreasing)
- → Stable (pass rate consistent)
- ⚠️ New Rule (insufficient data)

**Time Periods:**
- Last 7 days vs Last 30 days
- Last month vs Previous month

---

## Phase 3: Management Actions (Advanced)

### 3.1 Rule Toggle (Enable/Disable)
**Purpose:** Temporarily disable problematic rules

**Functionality:**
- Toggle switch in table row
- Confirmation dialog for disabling critical rules
- Visual indicator (grayed out) for disabled rules
- Bulk enable/disable selected rules

**API Endpoint:** `PATCH /api/v1/validations/rules/{rule_id}/toggle`

### 3.2 Rule Testing
**Purpose:** Test rules against specific uploads

**Functionality:**
- "Test Rule" button in details modal
- Select upload(s) to test against
- Run validation and show results
- Compare with previous results

**API Endpoint:** `POST /api/v1/validations/rules/{rule_id}/test`

### 3.3 Export Functionality
**Purpose:** Export rule statistics for reporting

**Formats:**
- CSV export (rule statistics table)
- PDF report (comprehensive rule performance report)
- Excel export (with charts)

**Content:**
- Rule list with statistics
- Performance charts
- Recent failures
- Recommendations

---

## Phase 4: Integration Features (Best-in-Class)

### 4.1 Link to Failed Validations
**Purpose:** Quick navigation to review queue

**Functionality:**
- Click on "Failed Count" → Navigate to Review Queue filtered by rule
- "View Failed Validations" button in rule details modal
- Show affected properties and documents

### 4.2 Rule Recommendations
**Purpose:** AI-powered suggestions for rule improvements

**Suggestions:**
- Rules with high failure rates → Suggest tolerance adjustments
- Rules never failing → Suggest making more strict
- Missing validations → Suggest new rules based on common errors

### 4.3 Rule Templates
**Purpose:** Quick creation of new rules

**Templates:**
- Balance Sheet Equation
- Income Statement Totals
- Cash Flow Reconciliation
- Range Checks
- Required Field Checks

**Functionality:**
- "Create from Template" button
- Pre-filled form with template values
- Customize before saving

---

## Implementation Priority

### Must Have (Phase 1):
1. ✅ Fetch and display rules from API
2. ✅ Show rule statistics (pass/fail counts)
3. ✅ Basic filtering (document type, severity, status)
4. ✅ Rule details modal
5. ✅ Link to "Manage Rules" page

### Should Have (Phase 2):
1. Performance charts
2. Health scores
3. Trend indicators
4. Search functionality

### Nice to Have (Phase 3 & 4):
1. Rule toggling
2. Export functionality
3. Rule testing
4. Recommendations

---

## API Endpoints Needed

### Existing:
- ✅ `GET /api/v1/validations/rules` - List all rules
- ✅ `GET /api/v1/validations/{upload_id}` - Get validation results for upload

### New Endpoints Needed:
1. `GET /api/v1/validations/rules/statistics`
   - Returns aggregated statistics for all rules
   - Includes: total tests, passed, failed, pass rate per rule
   - Optional filters: document_type, severity, date_range

2. `GET /api/v1/validations/rules/{rule_id}/results`
   - Returns recent validation results for a specific rule
   - Pagination support
   - Optional filters: date_range, passed/failed

3. `GET /api/v1/validations/rules/{rule_id}/trends`
   - Returns pass rate trends over time
   - Time periods: 7 days, 30 days, 90 days

4. `PATCH /api/v1/validations/rules/{rule_id}/toggle`
   - Enable/disable a rule
   - Body: `{ "is_active": true/false }`

5. `POST /api/v1/validations/rules/{rule_id}/test`
   - Test rule against specific upload(s)
   - Body: `{ "upload_ids": [1, 2, 3] }`

---

## UI/UX Considerations

### Table Features:
- Sortable columns (click header to sort)
- Pagination (if many rules)
- Row selection (for bulk actions)
- Expandable rows (show recent results inline)

### Visual Indicators:
- Color-coded severity badges
- Progress bars for pass rates
- Trend arrows (↑↓→)
- Health score badges

### Responsive Design:
- Mobile-friendly table (horizontal scroll)
- Collapsible filters on mobile
- Stacked cards on small screens

### Loading States:
- Skeleton loaders while fetching
- Progressive loading (show rules as they load)
- Error states with retry button

---

## Data Flow

```
User opens Validation Rules tab
    ↓
Fetch rules from API: GET /api/v1/validations/rules
    ↓
Fetch statistics: GET /api/v1/validations/rules/statistics
    ↓
Display in table with filters
    ↓
User clicks rule → Show details modal
    ↓
Fetch rule results: GET /api/v1/validations/rules/{id}/results
    ↓
Display detailed information
```

---

## Example Implementation Structure

```typescript
// State
const [rules, setRules] = useState<ValidationRule[]>([]);
const [statistics, setStatistics] = useState<RuleStatistics>({});
const [filters, setFilters] = useState<RuleFilters>({
  documentType: 'all',
  severity: 'all',
  status: 'active',
  search: ''
});
const [selectedRule, setSelectedRule] = useState<ValidationRule | null>(null);

// API Calls
const loadRules = async () => {
  const response = await fetch(`${API_BASE_URL}/validations/rules?...`);
  const data = await response.json();
  setRules(data);
};

const loadStatistics = async () => {
  const response = await fetch(`${API_BASE_URL}/validations/rules/statistics`);
  const data = await response.json();
  setStatistics(data);
};
```

---

## Success Metrics

- ✅ All validation rules visible in table
- ✅ Accurate pass/fail statistics displayed
- ✅ Users can filter and search rules
- ✅ Rule details accessible via modal
- ✅ Performance trends visible in charts
- ✅ Rules can be enabled/disabled
- ✅ Export functionality works

---

## Next Steps

1. **Create API endpoint for statistics** (`/api/v1/validations/rules/statistics`)
2. **Update frontend to fetch and display rules**
3. **Implement filtering and search**
4. **Add rule details modal**
5. **Create performance charts**
6. **Add rule management actions**

