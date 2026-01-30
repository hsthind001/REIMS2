# Reconciliation Rules – Deep Dive and Full Implementation Plan

**Date**: January 29, 2026  
**Reference**: `RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md` (January 28, 2026)  
**Codebase**: REIMS2 backend rules engine (post Phase 1–2 implementation)

---

## 1. Executive Summary

The analysis document (`RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md`) was written before the Phase 1–2 work (RRBS-2/3, AUDIT-48 config, covenant per-property, ANALYTICS-8, etc.). A **codebase deep dive** shows that **many rules the analysis marked as "NOT IMPLEMENTED" or "PARTIALLY IMPLEMENTED" are already implemented**, sometimes under different names or with INFO/SKIP when data is missing.

This document:

1. **Corrects** the analysis against the current codebase (what is actually implemented).
2. **Identifies** the **remaining gaps** (stubs, missing data wiring, or missing features).
3. **Proposes a phased plan** to fully implement or harden all rules.

---

## 2. Current Implementation vs Analysis Document

### 2.1 Forensic Accounting Rules

| Analysis Doc | Rule | Current State | Location |
|--------------|------|---------------|----------|
| FA-CASH-4 "NEEDS ENHANCEMENT" | Account appearance/disappearance | **FULLY IMPLEMENTED** | `cash_flow_rules.py`: `_rule_fa_cash_4_appearance_disappearance()`; also `audit_rules_mixin.py`: `_rule_wcr_2_account_appearance_disappearance()` |
| FA-RR-1 "NEEDS IMPLEMENTATION" | Security deposit floor | **IMPLEMENTED** | `rent_roll_balance_sheet_rules_mixin.py`: `_rule_rrbs_1_security_deposits_floor()` (BS ≥ RR) |
| FA-RR-2 "NEEDS IMPLEMENTATION" | A/R reasonableness bands | **IMPLEMENTED** | Same file: `_rule_rrbs_2_ar_reasonableness()` (AR_Months + 5 bands) |
| FA-RR-3 "NEEDS IMPLEMENTATION" | Prepaid rent reasonability | **IMPLEMENTED** | Same file: `_rule_rrbs_3_prepaid_rent()` ($20k default, configurable) |
| FA-RR-4 | Lease roster completeness | **IMPLEMENTED** | Same file: `_rule_rrbs_4_lease_roster_completeness()` |
| FA-MORT-4 "PARTIALLY IMPLEMENTED" | Escrow documentation | **PARTIAL** | No dedicated escrow→document link; AUDIT-53 checks generic supporting docs |

**Verdict**: Forensic rules are implemented except **FA-MORT-4** (escrow documentation linkage), which is a workflow/data-model enhancement.

---

### 2.2 Cross-Document Audit Rules

| Analysis Doc | Rule | Current State | Location |
|--------------|------|---------------|----------|
| AUDIT-48 "NEEDS ENHANCEMENT" | Variance investigation triggers | **IMPLEMENTED (configurable)** | `audit_rules_mixin.py`: `_rule_audit_48_variance_investigation_triggers()`; thresholds from `system_config` |
| AUDIT-43–46 "PARTIALLY" (configurable thresholds) | Covenant compliance | **IMPLEMENTED (per-property)** | `covenant_thresholds` table + `covenant_resolver.py`; AUDIT-43/44/45 use resolver |
| AUDIT-51 "NOT IMPLEMENTED" | Budget vs actual | **IMPLEMENTED** | `audit_rules_mixin.py`: `_rule_audit_51_budget_vs_actual()`; SKIP when no budget data |
| AUDIT-52 "NOT IMPLEMENTED" | Forecast vs actual | **IMPLEMENTED** | Same: `_rule_audit_52_forecast_vs_actual()`; SKIP when no forecast data |
| AUDIT-53, AUDIT-54 | Supporting docs / journal tracking | **IMPLEMENTED** | `_rule_audit_53_supporting_documentation()`, `_rule_audit_54_adjustment_journal_entry_tracking()` |

**Verdict**: Audit rules AUDIT-1–55 are implemented. Budget/Forecast **models exist** (`Budget`, `Forecast` in `backend/app/models/budget.py`). The only gap is ensuring **budget/forecast data entry** (UI/API) so AUDIT-51/52 run with data instead of SKIP.

---

### 2.3 Advanced Analytics (ANALYTICS-1–33)

| Analysis Doc | Rule | Current State | Location |
|--------------|------|---------------|----------|
| ANALYTICS-4, 5 "NOT IMPLEMENTED" | Cash-on-cash, Cap rate | **IMPLEMENTED** | `analytics_rules_mixin.py`: `_rule_analytics_4_cash_on_cash()`, `_rule_analytics_5_cap_rate()` |
| ANALYTICS-6–10 "NOT IMPLEMENTED" | Economic occ, rollover, retention, WALT, growth | **IMPLEMENTED** | Same file: 6–10 with real calc or INFO when data missing |
| ANALYTICS-13, 14 "NOT IMPLEMENTED" | Interest coverage, Debt yield | **IMPLEMENTED** | `_rule_analytics_13_interest_coverage()`, `_rule_analytics_14_debt_yield()` |
| ANALYTICS-15–18 "NOT IMPLEMENTED" | Current ratio, CF coverage, days cash, AR days | **IMPLEMENTED** | Same file: 15–18 |
| ANALYTICS-19–24 "NOT IMPLEMENTED" | ROA, ROE, margin, per-SF, efficiency | **IMPLEMENTED** | Same file: 19–24 |
| ANALYTICS-25–33 "MOSTLY NOT IMPLEMENTED" | Risk metrics | **IMPLEMENTED** | Same file: 25–33 (debt-to-equity, concentration, lease expiration, etc.) |

**Verdict**: All ANALYTICS-1–33 rules exist. Many emit **INFO** when `_get_metric()` returns 0 or data is missing; "full" implementation means **populating `financial_metrics`** (and related sources) so these rules output PASS with real numbers.

---

### 2.4 Covenant Rules (COVENANT-1–6)

| Analysis Doc | Rule | Current State | Location |
|--------------|------|---------------|----------|
| COVENANT-1–3 | DSCR, LTV, Min liquidity | **IMPLEMENTED (per-property)** | `analytics_rules_mixin.py` + `covenant_resolver` |
| COVENANT-4, 5 "NOT IMPLEMENTED" | Occupancy ≥85%, Single tenant ≤20% | **IMPLEMENTED (per-property)** | `_rule_covenant_4_occupancy()`, `_rule_covenant_5_tenant_concentration()` with resolver |
| COVENANT-6 "NOT IMPLEMENTED" | Reporting requirements | **STUB** | `_rule_covenant_6_reporting_requirements()`: INFO only, points to DQ-16 |

**Verdict**: COVENANT-1–5 are full. **COVENANT-6** is an INFO stub; full implementation would validate **reporting deadlines** (e.g. covenant submission dates) against document upload dates.

---

### 2.5 Benchmark, Trend, Stress (BENCHMARK-1–4, TREND-1–3, STRESS-1–5)

| Analysis Doc | Rule | Current State | Location |
|--------------|------|---------------|----------|
| BENCHMARK-1–4 "NOT IMPLEMENTED" | Market comparison | **STUB** | `analytics_rules_mixin.py`: each tries `market_data_integration`; else INFO "Market data not available" |
| TREND-1, 2 "NOT IMPLEMENTED" | 3-month MA, YoY | **IMPLEMENTED** | `_rule_trend_1_3_month_ma()`, `_rule_trend_2_year_over_year()` with real queries |
| TREND-3 | Variance analysis | **STUB** | INFO: "Variance vs budget/forecast tracked in AUDIT-51/52" |
| STRESS-1–5 "NOT IMPLEMENTED" | Stress scenarios | **IMPLEMENTED** | `_rule_stress_1_occupancy()` through `_rule_stress_5_tenant_loss()` with scenario logic |

**Verdict**: TREND-1/2 and STRESS-1–5 are implemented. **BENCHMARK-1–4** are stubs without real market data. **TREND-3** could be deepened to show variance breakdown (e.g. by account).

---

## 3. Rules Not Fully Implemented (Gap List)

After aligning the analysis with the codebase, the **remaining gaps** are:

### 3.1 High impact (spec-called, currently stub or missing)

| ID | Description | Current State | Required Work |
|----|-------------|---------------|----------------|
| **COVENANT-6** | Reporting requirements (timeliness) | INFO stub, references DQ-16 | Validate document upload dates vs covenant submission deadlines (need covenant_deadline or config). |
| **BENCHMARK-1–4** | Market rent/OpEx/occupancy/cap rate comparison | INFO when no market data | Either: (a) Integrate real market data source, or (b) Allow user-defined benchmark targets (e.g. market cap rate %) and compare property metric to target. |
| **TREND-3** | Variance analysis | INFO stub, points to AUDIT-51/52 | Optionally: breakdown variance by account/category and surface in rule details. |

### 3.2 Data / workflow (rules exist, need data or linkage)

| ID | Description | Current State | Required Work |
|----|-------------|---------------|----------------|
| **AUDIT-51 / AUDIT-52** | Budget vs actual, Forecast vs actual | Implemented; SKIP when no data | Ensure budget/forecast **entry** (API + UI) and that `budgets` / `forecasts` are populated so rules run. |
| **ANALYTICS-4–33** | Many metrics | Implemented; INFO when `_get_metric()` is 0 | Ensure **financial_metrics** (and property fields like `net_property_value`, `total_equity`) are calculated and stored from BS/IS/CF so rules output real values. |
| **FA-MORT-4** | Escrow disbursement documentation | No dedicated link | Add optional **escrow disbursement → document** linkage (table or metadata) and/or align AUDIT-53 to escrow-specific checks. |

### 3.3 Optional hardening

| Item | Description | Current State | Optional Work |
|------|-------------|---------------|----------------|
| **RRBS-1** | Security deposit floor | PASS if BS ≥ RR − $1 | Make tolerance configurable (e.g. `system_config` or per-property). |
| **FA-CASH-4 / WCR-2** | Appearance/disappearance | Full implementation | Consider configurable materiality (min balance to flag). |

---

## 4. Phased Plan to Fully Implement All Rules

### Phase 1: Close spec gaps (1–2 weeks) — **IMPLEMENTED** (Jan 2026)

**Goal**: Implement or harden every rule referenced in the analysis so none remains "NOT IMPLEMENTED" or "stub only" without a clear path.

1. **COVENANT-6 (Reporting requirements)** — **DONE**  
   - `system_config` key: `covenant_reporting_deadline_days` (days after period end by which documents must be uploaded).  
   - In `_rule_covenant_6_reporting_requirements()`: if key missing or 0, INFO with message to configure; else query `document_uploads` for property/period, count uploads by deadline; PASS if any on time, FAIL if uploads exist but none by deadline, INFO if no uploads.

2. **BENCHMARK-1–4 (Market comparison)** — **DONE**  
   - User-defined targets in `system_config`: `benchmark_market_rent_per_sf`, `benchmark_market_opex_per_sf`, `benchmark_market_occupancy_pct`, `benchmark_market_cap_rate_pct`.  
   - Rules compare property metric to target; if target not set (0): INFO with hint to set key; else PASS/WARNING with variance (e.g. ±10% rent, ±15% opex, ±5 pp occupancy, ±1.5 pp cap rate).

3. **TREND-3 (Variance analysis)** — **DONE**  
   - Query `budgets` joined to `income_statement_data` by account; top 10 accounts by budget amount; overall and per-account variance. If no approved budget data: INFO pointing to AUDIT-51/52; else PASS/INFO with "Top accounts: …" details.

**Deliverables**: COVENANT-6, BENCHMARK-1–4, TREND-3 implemented in `analytics_rules_mixin.py`; optional seed in `backend/scripts/seed_reconciliation_config.sql`.

---

### Phase 2: Data and metrics (2–3 weeks)

**Goal**: Maximize rule effectiveness by ensuring data exists so AUDIT-51/52 and analytics rules run with real numbers.

1. **Budget / Forecast entry**  
   - Confirm APIs for creating/updating `Budget` and `Forecast` (and that they use `account_code` / period alignment).  
   - Add or refine UI for budget/forecast entry by period and account so AUDIT-51 and AUDIT-52 have data and no longer SKIP when appropriate.

2. **Financial metrics population**  
   - Ensure a job or service **calculates and writes** to `financial_metrics` (and property-level fields if used) from balance sheet, income statement, cash flow, and rent roll.  
   - Map which metrics each analytics rule uses (e.g. `net_property_value`, `total_equity`, `total_revenue`, `net_operating_income`, etc.) and ensure they are populated so ANALYTICS-4–33 and covenant rules produce PASS with values instead of INFO.

**Deliverables**: Budget/forecast entry path documented and working; financial_metrics (and related) population documented and runnable; regression test that key rules (e.g. AUDIT-51, ANALYTICS-4, 5) run without SKIP/INFO when seed data is present.

---

### Phase 2: Data and metrics (2–3 weeks) — Triggers already exist

**Goal**: Maximise rule effectiveness by ensuring data exists so AUDIT-51/52 and analytics rules run with real numbers.

**How to trigger / populate data** (no new code required; use existing APIs):

1. **Financial metrics**  
   - **API**: `POST /api/v1/metrics/properties/{property_id}/periods/{period_id}/recalculate` (see `backend/app/api/v1/metrics.py`).  
   - **Service**: `MetricsService(db).calculate_all_metrics(property_id, period_id)` computes from BS/IS/CF/rent roll and upserts into `financial_metrics`.  
   - Call after extraction or period close so ANALYTICS-4–33 and covenant rules read real values.

2. **Budget / forecast**  
   - **APIs**: `POST /api/v1/variance-analysis/budget`, `POST /api/v1/variance-analysis/forecast`; GET variants by property/period (see `backend/app/api/v1/variance_analysis.py`).  
   - **Bulk import**: `POST /api/v1/bulk-import/budgets`, `POST /api/v1/bulk-import/forecasts` (CSV/Excel) in `backend/app/api/v1/bulk_import.py`.  
   - Ensure `budgets` and `forecasts` rows exist with `status = 'approved'` (or equivalent) and match `account_code` / period so AUDIT-51, AUDIT-52, and TREND-3 have data.

**Deliverables**: Document the above in runbooks or onboarding; optionally add a “Recalculate metrics” button in the UI for a property/period.

---

### Phase 3: Escrow documentation and optional hardening (1–2 weeks) — **FA-MORT-4 IMPLEMENTED** (Jan 2026)

**Goal**: Address FA-MORT-4 and optional tolerances.

1. **FA-MORT-4 (Escrow documentation)** — **DONE**  
   - **Model**: `EscrowDocumentLink` (`escrow_document_links` table) links `property_id`, `period_id`, `document_upload_id`, and `escrow_type` (property_tax, insurance, reserves, general). Migration: `20260129_0003_add_escrow_document_links_table.py`.  
   - **Rule**: `_rule_fa_mort_4_escrow_documentation_link()` in `audit_rules_mixin.py`. When material escrow disbursement (period delta of YTD tax/insurance/reserve) exceeds threshold (`fa_mort_4_materiality_threshold` or `audit_53_materiality_threshold`), requires either an `EscrowDocumentLink` for that type or a supporting document upload (mortgage_statement, tax_bill, insurance_invoice). Wired in `_execute_audit_rules()`.  
   - **API**: `GET/POST /documents/escrow-links`, `DELETE /documents/escrow-links/{id}` in `app/api/v1/documents.py`; config seed: `fa_mort_4_materiality_threshold` in `backend/scripts/seed_reconciliation_config.sql`.

2. **Optional**  
   - **RRBS-1: configurable tolerance** — **DONE** (Jan 2026). `system_config` key `rrbs_1_tolerance_usd` (default 1.0); rule in `rent_roll_balance_sheet_rules_mixin.py` uses `get_numeric_config_sync(self.db, "rrbs_1_tolerance_usd", 1.0)`.  
   - **FA-CASH-4: configurable materiality** — **DONE** (Jan 2026). `system_config` key `fa_cash_4_min_balance_to_flag` (default 0 = flag all); rule in `cash_flow_rules.py` only adds to appeared/disappeared when the non-zero balance has abs() >= this value (e.g. 1000 to ignore small noise).

**Deliverables**: Escrow–document linkage (if adopted); RRBS-1 and FA-CASH-4 config implemented.

---

### Phase 4: Documentation and sign-off

**Goal**: Align documentation and success criteria with actual implementation.

1. **Update RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md**  
   - Mark as implemented: FA-CASH-4, FA-RR-1–4, AUDIT-48, AUDIT-51/52, covenant per-property, ANALYTICS-4–33, BENCHMARK/TREND/STRESS as per Section 2.  
   - In each section, add a short "As of [date], implementation status: [location and method]."

2. **Rule coverage matrix**  
   - One table: Rule ID, name, implementation status (Full / Stub / Data-dependent), file/method, notes.  
   - Maintain in `docs/` or in `RULES_MAPPING.md`.

3. **Success criteria**  
   - All rules in the analysis doc have a non-"NOT IMPLEMENTED" status.  
   - COVENANT-6 and BENCHMARK either implemented with config or explicitly documented as "INFO until market/deadline config."  
   - AUDIT-51/52 and key analytics run without SKIP/INFO when seed data is provided; financial_metrics population is documented and runnable.

---

## 5. Summary Table: What’s Implemented vs What’s Left

| Category | Analysis said | Actual state | Remaining work |
|----------|----------------|--------------|----------------|
| FA-PAL, FA-CASH, FA-FRAUD, FA-WC, FA-MORT-1–4, FA-RR | Mixed "needs implementation" | **Implemented** (incl. FA-CASH-4, RRBS-1–4, FA-MORT-4 escrow link) | None |
| AUDIT-1–55 | AUDIT-48/51/52 "not implemented" | **Implemented** (48 configurable, 51/52 full, SKIP when no data) | Ensure budget/forecast data entry (Phase 2 – data, not code) |
| DQ-1–33 | Implemented | **Implemented** | None |
| ANALYTICS-1–33 | Many "not implemented" | **Implemented** (INFO when data missing) | Populate financial_metrics (Phase 2 – data, not code) |
| COVENANT-1–6 | 4–6 "not implemented" | 1–6 **implemented** (6: deadline check via covenant_reporting_deadline_days) | None |
| BENCHMARK-1–4 | Not implemented | **Implemented** (configurable targets: benchmark_market_* in system_config) | None |
| TREND-1–3, STRESS-1–5 | Not implemented | **Implemented** (TREND-3: budget vs actual by account; STRESS-1–5 scenario logic) | None |

---

## 6. Recommended Next Steps

1. **Review** this deep dive and the phased plan with the team.  
2. **Prioritise** Phase 1 (COVENANT-6, BENCHMARK, TREND-3) if spec compliance is required soon.  
3. **Prioritise** Phase 2 (budget/forecast entry, financial_metrics) if the goal is maximum rule utilisation with real data.  
4. **Update** `RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md` after Phase 1 (and optionally after Phase 2) so the analysis reflects the codebase.  
5. **Add** a single source of truth (e.g. rule coverage matrix in `docs/` or `RULES_MAPPING.md`) and keep it updated as rules are added or changed.

---

**Document version**: 1.0  
**Last updated**: January 29, 2026
