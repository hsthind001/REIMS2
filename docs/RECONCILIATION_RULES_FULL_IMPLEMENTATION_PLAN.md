# Reconciliation Rules – Full Implementation Plan

**Date**: January 29, 2026  
**Reference**: `RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md`, `docs/RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md`  
**Purpose**: Deep-dive analysis of rules not fully implemented per the analysis doc, and a phased plan to fully implement all rules.

---

## 1. Executive Summary

The **RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md** file contains some sections that still describe rules as "NOT IMPLEMENTED" or "PARTIALLY IMPLEMENTED" even though the codebase (and **docs/RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md**) shows many of these have since been implemented. This document:

1. **Reconciles** the analysis doc with the current codebase and identifies the **true remaining gaps**.
2. **Lists** every rule that is either (a) not fully implemented, (b) implemented but data-dependent (needs data population), or (c) implemented but could be enhanced.
3. **Proposes a phased plan** to fully implement or harden all rules so the system reaches 100% rule coverage with clear success criteria.

---

## 2. Analysis Doc vs Codebase – Rule-by-Rule Reconciliation

### 2.1 Rules the Analysis Says Are NOT/PARTIALLY Implemented but Are Implemented

| Analysis Doc Claim | Rule(s) | Actual State | Location |
|--------------------|---------|--------------|----------|
| FA-MORT-4 "PARTIALLY IMPLEMENTED" | Escrow documentation | **FULLY IMPLEMENTED** | `audit_rules_mixin.py`: `_rule_fa_mort_4_escrow_documentation_link()`; `EscrowDocumentLink` model; API `/documents/escrow-links` |
| ANALYTICS-6–10 "NOT IMPLEMENTED" | Economic occ, rollover, retention, WALT, growth | **IMPLEMENTED** | `analytics_rules_mixin.py`: `_rule_analytics_6_economic_occupancy` … `_rule_analytics_10_rent_roll_growth` |
| ANALYTICS-13, 14 "NOT IMPLEMENTED" | Interest coverage, Debt yield | **IMPLEMENTED** | `_rule_analytics_13_interest_coverage()`, `_rule_analytics_14_debt_yield()` |
| ANALYTICS-15–18 "NOT IMPLEMENTED" | Current ratio, CF coverage, days cash, AR days | **IMPLEMENTED** | `_rule_analytics_15_current_ratio` … `_rule_analytics_18_ar_days` |
| ANALYTICS-19–24 "NOT IMPLEMENTED" | ROA, ROE, per-SF, efficiency | **IMPLEMENTED** | `_rule_analytics_19_roa` … `_rule_analytics_24_management_efficiency` |
| ANALYTICS-25–33 "MOSTLY NOT IMPLEMENTED" | Risk metrics | **IMPLEMENTED** | `_rule_analytics_25_debt_to_equity` … `_rule_analytics_33_occupancy_volatility` |
| COVENANT-6 "STUB" | Reporting requirements | **FULLY IMPLEMENTED** | `_rule_covenant_6_reporting_requirements()` – checks `document_uploads` vs `covenant_reporting_deadline_days` |
| BENCHMARK-1–4 "NOT IMPLEMENTED" | Market comparison | **IMPLEMENTED** | `_rule_benchmark_1_market_rent` … `_rule_benchmark_4_cap_rate_vs_market` (config: `benchmark_market_*`) |
| TREND-3 "STUB" | Variance analysis | **IMPLEMENTED** | `_rule_trend_3_variance_analysis()` – budget vs actual by account (top 10) |
| AUDIT-51, 52 "NOT IMPLEMENTED" | Budget/forecast vs actual | **IMPLEMENTED** | `_rule_audit_51_budget_vs_actual()`, `_rule_audit_52_forecast_vs_actual()`; SKIP when no data |

**Verdict**: The analysis document is **outdated** for these items. No code changes required for “full” implementation of the rule logic; only data population and optional enhancements (below).

---

### 2.2 Rules That Are Implemented but Need Enhancement (Per Analysis)

| Rule(s) | Analysis Doc Statement | Current Implementation | Gap / Enhancement |
|---------|------------------------|------------------------|-------------------|
| **AUDIT-49** | "Year-end and year-over-year rules are basic. Need enhanced year-end close procedures." | Runs only for **January** periods; checks BS current earnings vs IS YTD vs period net income (reset_ok, ytd_matches_period). | Add **year-end close checklist**: e.g. retained earnings roll, closing entries verification, optional configurable checkpoints. |
| **AUDIT-50** | Same as above. | YoY comparison for total income, NOI, net income, occupancy; hard-coded -10% warning threshold. | Add **configurable YoY thresholds** (e.g. `audit50_income_decrease_pct`, `audit50_noi_decrease_pct`); optionally more metrics (revenue, expenses, cash). |

---

### 2.3 Rules That Are Implemented but Data-Dependent (No Code Gap)

| Rule(s) | Behavior When Data Missing | Required Data / Action |
|---------|----------------------------|------------------------|
| **AUDIT-51** | SKIP | `budgets` table populated (property_id, period_id, account_code, budgeted_amount, status='approved'). APIs: `POST /api/v1/variance-analysis/budget`, bulk import. |
| **AUDIT-52** | SKIP | `forecasts` table populated. APIs: `POST /api/v1/variance-analysis/forecast`, bulk import. |
| **TREND-3** | INFO "No approved budget data" | Same as AUDIT-51 – ensure budget entry (API + UI). |
| **ANALYTICS-4–33** | Many emit **INFO** when `_get_metric()` returns 0 or data missing | Populate **financial_metrics** (and property-level fields) via `POST /api/v1/metrics/properties/{id}/periods/{id}/recalculate` (MetricsService.calculate_all_metrics). |

**Verdict**: Full implementation = **data population and runbooks**, not new rule code. Phase 2 below focuses on ensuring entry paths and documentation.

---

### 2.4 Optional Hardening (Already Done or Low Priority)

| Item | Analysis / Deep Dive | Current State |
|------|----------------------|---------------|
| RRBS-1 tolerance | Make configurable | **DONE** – `system_config`: `rrbs_1_tolerance_usd` (default 1.0). |
| FA-CASH-4 materiality | Configurable min balance to flag | **DONE** – `system_config`: `fa_cash_4_min_balance_to_flag`. |
| Doc/rule matrix | Phase 4 "doc/rule matrix maintenance" | Optional: single source of truth (e.g. `docs/RULES_COVERAGE_MATRIX.md`) updated when rules change. |

---

## 3. Rules Not Fully Implemented – Consolidated Gap List

After reconciling the analysis doc with the codebase and deep dive doc, the **only remaining gaps** are:

### 3.1 Enhancement Gaps (Code Changes) — **DONE (Jan 2026)**

| ID | Description | Current State | Required Work |
|----|-------------|---------------|---------------|
| **AUDIT-49** | Year-end validation | **IMPLEMENTED (enhanced)** | Config: `audit49_earnings_tolerance_pct`; optional retained earnings roll; checklist in details. See `audit_rules_mixin._rule_audit_49_year_end_validation`. |
| **AUDIT-50** | Year-over-year comparison | **IMPLEMENTED (enhanced)** | Config: `audit50_income_decrease_pct`, `audit50_noi_decrease_pct`, `audit50_net_income_decrease_pct`, `audit50_occupancy_decrease_pp`. See `audit_rules_mixin._rule_audit_50_year_over_year_comparison`. |

### 3.2 Data / Workflow Gaps (No New Rule Code)

| ID | Description | Current State | Required Work |
|----|-------------|---------------|---------------|
| **AUDIT-51 / AUDIT-52** | Budget vs actual, Forecast vs actual | Implemented; SKIP when no data | Ensure **budget/forecast entry** (API + UI) and that `budgets` / `forecasts` are populated so rules run with data. |
| **ANALYTICS-4–33** | All analytics metrics | Implemented; INFO when metrics 0/missing | Ensure **financial_metrics** (and related) are **calculated and stored** after extraction/period close (recalculate API + docs). |
| **TREND-3** | Variance analysis | Implemented; INFO when no budget | Same as AUDIT-51 – budget data entry. |

### 3.3 Optional / Documentation

| Item | Description |
|------|-------------|
| **FA-MORT-4** | Fully implemented; optional workflow: promote escrow document linking in UI. |
| **Rule coverage matrix** | Maintain a single table (e.g. in `docs/`) with Rule ID, status, file/method, notes; update when rules change. |

---

## 4. Phased Plan to Fully Implement All Rules

### Phase 1: Enhance AUDIT-49 and AUDIT-50 (1–2 weeks) — **DONE (Jan 2026)**

**Goal**: Address the only remaining “basic” rules so year-end and YoY checks are spec-complete and configurable.

1. **AUDIT-49 (Year-end validation)** — **DONE**  
   - Config: `audit49_earnings_tolerance_pct` (default 1.0). Optional retained earnings roll (prior Dec RE + Jan NI vs Jan beginning RE). Checklist in details: BS=IS YTD, YTD=period, retained earnings roll ✓/✗/N/A.  
   - **Deliverable**: `_rule_audit_49_year_end_validation()` enhanced; seed key in `backend/scripts/seed_reconciliation_config.sql`.

2. **AUDIT-50 (Year-over-year comparison)** — **DONE**  
   - Config: `audit50_income_decrease_pct`, `audit50_noi_decrease_pct`, `audit50_net_income_decrease_pct`, `audit50_occupancy_decrease_pp` (defaults 10, 10, 10, 5). WARNING when any metric exceeds threshold.  
   - **Deliverable**: `_rule_audit_50_year_over_year_comparison()` uses config; seed keys in `backend/scripts/seed_reconciliation_config.sql`.

**Success criteria**:  
- AUDIT-49 and AUDIT-50 run for applicable periods; AUDIT-50 thresholds are configurable; no regression in existing behavior. **Met.**

---

### Phase 2: Data Population and Runbooks (2–3 weeks)

**Goal**: Maximize rule effectiveness so AUDIT-51, AUDIT-52, TREND-3, and ANALYTICS-4–33 run with real data (no SKIP/INFO when data exists).

**Runbook**: **docs/RECONCILIATION_DATA_POPULATION_RUNBOOK.md** documents APIs and steps.

1. **Budget / forecast entry**  
   - Documented in runbook: bulk import `POST /api/v1/bulk-import/budgets`, `POST /api/v1/bulk-import/forecasts`; variance analysis GET/POST endpoints.  
   - Ensure budget/forecast rows have `status = 'approved'` so AUDIT-51, AUDIT-52, and TREND-3 have data.  
   - **Deliverable**: Runbook done; optional “Recalculate variance” or “Sync budget” button in UI.

2. **Financial metrics population**  
   - Documented in runbook: `POST /api/v1/metrics/{property_code}/{year}/{month}/recalculate`; `MetricsService.calculate_all_metrics(property_id, period_id)`.  
   - Run after extraction or period close so ANALYTICS-4–33 and covenant rules read real values.  
   - **Deliverable**: Runbook done; optional “Recalculate metrics” button in UI; regression test that key rules do not SKIP/INFO when seed data is present.

**Success criteria**:  
- With seed budget/forecast and recalculated metrics, AUDIT-51, AUDIT-52, TREND-3, and a representative set of analytics rules return PASS or meaningful WARNING (not SKIP/INFO due to missing data).

---

### Phase 3: Documentation and Sign-Off (Ongoing) — **Partial (Jan 2026)**

**Goal**: Align all docs with implementation and keep a single source of truth for rule coverage.

1. **Update RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md** — **DONE**  
   - Analysis doc updated; AUDIT-49/50 set to **IMPLEMENTED (enhanced)** with config keys.

2. **Rule coverage matrix** — **DONE**  
   - `docs/RULES_COVERAGE_MATRIX.md` created with Rule ID, Rule name, Status, File/method, Notes. Update when rules change.

3. **Success criteria (global)**  
   - Every rule in the analysis doc has status other than "NOT IMPLEMENTED." **Met.**  
   - AUDIT-49/50: enhanced and configurable. **Met.**  
   - Data entry and metrics recalculation are documented; key rules run without SKIP/INFO when seed data is provided. **Runbook**: `docs/RECONCILIATION_DATA_POPULATION_RUNBOOK.md`.

---

## 5. Summary: What’s Left to “Fully Implement All Rules”

| Category | Action |
|----------|--------|
| **FA-MORT-4, COVENANT-6, BENCHMARK-1–4, TREND-3, AUDIT-51/52, ANALYTICS-1–33** | Already implemented. No code gap; ensure data population (Phase 2 runbook) and doc updates (Phase 3). |
| **AUDIT-49** | **DONE** – Enhanced with config and optional retained earnings roll (Phase 1). |
| **AUDIT-50** | **DONE** – Enhanced with configurable YoY thresholds (Phase 1). |
| **Budget/forecast and financial_metrics** | Documented in `docs/RECONCILIATION_DATA_POPULATION_RUNBOOK.md`; add UI “Recalculate metrics” / budget entry as needed (Phase 2). |
| **RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md** | Updated; AUDIT-49/50 marked IMPLEMENTED (enhanced) (Phase 3). |
| **Rule coverage matrix** | `docs/RULES_COVERAGE_MATRIX.md` created; maintain when rules change (Phase 3). |

---

## 6. Financial Integrity Hub – Overview Tab (Jan 2026)

The hub Overview tab at `#forensic-reconciliation` includes: **Covenant Compliance** (current period), **Covenant History** (table by period; "View in Covenant Compliance" → `#covenant-compliance`), and **Variance Alerts** (AUDIT-48; "View all" → Risk; new alerts trigger `AlertNotificationService.notify_alert_created`). See `docs/RECONCILIATION_QUICK_REFERENCE.md` and `docs/RULES_COVERAGE_MATRIX.md`.

---

## 7. Recommended Next Steps

1. **Phase 1** (AUDIT-49/50 enhancement) — **DONE**.  
2. **Phase 2**: Use `docs/RECONCILIATION_DATA_POPULATION_RUNBOOK.md`; optionally add UI “Recalculate metrics” and budget/forecast entry flows.  
3. **Phase 3**: Keep `docs/RULES_COVERAGE_MATRIX.md` updated when rules change.  
4. **Optional**: Implement FA-MORT-4 escrow document linking workflow in the UI if required by operations.

---

**Document version**: 1.2  
**Last updated**: January 29, 2026
