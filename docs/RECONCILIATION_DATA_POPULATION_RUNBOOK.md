# Reconciliation Rules – Data Population Runbook

**Date**: January 29, 2026  
**Purpose**: Ensure AUDIT-51, AUDIT-52, TREND-3, and ANALYTICS-4–33 run with real data (no SKIP/INFO due to missing data).  
**Reference**: `docs/RECONCILIATION_RULES_FULL_IMPLEMENTATION_PLAN.md` Phase 2

---

## 1. Overview

Reconciliation rules **AUDIT-51** (Budget vs actual), **AUDIT-52** (Forecast vs actual), **TREND-3** (Variance analysis), and **ANALYTICS-4–33** (metrics) require populated data to return PASS or meaningful WARNING instead of SKIP or INFO. This runbook documents how to populate:

1. **Budget and forecast data** – so AUDIT-51, AUDIT-52, and TREND-3 have approved budget/forecast rows.
2. **Financial metrics** – so ANALYTICS-4–33 and covenant rules read real values from `financial_metrics`.

---

## 2. Financial Metrics Population

Rules that use metrics (ANALYTICS-4–33, covenant rules) read from the `financial_metrics` table. Metrics are computed from balance sheet, income statement, cash flow, and rent roll.

### 2.1 When to Recalculate

- After extraction or period close.
- After manual data corrections or bulk imports that affect BS/IS/CF/rent roll.

### 2.2 API: Recalculate Metrics

**Endpoint**:  
`POST /api/v1/metrics/{property_code}/{year}/{month}/recalculate`

**Path parameters**:
- `property_code` – Property code (e.g. `ESP-001`)
- `year` – Financial year (e.g. 2025)
- `month` – Financial month (1–12)

**Example** (curl):
```bash
curl -X POST "https://<host>/api/v1/metrics/ESP-001/2025/1/recalculate" \
  -H "Authorization: Bearer <token>"
```

**Response**: Success, `metrics_calculated` count, cache invalidated.

**Service**: `MetricsService(db).calculate_all_metrics(property_id, period_id)` – computes from BS/IS/CF/rent roll and upserts into `financial_metrics`.

### 2.3 UI “Recalculate metrics”

**Location**: Financials → **Statements** tab (header next to Export). A **"Recalculate metrics"** button calls the recalculate endpoint for the selected property and period, then refreshes financial data. Use it after extraction or period close so ANALYTICS-4–33 and covenant rules read real values.

---

## 3. Budget and Forecast Entry

AUDIT-51, AUDIT-52, and TREND-3 require **approved** budget and forecast rows for the property and period. Budget/forecast are stored in `budgets` and `forecasts`; rules filter by `status = 'approved'`.

### 3.1 Bulk Import (Primary Path)

**Budget import**  
- **Endpoint**: `POST /api/v1/bulk-import/budgets`  
- **Form fields**: `file` (CSV/Excel), `property_id`, `financial_period_id`, `budget_name`, `budget_year`, `created_by`  
- **Required columns**: `account_code`, `account_name`, `budgeted_amount`  
- **Optional columns**: `account_category`, `tolerance_percentage`, `tolerance_amount`, `notes`  
- **Note**: Import creates rows with `status = 'DRAFT'`. To be used by AUDIT-51/TREND-3, set `status = 'approved'` (e.g. via DB update or future approve API).

**Forecast import**  
- **Endpoint**: `POST /api/v1/bulk-import/forecasts`  
- **Form fields**: `file` (CSV/Excel), `property_id`, `financial_period_id`, `forecast_name`, `forecast_year`, `forecast_type`, `created_by`  
- **Forecast types**: `original`, `reforecast`, `rolling`  
- **Note**: Same as budget – ensure rows are `status = 'approved'` for AUDIT-52.

**Example** (curl, budget):
```bash
curl -X POST "https://<host>/api/v1/bulk-import/budgets" \
  -H "Authorization: Bearer <token>" \
  -F "file=@budget_2025_01.csv" \
  -F "property_id=1" \
  -F "financial_period_id=10" \
  -F "budget_name=2025 Annual Budget" \
  -F "budget_year=2025" \
  -F "created_by=1"
```

### 3.2 Approving Budgets/Forecasts

Rules only consider rows with `status = 'approved'`. After bulk import:

- **Option A (API)** – single record:
  - **Budget**: `PUT /api/v1/variance-analysis/budgets/{budget_id}/approve` (optional query: `approved_by=user_id`).
  - **Forecast**: `PUT /api/v1/variance-analysis/forecasts/{forecast_id}/approve`.
  - Only DRAFT or REVISED rows can be approved; returns 200 with `status: "APPROVED"`.
- **Option A2 (API)** – by property/period (after bulk import):
  - **Budgets**: `POST /api/v1/variance-analysis/budgets/approve-by-period` with body `{ "property_id": 1, "financial_period_id": 10, "approved_by": 1 }`. Approves all DRAFT/REVISED budgets for that property/period; returns `approved_count` and `budget_ids`.
  - **Forecasts**: `POST /api/v1/variance-analysis/forecasts/approve-by-period` with body `{ "property_id": 1, "financial_period_id": 10 }`. Approves all DRAFT/REVISED forecasts for that property/period; returns `approved_count` and `forecast_ids`.
- **Option B (DB)**: Update in DB, e.g.  
  `UPDATE budgets SET status = 'approved' WHERE property_id = ? AND financial_period_id = ?;`  
  (and similarly for `forecasts`).

**UI**: Financials → **Variance** tab:
- **Reconciliation data status** card shows checklist (metrics calculated, approved budget count, approved forecast count) and actions: Recalculate metrics, Import budget/forecast (link to Bulk import), Approve budgets, Approve forecasts.
- **Budget & forecast entry** card: link to Bulk import; **View budget lines** / **View forecast lines** load line items for the property/period; inline edit (change amount and blur to save) for DRAFT/REVISED lines only (PATCH `/variance-analysis/budgets/{id}` and `/forecasts/{id}`).
- **Approve budgets** and **Approve forecasts** buttons call the approve-by-period API for the selected property and period (real period only; simulated periods are disabled).

### 3.3 Data status and budget/forecast lines

- **GET** `/api/v1/variance-analysis/properties/{property_id}/periods/{period_id}/data-status` – returns `has_metrics`, `approved_budget_count`, `draft_budget_count`, `approved_forecast_count`, `draft_forecast_count` for the reconciliation data checklist.
- **GET** `/api/v1/variance-analysis/properties/{property_id}/periods/{period_id}/budgets` – list budget line items (id, account_code, account_name, budgeted_amount, status).
- **GET** `/api/v1/variance-analysis/properties/{property_id}/periods/{period_id}/forecasts` – list forecast line items (id, account_code, account_name, forecasted_amount, status).
- **PATCH** `/api/v1/variance-analysis/budgets/{budget_id}` – body `{ "budgeted_amount": number }`; only DRAFT/REVISED budgets can be updated.
- **PATCH** `/api/v1/variance-analysis/forecasts/{forecast_id}` – body `{ "forecasted_amount": number }`; only DRAFT/REVISED forecasts can be updated.

### 3.4 API tests (data-status, list, PATCH)

Tests for data-status, list budgets/forecasts, and PATCH budget/forecast live in `backend/tests/test_variance_analysis_approve.py` (classes `TestDataStatus`, `TestListBudgetsForecasts`, `TestPatchBudgetForecast`). They run only when `slowapi` is installed; otherwise the module is skipped. Run:

```bash
cd backend && python -m pytest tests/test_variance_analysis_approve.py -v -o addopts=
```

### 3.5 Regression tests (key rules)

Unit regression tests ensure that key reconciliation rules run and produce a result (no crash, no unexpected SKIP when dummy data is present). Run:

```bash
cd backend && python -m pytest tests/services/test_reconciliation_rules_mortgage_wc.py -v -o addopts=
```

In particular, `test_audit_49_50_fa_mort_4_produce_result` asserts that **AUDIT-49** (year-end validation), **AUDIT-50** (year-over-year comparison), and **FA-MORT-4** (escrow documentation link) each append exactly one result with an expected status (PASS/WARNING/INFO).

### 3.6 Variance Analysis Endpoints (Read-Only for Rules)

- **GET** `/api/v1/variance-analysis/properties/{property_id}/periods/{period_id}/budget` – get budget variance analysis.  
- **GET** `/api/v1/variance-analysis/properties/{property_id}/periods/{period_id}/forecast` – get forecast variance analysis.  
- **POST** `/api/v1/variance-analysis/budget` and **POST** `/api/v1/variance-analysis/forecast` – run variance analysis (compare actual to budget/forecast); they do **not** create budget/forecast rows.

---

## 4. Checklist for Maximum Rule Effectiveness

1. **After extraction or period close**  
   - Call `POST /api/v1/metrics/{property_code}/{year}/{month}/recalculate` for each property/period so `financial_metrics` is populated.

2. **For budget vs actual and TREND-3**  
   - Import budgets via `POST /api/v1/bulk-import/budgets` (CSV/Excel).  
   - Approve for the target property/period: `POST /api/v1/variance-analysis/budgets/approve-by-period` with `{ "property_id", "financial_period_id", "approved_by" }`, or approve individual budgets via `PUT .../budgets/{id}/approve`.

3. **For forecast vs actual**  
   - Import forecasts via `POST /api/v1/bulk-import/forecasts`.  
   - Approve for the target property/period: `POST /api/v1/variance-analysis/forecasts/approve-by-period` with `{ "property_id", "financial_period_id" }`, or approve individual forecasts via `PUT .../forecasts/{id}/approve`.

4. **Re-run reconciliation**  
   - Execute the reconciliation rule engine for the same property/period. AUDIT-51, AUDIT-52, TREND-3, and analytics rules should then return PASS or meaningful WARNING when data is present, instead of SKIP/INFO.

---

## 5. Reconciliation Rule Config (Optional)

Rule thresholds and options are stored in `system_config`. To seed or update them (including AUDIT-49, AUDIT-50, AUDIT-48, COVENANT-6, BENCHMARK, RRBS-1, FA-CASH-4, FA-MORT-4):

**Run the seed script** (after migrations):

```bash
# With Docker Postgres
docker exec -i reims-postgres psql -U reims -d reims < backend/scripts/seed_reconciliation_config.sql

# Or with local psql
psql -U <user> -d <database> -f backend/scripts/seed_reconciliation_config.sql
```

**Keys added for Phase 1 (AUDIT-49/50):**

- `audit49_earnings_tolerance_pct` (default 1.0) – year-end validation tolerance %
- `audit50_income_decrease_pct` (default 10) – YoY income decrease % to trigger WARNING
- `audit50_noi_decrease_pct` (default 10)
- `audit50_net_income_decrease_pct` (default 10)
- `audit50_occupancy_decrease_pp` (default 5) – YoY occupancy decrease (percentage points)

If keys are missing, rules use these defaults; seeding is optional but recommended for tuning.

---

## 6. Regression Test (Optional)

To verify that key rules run with data:

1. Seed a property/period with balance sheet, income statement, cash flow, and rent roll.  
2. Call recalculate metrics for that property/period.  
3. Seed approved budget (and optionally forecast) for the same property/period.  
4. Run reconciliation for that property/period.  
5. Assert: AUDIT-51 and TREND-3 do not SKIP (when budget exists); ANALYTICS-4 and ANALYTICS-5 do not return INFO due to missing metrics (when metrics are populated).

---

## 7. Where to view variance alerts and covenant history (UI)

- **Financial Integrity Hub** (`#forensic-reconciliation`, Operations): **Overview** tab shows **Covenant Compliance** (current period), **Covenant History** (table by period; “View in Covenant Compliance” opens the Covenant Compliance dashboard), and **Variance Alerts** (AUDIT-48; “View all” opens the Risk page).
- **Covenant Compliance dashboard** (`#covenant-compliance`, Risk): Full covenant DSCR/LTV and related tests for a selected property/period.
- **Risk page**: Committee alerts including variance breach (AUDIT-48) and DSCR breach; list and filter by type/status.

New variance breach alerts trigger email (if enabled) and in-app notification via `AlertNotificationService.notify_alert_created`.

---

**Document version**: 1.2  
**Last updated**: January 29, 2026
