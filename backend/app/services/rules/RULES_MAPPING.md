## Rules Mapping: Markdown Specifications → Implementation

This document maps rule IDs defined in the reconciliation/audit rule markdown
files to their concrete implementations in the REIMS backend.

**Status & coverage**: For implementation status and a rule coverage matrix (as of Jan 2026), see repo root **RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md** and **docs/RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md**.

### Period Alignment / PAL & FA-PAL

- **PAL / FA-PAL-1..5**  
  - Implemented in `period_alignment_mixin.py`:
    - `PeriodAlignmentMixin._detect_period_types`
    - `PeriodAlignmentMixin._get_cf_cash_table_totals`
    - `PeriodAlignmentMixin._infer_begin_period_id`
    - `PeriodAlignmentMixin._get_bs_delta_in_window`

### Analytics / Covenant / Benchmark / Trend / Stress / Dashboard

- **ANALYTICS-1..33, COVENANT-1..6, BENCHMARK-1..4, TREND-1..3, STRESS-1..5, DASHBOARD-1..3**  
  - Implemented in `analytics_rules_mixin.py`:
    - `AnalyticsRulesMixin._execute_analytics_rules` and `_rule_analytics_*`,
      `_rule_covenant_*`, `_rule_benchmark_*`, `_rule_trend_*`, `_rule_stress_*`,
      `_rule_dashboard_*` methods.

### Data Quality / DQ

- **DQ-1..33**  
  - Implemented in `data_quality_rules_mixin.py`:
    - `DataQualityRulesMixin._execute_data_quality_rules` and `_rule_dq_*` methods.

### Forensic Anomaly / FA / FA-WC / FA-MORT / FA-RR

- **FA-1..7** (from `forensic_anomaly_rules.md`)  
  - Implemented in `forensic_anomaly_rules_mixin.py`:
    - `_rule_fa_1_cash_flow_internal_consistency`
    - `_rule_fa_2_working_capital_sign_test`
    - `_rule_fa_3_non_cash_journal_detector`
    - `_rule_fa_4_duplicate_round_numbers`
    - `_rule_fa_5_benford_screen`
    - `_rule_fa_6_tenant_concentration_sanity`
    - `_rule_fa_7_accrual_reversals`

- **FA-WC-1** (working-capital attribution)  
  - Implemented in `forensic_anomaly_rules_mixin.py`:
    - `_rule_fa_wc_1_working_capital_attribution`

- **FA-MORT-1..2** (mortgage payment continuity & escrow reasonableness)  
  - Implemented in `forensic_anomaly_rules_mixin.py`:
    - `_rule_fa_mort_1_payment_history_continuity`
    - `_rule_fa_mort_2_escrow_balance_reasonableness`

- **FA-MORT-4** (escrow disbursement documentation linkage)  
  - Implemented in `audit_rules_mixin.py`:
    - `_rule_fa_mort_4_escrow_documentation_link()` — requires `EscrowDocumentLink` or supporting document upload for material escrow disbursements (tax/insurance/reserves).
  - Data: `EscrowDocumentLink` model (`escrow_document_links` table); config `fa_mort_4_materiality_threshold` (optional, falls back to `audit_53_materiality_threshold`).
  - API: `GET/POST /documents/escrow-links`, `DELETE /documents/escrow-links/{id}` (see `app/api/v1/documents.py`).

- **FA-RR-1** (lease term consistency)  
  - Implemented in `forensic_anomaly_rules_mixin.py`:
    - `_rule_fa_rr_1_lease_term_consistency`

### Rent Roll ↔ Balance Sheet Forensic Rules / RRBS

- **RRBS-1..4**  
  - Implemented in `rent_roll_balance_sheet_rules_mixin.py`:
    - `_rule_rrbs_1_security_deposits_floor`
    - `_rule_rrbs_2_ar_reasonableness`
    - `_rule_rrbs_3_prepaid_rent`
    - `_rule_rrbs_4_lease_roster_completeness`

### Working Capital Reconciliation / WCR

- **WCR-1** (generic delta rule)  
  - Implemented in `audit_rules_mixin.py`:
    - `_rule_wcr_1_generic_delta_reconciliation`

- **WCR-2** (appearance/disappearance rule)  
  - Implemented in `audit_rules_mixin.py`:
    - `_rule_wcr_2_account_appearance_disappearance`

- **WCR-3** (escrow activity consistency)  
  - Implemented in `audit_rules_mixin.py`:
    - `_rule_wcr_3_escrow_activity_three_way`

### Mortgage ↔ Cash Flow ↔ Income Statement / MCI

- **MCI-1..3,5** (principal tie, escrows, principal CF mapping, interest reasonableness)  
  - Primarily implemented via existing AUDIT rules in `audit_rules_mixin.py`:
    - `AUDIT-4` – `_rule_audit_4_mortgage_principal_balance`
    - `AUDIT-5-*` – `_rule_audit_5_escrow_three_way`
    - `AUDIT-6` – `_rule_audit_6_mortgage_interest_flow`
    - `AUDIT-7` – `_rule_audit_7_mortgage_payment_composition`

- **MCI-4** (principal reduction validation)  
  - Implemented in `audit_rules_mixin.py`:
    - `_rule_mci_4_principal_reduction_validation`

- **MCI-6** (escrow funding vs disbursements)  
  - Implemented in `audit_rules_mixin.py`:
    - `_rule_mci_6_escrow_funding_vs_disbursements`

### Cross-Document Audit / AUDIT

- **AUDIT-1..5,7..7,10..24,26..36,37..39,40..55**  
  - Implemented in `audit_rules_mixin.py`:
    - `_execute_audit_rules` and the corresponding `_rule_audit_*` methods.
  - Notable mappings:
    - **AUDIT-1** – `_rule_audit_1_balance_sheet_equation`
    - **AUDIT-2** – `_rule_audit_2_cash_reconciliation`
    - **AUDIT-3** – `_rule_audit_3_net_income_three_way`
    - **AUDIT-4** – `_rule_audit_4_mortgage_principal_balance`
    - **AUDIT-5** – `_rule_audit_5_escrow_three_way`
    - **AUDIT-6** – `_rule_audit_6_mortgage_interest_flow`
    - **AUDIT-7** – `_rule_audit_7_mortgage_payment_composition`
    - **AUDIT-24** – `_rule_audit_24_cash_flow_cash_bridge`
    - **AUDIT-26** – `_rule_audit_26_operating_activities_reconciliation`

This file is intentionally high-level; for any given rule ID, search for the
`rule_id` in the corresponding mixin to see the exact implementation details.

