# Reconciliation Rules – Coverage Matrix

**Date**: January 29, 2026  
**Purpose**: Single source of truth for rule implementation status. Update when rules are added or changed.  
**Reference**: `RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md`, `backend/app/services/rules/RULES_MAPPING.md`

---

## Status Legend

| Status | Meaning |
|--------|--------|
| **Full** | Rule implemented; runs with real logic; may emit INFO/SKIP when data missing. |
| **Data-dependent** | Rule implemented; requires populated data (budget, forecast, financial_metrics) to return PASS. |
| **Enhanced** | Rule implemented with configurable thresholds or optional checklist (Phase 1 enhancements). |

---

## Rule Coverage Table

| Rule ID | Rule name | Status | File / method | Notes |
|---------|------------|--------|---------------|-------|
| FA-PAL-1..5 | Period alignment | Full | period_alignment_mixin.py | Period type, CF window, begin/end inference |
| FA-CASH-1..4 | Cash flow consistency, appearance/disappearance | Full | forensic_anomaly_rules_mixin.py; cash_flow_rules.py | FA-CASH-4 config: fa_cash_4_min_balance_to_flag |
| FA-FRAUD-1..4 | Duplicate round, Benford, accrual reversals, tenant concentration | Full | forensic_anomaly_rules_mixin.py | |
| FA-WC-1, FA-WC-2, WCR-1, WCR-2, WCR-3 | Working capital, escrow three-way | Full | audit_rules_mixin.py | WCR: generic delta, appearance/disappearance, escrow activity |
| MCI-1, MCI-3, MCI-4, MCI-5, MCI-6 | Mortgage/principal/escrow validation | Full | audit_rules_mixin.py | Principal reduction, escrow funding vs disbursements |
| FA-MORT-1..4 | Principal, principal flow, interest, escrow documentation | Full | audit_rules_mixin.py; Financials.tsx | FA-MORT-4: EscrowDocumentLink + UI in Financials → Statements (link/remove escrow docs); config fa_mort_4_materiality_threshold |
| RRBS-1..4 (FA-RR-1..4) | Security deposits, A/R bands, prepaid rent, lease roster | Full | rent_roll_balance_sheet_rules_mixin.py | RRBS-1 config: rrbs_1_tolerance_usd |
| AUDIT-1..48 | Balance sheet, cash, net income, mortgage, rent roll, working capital, D&A, CapEx, debt service, ratios, data quality, covenant, variance | Full | audit_rules_mixin.py | AUDIT-48 config: audit48_*_pct |
| **AUDIT-49** | Year-end validation | **Enhanced** | audit_rules_mixin._rule_audit_49_year_end_validation | Config: audit49_earnings_tolerance_pct; optional retained earnings roll; checklist in details |
| **AUDIT-50** | Year-over-year comparison | **Enhanced** | audit_rules_mixin._rule_audit_50_year_over_year_comparison | Config: audit50_income_decrease_pct, audit50_noi_decrease_pct, audit50_net_income_decrease_pct, audit50_occupancy_decrease_pp |
| AUDIT-51 | Budget vs actual | Data-dependent | audit_rules_mixin._rule_audit_51_budget_vs_actual | SKIP when no approved budget; populate via bulk-import/budgets |
| AUDIT-52 | Forecast vs actual | Data-dependent | audit_rules_mixin._rule_audit_52_forecast_vs_actual | SKIP when no approved forecast; populate via bulk-import/forecasts |
| AUDIT-53..55 | Supporting docs, journal tracking, checklists | Full | audit_rules_mixin.py | |
| DQ-1..33 | Data quality | Full | data_quality_rules_mixin.py | |
| ANALYTICS-1..33 | NOI, margin, CoC, cap rate, occupancy, rollover, retention, WALT, growth, LTV, DSCR, ICR, debt yield, current ratio, CF coverage, days cash, AR days, ROA, ROE, margin, per-SF, efficiency, risk metrics | Full | analytics_rules_mixin.py | INFO when financial_metrics missing; populate via metrics recalculate |
| COVENANT-1..6 | DSCR, LTV, liquidity, occupancy, tenant concentration, reporting | Full | analytics_rules_mixin.py + covenant_resolver | COVENANT-6: covenant_reporting_deadline_days |
| BENCHMARK-1..4 | Market rent, opex, occupancy, cap rate | Full | analytics_rules_mixin.py | Config: benchmark_market_* |
| TREND-1..3 | 3-month MA, YoY, variance analysis | Full | analytics_rules_mixin.py | TREND-3: budget vs actual by account; data-dependent when no budget |
| STRESS-1..5 | Occupancy, rent, expense, interest, tenant loss | Full | analytics_rules_mixin.py | |
| DASHBOARD-1..3 | Dashboard requirements | Full | analytics_rules_mixin.py | |

---

## Data Population (Phase 2)

To maximize rule effectiveness:

- **Financial metrics**: Call `POST /api/v1/metrics/{property_code}/{year}/{month}/recalculate` after extraction/period close so ANALYTICS-4–33 and covenant rules read real values.
- **Budget / forecast**: Use `POST /api/v1/bulk-import/budgets` and `POST /api/v1/bulk-import/forecasts`; set `status = 'approved'` so AUDIT-51, AUDIT-52, and TREND-3 run with data.

See **docs/RECONCILIATION_DATA_POPULATION_RUNBOOK.md**.

---

## Maintenance

**When to update**

- A new rule is added in `backend/app/services/rules/` (any mixin).
- A rule’s status or behavior changes (e.g. new config, now data-dependent).
- A rule is removed or renamed.

**How to update**

1. Open this file and find the rule in the **Rule Coverage Table** (or add a new row).
2. Set **Status**: `Full` | `Data-dependent` | `Enhanced` per the legend.
3. Set **File / method**: e.g. `audit_rules_mixin._rule_audit_49_year_end_validation`.
4. Add or adjust **Notes** (config keys, UI location, data requirements).
5. Bump **Document version** and **Last updated** at the bottom.
6. (Optional) Run the validation script to compare code vs matrix (see below).

**Where rule IDs live in code**

- Audit / forensic: `backend/app/services/rules/audit_rules_mixin.py`, `forensic_anomaly_rules_mixin.py` — search for `rule_id="..."`.
- Other mixins: `analytics_rules_mixin.py`, `data_quality_rules_mixin.py`, `period_alignment_mixin.py`, `rent_roll_balance_sheet_rules_mixin.py`, `cash_flow_rules.py`.
- Mapping doc: `backend/app/services/rules/RULES_MAPPING.md`.

**Validation script**

From repo root:

```bash
python scripts/validate_rules_coverage_matrix.py
```

The script parses rule IDs from this matrix and from backend rule code; it prints any IDs in code that are missing from the matrix (or vice versa) so you can keep the table in sync. See `scripts/validate_rules_coverage_matrix.py` for options.

---

**Document version**: 1.1  
**Last updated**: January 29, 2026
