# Deployment Runbook

## Prerequisites

- **Migrations-only deploy**: Schema is managed by Alembic. `Base.metadata.create_all()` is not used at runtime.
- `alembic upgrade head` must run before starting the app.
- Required env vars in production: `SECRET_KEY`, `POSTGRES_*`, `ENVIRONMENT=production`.

## DB Init

```bash
cd backend
alembic upgrade head
```

For Docker: set `RUN_MIGRATIONS=true` so the entrypoint runs migrations on startup.

## Env Validation

Validate config before deploy:

```bash
ENVIRONMENT=production python backend/scripts/validate_env.py
```

## Health Checks

- `GET /api/v1/health` - API, DB, Redis
- `GET /api/v1/storage/health` - MinIO (public, no auth)
