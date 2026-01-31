# REIMS SaaS Hardening & Best-in-Class Upgrade Implementation Plan

> Reference: REIMS SaaS Hardening plan across 8 epics (E0–E8).  
> Sprint 1 focus: JWT correctness, route protection, and org membership enforcement.

## Current State Assessment

### Auth & Identity

- **Session auth** via `get_current_user` (reads `request.session["user_id"]`)
- **JWT auth** via `get_current_user_jwt` — exists; `get_current_organization` now uses `get_current_user_hybrid`
- **Hybrid** `get_current_user_hybrid` — used for org-scoped endpoints
- JWT service: `verify_token`, `get_user_from_token` in `backend/app/core/jwt_auth.py`
- SECRET_KEY validator in `backend/app/core/config/security.py`

### Unprotected / High-Risk Endpoints (addressed)

| Router          | Status                                                                 |
| --------------- | ---------------------------------------------------------------------- |
| **storage**     | Auth + org added; presigned by document_id                             |
| **ocr, pdf**    | Auth added                                                             |
| **bulk_import** | Auth + org added                                                       |
| **websocket**   | Auth handshake (token + org_id in query)                               |
| **tasks**       | Auth added; demo endpoints disabled in production                      |
| **extraction**  | Auth + org audited                                                     |
| **health**      | Public by design (OK)                                                  |

### Tenancy

- `get_current_organization` validates `X-Organization-ID` and membership
- Scoped fetchers in `backend/app/repositories/tenant_scoped.py`
- `organization_id` added to tenant tables (see migrations)
- RLS enabled on properties, financial_periods, document_uploads

### Storage

- Path format: `org/{org_id}/property/{property_id}/period/{period_id}/{doc_type}/{uuid}.pdf`
- Presigned URL via `GET /storage/document/{upload_id}/url` with ownership check
- Server-side only; never accept `object_name` from client

### Migrations & Deployment

- `Base.metadata.create_all()` removed from runtime
- Schema managed by Alembic; `alembic upgrade head` required before app start
- CI job: db-init-smoke (postgres service → alembic upgrade head → smoke test)

---

## Implementation Plan by Epic

### Epic E0 — Repository & Engineering Baseline

- **E0-S1**: `backend/.env.example`, startup validation, SECRET_KEY validator
- **E0-S2**: `backend-ci.yml` — ruff, mypy, pytest; db-init-smoke job

### Epic E1 — Authentication & Authorization (P0)

- **E1-S1**: JWT/config fix, `get_current_user_hybrid` in org resolution
- **E1-S2**: Route protection (storage, ocr, pdf, bulk_import, websocket, tasks)
- **E1-S3**: RBAC via `require_org_role`

### Epic E2 — Multi-Tenancy Enforcement (P0)

- **E2-S1**: Org resolution, `require_organization`
- **E2-S2**: Scoped fetchers (`get_property_for_org`, `get_upload_for_org`, etc.)
- **E2-S3**: `organization_id` on tenant tables (migrations 20260130_0001–0007)
- **E2-S4**: Postgres RLS

### Epic E3 — Storage Security & Upload Pipeline (P0)

- **E3-S1**: Secure object naming
- **E3-S2**: Presigned URL by document_id
- **E3-S3**: Auth on storage
- **E3-S4**: Upload validation (type, size, page count)

### Epic E4 — Migrations-Only Deployment (P1)

- **E4-S1**: No runtime `create_all`
- **E4-S2**: CI db-init job (alembic + smoke test)

### Epic E5 — Job Reliability (P1)

- **E5-S1**: Idempotent ingestion (Redis locks)
- **E5-S2**: Queue separation; DLQ for failed tasks (Redis list `celery:dlq`)
- **E5-S3**: ValidationRun / RuleRun — deterministic, versioned rule execution

### Epic E6 — Observability (P1)

- **E6-S1**: Structlog, request correlation
- **E6-S2**: Prometheus metrics, OpenTelemetry tracing
- **E6-S3**: Rate limiting by org/user

### Epic E7 — SaaS Monetization (P2)

- Plans, quotas, Stripe webhooks

### Epic E8 — Best-in-Class Product (P2)

- **E8-S1**: Explainability UI (rule, evidence, numbers, source link)
- **E8-S2**: Audit trail
- **E8-S3**: Lender-ready export (PDF + Excel with evidence)

---

## Related Docs

- [docs/security/tenant_isolation.md](../security/tenant_isolation.md) — RLS, scoped fetchers, guardrails
- [docs/runbooks/deploy.md](../runbooks/deploy.md) — migrations-only, env validation, health checks
