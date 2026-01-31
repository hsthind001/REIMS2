# Tenant Isolation

## Storage Security (E3-S2)

- **Presigned URLs only by DB record**: Use `GET /api/v1/storage/document/{upload_id}/url` for documents. Path-based `/storage/url/{path}` requires a matching `DocumentUpload` record.
- **Download/info/delete**: All path-based storage endpoints validate ownership via `get_upload_by_path_for_org`.

Multi-tenant security for REIMS SaaS. Ensures organization-level data isolation.

## Guardrails

### Endpoint Checklist

When editing any backend endpoint that touches tenant data:

1. **Auth**: Must include `Depends(get_current_user_hybrid)` (or `get_current_user` for session-only).
2. **Org**: Must include `Depends(get_current_organization)` for tenant data.
3. **Ownership**: Verify property/upload/period belongs to org before returning data.
4. **Storage**: Never accept raw object key for storage access; use `document_id` and verify ownership via DB.

### Scoped Fetch Helpers

Use `app.repositories.tenant_scoped` instead of direct `session.query()`:

| Helper | Purpose |
|--------|---------|
| `get_property_for_org(db, org_id, property_id)` | Property by ID |
| `get_property_by_code_for_org(db, org_id, property_code)` | Property by code |
| `get_upload_for_org(db, org_id, upload_id)` | DocumentUpload by ID |
| `get_upload_by_path_for_org(db, org_id, file_path)` | DocumentUpload by MinIO path (for URL validation) |
| `get_period_for_org(db, org_id, period_id)` | FinancialPeriod by ID |
| `get_workflow_lock_for_org(db, org_id, lock_id)` | WorkflowLock by ID |
| `get_reconciliation_session_for_org(db, org_id, session_id)` | ReconciliationSession by ID |
| `get_forensic_reconciliation_session_for_org(db, org_id, session_id)` | ForensicReconciliationSession by ID |
| `get_forensic_match_for_org(db, org_id, match_id)` | ForensicMatch by ID (via session) |
| `get_forensic_discrepancy_for_org(db, org_id, discrepancy_id)` | ForensicDiscrepancy by ID (via session) |
| `get_anomaly_for_org(db, org_id, anomaly_id)` | AnomalyDetection by ID (via document/property) |

These helpers join through `Property.organization_id` and return `None` if the resource does not belong to the org.

## RLS (Defense-in-Depth)

Migration `20260130_0002_add_rls_policies` enables Row Level Security on:
- `properties`
- `financial_periods`
- `document_uploads`

**Activation:** `get_current_organization` automatically sets `app.current_organization_id` via `set_config()` when the org is resolved. Any route that uses `Depends(get_current_organization)` will have RLS applied for that request's DB usage.

When not set (e.g., routes without org context), policies allow all rows (backward compatibility).
