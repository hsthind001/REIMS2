# Implementation Status

## P1: Idempotency & Observability (DONE)

- **Task idempotency**: `extract_document` uses Redis lock (`extract_lock:{upload_id}`) to prevent duplicate execution; early-exit if already completed.
- **Prometheus metrics**: `GET /api/v1/metrics` exposes Prometheus scrape endpoint.
- **Structlog**: Configured on startup (console, optional file); JSON output with correlation IDs.

## Plan Gaps Implemented (Session 3)

- **E0-S2 mypy**: Fixed syntax errors in bulk_import.py, chart_of_accounts.py, portfolio_analytics.py, vector_store_manager.py, extraction_tasks.py, metrics.py. Mypy runs without parse errors. CI keeps `|| true` until 3000+ type errors are cleaned.
- **E2-S3 anomaly/reconciliation**: Migration 20260130_0009 adds `organization_id` to anomaly_detections, reconciliation_sessions, reconciliation_differences, reconciliation_resolutions (backfilled from document_uploads/properties).
- **E5-S2 Separate queues**: Celery task_routes: extraction (extract_document, recover_stuck), analytics (anomaly, learning, batch, alerts, market_intel), forensic_audit. Workers need `-Q extraction,analytics,forensic_audit,celery`.
- **E5-S1 Unique constraint**: Migration 20260130_0010 adds partial unique index `uq_document_uploads_org_prop_period_doctype_filehash` on (organization_id, property_id, period_id, document_type, file_hash) WHERE file_hash IS NOT NULL.

---

## Plan Gaps Implemented (Latest Session 2)

- **Tasks router auth (E1-S2)**: Demo endpoints (send-email, process-data, add-numbers, long-running) and GET /tasks, GET /tasks/{id}, DELETE /tasks/{id} now require `get_current_user_hybrid`. Demo tasks return 404 in production.
- **E2-S3 tenant tables**: Migration 20260130_0007 adds `organization_id` to validation_results, balance_sheet_data, income_statement_data, cash_flow_data, rent_roll_data (backfilled from document_uploads/properties).
- **E4-S2 CI DB init**: New `db-init-smoke` job in backend-ci.yml — postgres service, alembic upgrade head, DB smoke test.
- **E5-S2 DLQ**: `task_failure` signal records failed task metadata to Redis list `celery:dlq` (last 1000 entries).
- **E5-S3 RuleRun**: `validation_runs` table and `validation_run_id` on validation_results; ValidationService creates run records with rules_version_hash, timestamps.
- **Docs**: `docs/agile/REIMS_SaaS_Hardening_Plan.md` created.
- **CI mypy**: Kept soft fail (`|| true`) — remove after type cleanup to enforce.

---

## Plan Gaps Implemented (Latest)

- **WebSocket auth (E1-S2)**: Token + org_id required in query params (`?token=&org_id=`). Both `/ws/extraction-status/{upload_id}` and `/ws/batch-job/{job_id}` validate JWT and org membership before accept. Frontend `wsAuth.ts` and hooks pass auth params.
- **test_tenant_isolation.py**: Unit test for `get_current_organization` 403 on non-member org; integration tests for 401 on unauthenticated storage/properties.
- **Mypy (E0-S2)**: Added to backend-ci.yml; runs on `backend/app` (soft fail during cleanup).
- **Upload validation (E3-S4)**: Max 500 pages enforced via pypdf; file type, size (50MB), magic bytes already present.
- **Rate limit by org/user (E6-S3)**: `get_rate_limit_key` uses X-Organization-ID or Bearer token when present; applied to documents upload and bulk_import.
- **organization_id on tenant tables (E2-S3)**: Added to `batch_reprocessing_jobs`, `extraction_logs` (migrations 20260130_0005, 0006).
- **E8-S1 Explainability**: RuleFailureDetail shows rule code, source/target documents, View Source PDF button.
- **E8-S3 Lender export**: Forensic audit export already includes PDF + Excel with source_document, target_document (evidence references).

---

## Implementation Complete (Final)

- **Storage decrement**: `decrement_document_count` and `decrement_storage` wired into `delete_all_upload_history` and `document_service` replace flows.
- **Storage accuracy**: `refresh_org_usage` uses `file_size_bytes`; `refresh_all_orgs_usage` + `POST /admin/tenants/refresh-all-usage` for backfill.
- **OpenTelemetry**: Optional tracing via `ENABLE_OTEL_TRACING=true` and `OTEL_EXPORTER_OTLP_ENDPOINT`; `otel_tracing.py` instruments FastAPI.
- **Celery idempotency**: Reprocess, anomaly nightly, forensic audit, alert backfill; also: `evaluate_alerts_for_property`, `escalate_overdue_alerts`, `update_alert_priorities`, `cleanup_resolved_alerts`, `monitor_all_properties`, `schedule_recurring_audits`, `cleanup_old_audit_results` (Redis locks).
- **Audit logging**: property, financial_period, chart_of_accounts, batch_job, admin.plan_updated; alert_rule; anomaly_threshold; bulk_import; extraction; document.downloaded; admin.audit_log_viewed; org.audit_log_viewed.
- **Frontend**: Administration – "Organization" tab with Add Member (email/username search via GET /organization/members/search), "Tenant Plans" sub-tab.
- **User search by email**: Add member accepts `email` or `user_id`; GET /organization/members/search?email= for typeahead.
- **OpenTelemetry**: FastAPI + SQLAlchemy in main app; Celery + SQLAlchemy in workers via worker_process_init.

---

## P2: Plans, Billing, Admin (DONE)

- **Plans & quotas**: Migration `20260130_0003` adds `plan_id`, `documents_limit`, `storage_limit_gb`, `documents_used`, `storage_used_bytes` to organizations. `QuotaService` enforces limits on upload; increment/decrement on success/delete.
- **Billing webhooks**: Stripe webhook handles `invoice.paid`, `invoice.payment_failed`; syncs `subscription_status` (past_due on failure, active on payment).
- **Admin control plane**: `org_members.py` – list/add/remove/update-role members; `audit_log` table + `AuditLog` model; org admins get `GET /organization/members/audit`; superusers get `GET /admin/audit-log`.
- **Admin plan management**: `PATCH /admin/tenants/{org_id}/plan` to set plan_id, documents_limit, storage_limit_gb; `POST /admin/tenants/{org_id}/refresh-usage` to recalc usage.
- **Audit logging**: document.uploaded, property.created, member.added/removed/role_updated.

---

## RBAC (E1-S3)

Org role enforcement (`require_org_role`) applied to:
- **admin**: properties (create/update/delete), financial_periods (create), chart_of_accounts (create/update/delete), anomaly_thresholds (create/update/delete/set_default), alert_rules (create/update/delete/activate/deactivate/create_from_template), documents (delete_filtered, escrow links)
- **editor**: documents (upload), bulk_import (all), batch_reprocessing (create), alert_rules (test)
- **superuser**: documents (delete_all_upload_history, delete_all_anomalies_warnings_alerts)
