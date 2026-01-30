# Reconciliation Rules – Quick Reference

**Last updated**: January 29, 2026  

Single entry point for reconciliation rules implementation, data population, and UI.

---

## Recent changes (Jan 2026)

- **Financial Integrity Hub – Overview tab**: Covenant Compliance (current period), Covenant History (table by period; "View in Covenant Compliance" → Covenant Compliance dashboard; tip with **Recalculate metrics** link → Financials → Statements), Variance Alerts (AUDIT-48; "View all" → Risk). Critical Issues "View All" → Exceptions tab.
- **Covenant**: `covenant_compliance_history` table and CRUD API (`/api/v1/covenant-compliance/history`, `/thresholds`); engine records compliance when reconciliation runs.
- **Variance alerts**: New variance breach alerts trigger `AlertNotificationService.notify_alert_created` (email if enabled, in-app). `GET /api/v1/variance-analysis/variance-alerts`.
- **Navigation**: `navigateToPage` supports optional `hash` (e.g. open Financials → Statements from hub tip). Hash `covenant-compliance` sets current page to Risk.

---

## Key documents

| Document | Purpose |
|----------|--------|
| [RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md](../RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md) | Rule-by-rule status and coverage matrix (root). |
| [RECONCILIATION_RULES_FULL_IMPLEMENTATION_PLAN.md](RECONCILIATION_RULES_FULL_IMPLEMENTATION_PLAN.md) | Gap list, phased plan, Phase 1/2/3 deliverables; §6 Hub Overview tab. |
| [RECONCILIATION_DATA_POPULATION_RUNBOOK.md](RECONCILIATION_DATA_POPULATION_RUNBOOK.md) | How to populate metrics, budget, forecast; APIs and UI; §7 where to view variance alerts and covenant history. |
| [RULES_COVERAGE_MATRIX.md](RULES_COVERAGE_MATRIX.md) | Rule ID → status, file/method, notes (single table); Hub Overview tab. |
| [RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md](RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md) | Codebase vs analysis alignment; Phase 2/3 triggers. |
| [RECONCILIATION_GAPS_STATUS.md](RECONCILIATION_GAPS_STATUS.md) | Gap implementation checklist: enhancement, data/workflow, covenant/variance, optional. |

---

## Phase 1 (done): Rule enhancements

- **AUDIT-49**: Year-end validation – config `audit49_earnings_tolerance_pct`; optional retained earnings roll; checklist in details.
- **AUDIT-50**: YoY comparison – config `audit50_income_decrease_pct`, `audit50_noi_decrease_pct`, `audit50_net_income_decrease_pct`, `audit50_occupancy_decrease_pp`.
- **Seed config**: `backend/scripts/seed_reconciliation_config.sql` (run after migrations). See runbook §5.

---

## Phase 2: Data population & UI

### APIs

- **Recalculate metrics**: `POST /api/v1/metrics/{property_code}/{year}/{month}/recalculate`
- **Budget import**: `POST /api/v1/bulk-import/budgets` (CSV/Excel)
- **Forecast import**: `POST /api/v1/bulk-import/forecasts` (CSV/Excel)
- **Approve budget**: `PUT /api/v1/variance-analysis/budgets/{id}/approve` or `POST .../budgets/approve-by-period` (body: `property_id`, `financial_period_id`, optional `approved_by`)
- **Approve forecast**: `PUT /api/v1/variance-analysis/forecasts/{id}/approve` or `POST .../forecasts/approve-by-period`

### UI (Financials page)

| Location | Action | Purpose |
|----------|--------|--------|
| **Statements** tab (header) | **Recalculate metrics** | Refresh KPIs for selected property/period so ANALYTICS-4–33 and covenant rules use real values. |
| **Statements** tab (left rail) | **Escrow documentation (FA-MORT-4)** | List, add, and remove escrow document links (property tax, insurance, reserves, general) for the selected property/period. |
| **Variance** tab | **Reconciliation data status** | Checklist: metrics calculated, approved budget count, approved forecast count; actions: Recalculate metrics, Import budget/forecast, Approve budgets, Approve forecasts. |
| **Variance** tab | **Budget & forecast entry** | Link to Bulk import; View budget lines / View forecast lines with inline edit (amount, blur to save) for DRAFT/REVISED only. |
| **Variance** tab (header) | **Approve budgets** | Approve all DRAFT budgets for selected property/period (AUDIT-51, TREND-3). |
| **Variance** tab (header) | **Approve forecasts** | Approve all DRAFT forecasts for selected property/period (AUDIT-52). |

### UI (Financial Integrity Hub – Overview tab)

| Section | Purpose |
|---------|--------|
| **Covenant Compliance** (card) | Current period: X/Y compliant by covenant type (DSCR, LTV, etc.); data from reconciliation results. |
| **Covenant History** (table) | All periods for selected property: Period, Type, Value, Threshold, Status (Pass/Fail). Uses `GET /api/v1/covenant-compliance/history?property_id=` (no period_id). "View in Covenant Compliance" opens Covenant Compliance dashboard; tip includes **Recalculate metrics** link to Financials → Statements. |
| **Variance Alerts** (card) | AUDIT-48 variance breach alerts for selected property/period. Uses `GET /api/v1/variance-analysis/variance-alerts`. "View all" opens Risk page. |

---

## Rule coverage summary

- **Full**: FA-PAL, FA-CASH, FA-FRAUD, FA-WC, FA-MORT (incl. FA-MORT-4), RRBS, AUDIT-1–55, DQ-1–33, ANALYTICS-1–33, COVENANT-1–6, BENCHMARK-1–4, TREND-1–3, STRESS-1–5.
- **Enhanced**: AUDIT-49, AUDIT-50 (configurable thresholds).
- **Data-dependent**: AUDIT-51, AUDIT-52, TREND-3 (need approved budget/forecast); ANALYTICS-4–33 (need populated `financial_metrics`).

See [RULES_COVERAGE_MATRIX.md](RULES_COVERAGE_MATRIX.md) for the full table.
