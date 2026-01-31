# Implementation Status

## P1: Idempotency & Observability (DONE)

- **Task idempotency**: `extract_document` uses Redis lock (`extract_lock:{upload_id}`) to prevent duplicate execution; early-exit if already completed.
- **Prometheus metrics**: `GET /api/v1/metrics` exposes Prometheus scrape endpoint.
- **Structlog**: Configured on startup (console, optional file); JSON output with correlation IDs.

## Implementation Complete (Final)

- **Storage decrement**: `decrement_document_count` and `decrement_storage` wired into `delete_all_upload_history` and `document_service` replace flows.
- **Storage accuracy**: `refresh_org_usage` uses `file_size_bytes`; `refresh_all_orgs_usage` + `POST /admin/tenants/refresh-all-usage` for backfill.
- **OpenTelemetry**: Optional tracing via `ENABLE_OTEL_TRACING=true` and `OTEL_EXPORTER_OTLP_ENDPOINT`; `otel_tracing.py` instruments FastAPI.
- **Celery idempotency**: `reprocess_documents_batch` uses Redis lock `reprocess_job:{job_id}`; early exit if job completed/cancelled.
- **Audit logging**: property.created/updated/deleted, financial_period.created, chart_of_accounts created/updated/deleted, batch_job created/cancelled, admin.plan_updated.
- **Frontend**: Administration page – "Organization" tab (members + audit), "Tenant Plans" sub-tab under Billing (set plan/limits per org). Standalone `OrganizationSettings.tsx` for org-only view.

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
