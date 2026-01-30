# Reconciliation Rules Implementation Summary

This document summarizes the implementation completed per the plan in `RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md` and the follow-up plan (reconciliation_rules_full_implementation).

**See also**: [RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md](RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md) for a **deep dive** that corrects the analysis doc against the current codebase and a **phased plan to fully implement all rules** (remaining gaps: COVENANT-6, BENCHMARK-1–4, TREND-3, data population).

## What Was Implemented

### Phase 1 – Spec alignment and config

- **RRBS-2 (A/R reasonableness bands)**  
  - `backend/app/services/rules/rent_roll_balance_sheet_rules_mixin.py`  
  - AR_Months = BS A/R Tenants / Monthly Scheduled Rent; bands: Excellent (&lt;0.5), Good (0.5–1.0), Acceptable (1.0–2.0), Concerning (2.0–3.0), Critical (3.0+).  
  - Details and `intermediate_calculations` include `ar_months` and `band`.

- **RRBS-3 (Prepaid rent threshold)**  
  - Same file.  
  - Default material threshold **$20,000** (was $50,000).  
  - Configurable via `system_config` key `forensic_prepaid_rent_material_threshold`.

- **AUDIT-48 (Configurable variance thresholds)**  
  - `backend/app/services/rules/audit_rules_mixin.py`  
  - Thresholds from `system_config`: `audit48_assets_change_pct` (default 5.0), `audit48_revenue_decrease_pct` (default 10.0), `audit48_cash_decrease_pct` (default 30.0).

### Phase 2 – Covenant and retention

- **Covenant per-property configuration**  
  - **Model:** `backend/app/models/covenant_threshold.py` (`CovenantThreshold`).  
  - **Migration:** `backend/alembic/versions/20260129_0001_add_covenant_thresholds_table.py`.  
  - **Resolver:** `backend/app/services/rules/covenant_resolver.py`  
    - `resolve_covenant_threshold_sync()` and `resolve_covenant_threshold_async()`  
    - Order: `covenant_thresholds` (by property + period) → `system_config` → defaults.  
  - **Wired into:** Audit rules (AUDIT-43 DSCR, AUDIT-44 LTV, AUDIT-45 MIN_LIQUIDITY), analytics covenant rules (COVENANT-1–5), and `CovenantComplianceService` (DSCR, LTV).

- **ANALYTICS-8 (Tenant retention rate)**  
  - **Model:** `backend/app/models/rent_roll_data.py` – added optional `renewal_status`.  
  - **Migration:** `backend/alembic/versions/20260129_0002_add_rent_roll_renewal_status.py`.  
  - **Rule:** `backend/app/services/rules/analytics_rules_mixin.py` – 12‑month lookback; retention = renewed / expiring when `renewal_status` is populated; otherwise INFO stub.

### Phase 3 – FA-MORT-4 (Escrow documentation linkage)

- **FA-MORT-4 (Escrow disbursement documentation)**  
  - **Model:** `backend/app/models/escrow_document_link.py` (`EscrowDocumentLink`, table `escrow_document_links`).  
  - **Migration:** `backend/alembic/versions/20260129_0003_add_escrow_document_links_table.py`.  
  - **Rule:** `backend/app/services/rules/audit_rules_mixin.py` – `_rule_fa_mort_4_escrow_documentation_link()`; material escrow disbursements (tax/insurance/reserves) require an `EscrowDocumentLink` or supporting document upload (mortgage_statement, tax_bill, insurance_invoice).  
  - **Config:** `system_config` key `fa_mort_4_materiality_threshold` (optional; defaults to `audit_53_materiality_threshold`, e.g. 10000).  
  - **API:** `GET/POST /documents/escrow-links`, `DELETE /documents/escrow-links/{id}` in `backend/app/api/v1/documents.py` for creating and listing escrow–document links.

### Optional seed

- **Script:** `backend/scripts/seed_reconciliation_config.sql`  
  - Seeds `audit48_*` and `forensic_prepaid_rent_material_threshold` in `system_config` (optional; code uses defaults when keys are missing).

### Tests

- **`backend/tests/services/test_covenant_resolver.py`** – covenant resolver (period end date, LTV conversion, DSCR default, config helpers).  
- **`backend/tests/services/test_rrbs_rules.py`** – RRBS-2 bands (parametrized), RRBS-2 result shape, RRBS-3 threshold (PASS/FAIL).

## How to Run

### 1. Migrations (requires PostgreSQL)

Start Postgres (e.g. Docker):

```bash
docker compose up -d postgres
# wait for healthy, then:
cd backend
alembic upgrade head
```

This applies:

- `20260129_0001_add_covenant_thresholds_table.py`
- `20260129_0002_add_rent_roll_renewal_status.py`
- `20260129_0003_add_escrow_document_links_table.py`

**Note:** If you see a revision chain error, ensure `backend/alembic/versions/20260128_0001_add_data_governance_and_gl_tables.py` has `down_revision = "20260125_0002_prop_coords"` (not `20260125_0002_add_property_coordinates`). If the data governance tables already exist, run `alembic stamp 20260128_0001` then `alembic upgrade head` to apply only the new migrations.

### 2. Optional: Seed reconciliation config

After migrations, if you use `system_config` and want to persist or tune the new keys:

```bash
# If psql is installed:
psql -h localhost -p 5433 -U reims -d reims -f backend/scripts/seed_reconciliation_config.sql

# Or via Docker (no local psql):
docker exec -i reims-postgres psql -U reims -d reims < backend/scripts/seed_reconciliation_config.sql
```

Or run the `INSERT ... ON CONFLICT` block from `backend/scripts/seed_reconciliation_config.sql` in your SQL client.

### 3. Run the new tests

From repo root, with backend deps installed (e.g. `pip install -r backend/requirements.txt`):

```bash
cd backend
python -m pytest tests/services/test_covenant_resolver.py tests/services/test_rrbs_rules.py -v -o addopts=
```

(Omit `-o addopts=` if your `pytest.ini` does not force `--cov` or other options that require extra plugins.)

**Troubleshooting:** `ExtractionOrchestrator` is lazy-loaded in `app.services.__init__.py`, so rules-only imports (e.g. covenant_resolver, rent_roll_balance_sheet_rules_mixin) no longer pull in the extraction stack. The new tests should run with standard backend deps (SQLAlchemy, pytest, etc.) without needing `pdfplumber`/`langdetect`/minio. If you see other `ModuleNotFoundError`s when running broader test suites, use a full backend venv with `pip install -r backend/requirements.txt` (Python 3.11 or 3.12 if 3.13 has compatibility issues).

### 4. Run full reconciliation rule tests

With DB and dependencies available:

```bash
cd backend
python -m pytest tests/services/test_reconciliation_rules_mortgage_wc.py -v -o addopts=
```

## Files Touched (summary)

| Area              | Files |
|-------------------|--------|
| RRBS-2 / RRBS-3   | `backend/app/services/rules/rent_roll_balance_sheet_rules_mixin.py` |
| AUDIT-48          | `backend/app/services/rules/audit_rules_mixin.py` |
| Covenant          | `backend/app/models/covenant_threshold.py`, `backend/app/services/rules/covenant_resolver.py`, audit + analytics mixins, `backend/app/services/covenant_compliance_service.py` |
| Covenant DB       | `backend/alembic/versions/20260129_0001_add_covenant_thresholds_table.py` |
| ANALYTICS-8       | `backend/app/models/rent_roll_data.py`, `backend/app/services/rules/analytics_rules_mixin.py`, `backend/alembic/versions/20260129_0002_add_rent_roll_renewal_status.py` |
| FA-MORT-4         | `backend/app/models/escrow_document_link.py`, `backend/app/services/rules/audit_rules_mixin.py`, `backend/app/api/v1/documents.py`, `backend/app/schemas/document.py` |
| Seed              | `backend/scripts/seed_reconciliation_config.sql` (includes `fa_mort_4_materiality_threshold`) |
| Tests             | `backend/tests/services/test_covenant_resolver.py`, `backend/tests/services/test_rrbs_rules.py` |
| Lazy import       | `backend/app/services/__init__.py` (ExtractionOrchestrator lazy-loaded so rules-only tests run without extraction stack) |
