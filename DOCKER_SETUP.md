# REIMS2 Docker Setup Guide
## Cash Flow Template v1.0 Enabled

This document provides instructions for running REIMS2 with Docker, including the newly implemented Cash Flow Statement Template v1.0.

---

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd REIMS2

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

---

## Services

### Core Services

1. **PostgreSQL (port 5432)**
   - Database: `reims`
   - User: `reims`
   - Password: `reims`
   - Includes all Cash Flow Template v1.0 tables

2. **Redis (port 6379)**
   - Message broker for Celery
   - RedisInsight GUI: http://localhost:8001

3. **MinIO (ports 9000, 9001)**
   - S3-compatible object storage
   - API: http://localhost:9000
   - Console: http://localhost:9001
   - Credentials: minioadmin / minioadmin

### Application Services

4. **Backend - FastAPI (port 8000)**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Automatic database migrations on startup
   - Automatic database seeding (chart of accounts, lenders)

5. **Celery Worker**
   - Background task processing for PDF extraction
   - Handles async document processing
   - Supports Cash Flow Template v1.0 extraction

6. **Flower (port 5555)**
   - Celery monitoring UI
   - Dashboard: http://localhost:5555

7. **pgAdmin (port 5050)**
   - PostgreSQL GUI
   - URL: http://localhost:5050
   - Credentials: admin@pgadmin.com / admin

8. **Frontend - React (port 5173)**
   - Development server with hot reload
   - URL: http://localhost:5173

---

## Cash Flow Template v1.0 Features

The Docker setup is configured to support all Cash Flow Template v1.0 features:

### Database Schema
- **cash_flow_headers**: Summary metrics and header information
  - Total Income, Expenses, NOI, Net Income, Cash Flow
  - Percentages and confidence scores
  - Beginning/Ending cash balances

- **cash_flow_adjustments**: 30+ adjustment types
  - AR Changes, Property & Equipment, Depreciation
  - Escrow Accounts, Loan Costs, Prepaid Items
  - Accounts Payable, Inter-Property Transfers, Distributions

- **cash_account_reconciliations**: Cash account tracking
  - Beginning/Ending balances with differences
  - Account type classification (operating, escrow)
  - Negative balance flagging

### Extraction Capabilities
- **100+ categories** across 6 sections
- **Multi-column extraction**: Period/YTD amounts and percentages
- **Section detection**: Income, Operating Expense, Additional Expense, Performance Metrics, Adjustments, Cash Reconciliation
- **Hierarchical linking**: Detail → Subtotal → Total relationships
- **Entity extraction**: Property names, lender names

### Validation Rules (11 rules)
1. Total Income = sum of income items
2. Base Rentals 70-85% of Total Income (warning)
3. Total Expenses = Operating + Additional
4. Expense Subtotals validation (5 subtotals)
5. NOI = Total Income - Total Expenses
6. NOI 60-80% of Total Income (warning)
7. NOI > 0 for viable properties (warning)
8. Net Income = NOI - (Interest + Depreciation + Amortization)
9. Cash Flow = Net Income + Total Adjustments
10. Cash Account Differences = Ending - Beginning
11. Total Cash = sum of all account ending balances

---

## Database Migrations

### Automatic Migration (Default)

On startup, the backend service automatically:
1. Waits for PostgreSQL to be ready
2. Runs `alembic upgrade heads` (or `alembic upgrade head` as fallback)
3. Seeds the database if not already seeded

### Manual Migration

```bash
# Enter backend container
docker-compose exec backend bash

# Run migrations manually
cd /app
alembic upgrade head

# Check current migration status
alembic current

# View migration history
alembic history

# Downgrade one migration
alembic downgrade -1
```

### Migration Files

All migrations are in `/backend/alembic/versions/`:

- `20251103_1259_*` - Initial 13 tables
- `20251103_1317_*` - Check constraints
- `20251104_0800_*` - Sample properties seed
- `20251104_1008_*` - Rent roll enhancements
- `20251104_1203_*` - Balance sheet template fields
- `20251104_1205_*` - Income statement template fields
- `20251104_1400_*` - Chart of accounts seed
- `20251104_1659_*` - Cash flow data enhancements
- `20251104_2128_*` - **Cash flow headers, adjustments, reconciliations** ⭐ NEW

---

## Environment Variables

### Backend Service

Key environment variables (see `docker-compose.yml` for full list):

```yaml
# Database
POSTGRES_USER: reims
POSTGRES_PASSWORD: reims
POSTGRES_SERVER: postgres
POSTGRES_PORT: 5432
POSTGRES_DB: reims

# Redis
REDIS_HOST: redis
REDIS_PORT: 6379

# MinIO
MINIO_ENDPOINT: minio:9000
MINIO_ACCESS_KEY: minioadmin
MINIO_SECRET_KEY: minioadmin
MINIO_BUCKET_NAME: reims

# Database Initialization
RUN_MIGRATIONS: "true"
SEED_DATABASE: "true"
```

---

## Development Workflow

### 1. Start Services

```bash
docker-compose up -d
```

### 2. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### 3. Access Services

- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **pgAdmin**: http://localhost:5050
- **Flower**: http://localhost:5555
- **RedisInsight**: http://localhost:8001
- **MinIO Console**: http://localhost:9001

### 4. Test Cash Flow Extraction

```bash
# Upload a Cash Flow PDF via Swagger UI
# 1. Navigate to http://localhost:8000/docs
# 2. Use POST /api/v1/documents/upload
# 3. Select document_type: CASH_FLOW
# 4. Choose property and period
# 5. Upload PDF file
# 6. Monitor extraction in Flower (http://localhost:5555)
```

### 5. Database Access

```bash
# psql via Docker
docker-compose exec postgres psql -U reims -d reims

# Query Cash Flow data
SELECT COUNT(*) FROM cash_flow_headers;
SELECT COUNT(*) FROM cash_flow_data;
SELECT COUNT(*) FROM cash_flow_adjustments;
SELECT COUNT(*) FROM cash_account_reconciliations;
```

---

## Troubleshooting

### Migration Issues

**Problem**: "Multiple head revisions"
```bash
# Solution: Run merge command
docker-compose exec backend bash
cd /app
alembic merge heads -m "Merge heads"
alembic upgrade head
```

**Problem**: Migration fails
```bash
# Check current state
docker-compose exec backend alembic current

# View pending migrations
docker-compose exec backend alembic show head

# Manually run migrations
docker-compose exec backend alembic upgrade head
```

### Celery Worker Issues

**Problem**: Worker not processing tasks
```bash
# Restart worker
docker-compose restart celery-worker

# Check worker logs
docker-compose logs -f celery-worker

# Check Flower UI
# Navigate to http://localhost:5555
```

### Database Reset

**Problem**: Need to start fresh
```bash
# ⚠️ WARNING: This deletes all data!

# Stop all services
docker-compose down

# Remove volumes (deletes all data)
docker-compose down -v

# Rebuild and start
docker-compose up -d --build
```

### Port Conflicts

**Problem**: Port already in use
```bash
# Check what's using the port
sudo lsof -i :8000

# Either stop the process or change port in docker-compose.yml
```

---

## Building from Scratch

### 1. Build Base Image (Optional)

```bash
cd backend
docker build -f Dockerfile.base -t reims-base:latest .
```

### 2. Build and Start All Services

```bash
docker-compose up -d --build
```

### 3. Verify All Services Running

```bash
docker-compose ps
```

Expected output:
```
NAME                  STATUS              PORTS
reims-backend         Up                  0.0.0.0:8000->8000/tcp
reims-celery-worker   Up                  
reims-flower          Up                  0.0.0.0:5555->5555/tcp
reims-frontend        Up                  0.0.0.0:5173->5173/tcp
reims-minio           Up                  0.0.0.0:9000-9001->9000-9001/tcp
reims-pgadmin         Up                  0.0.0.0:5050->80/tcp
reims-postgres        Up (healthy)        0.0.0.0:5432->5432/tcp
reims-redis           Up (healthy)        0.0.0.0:6379->6379/tcp, 0.0.0.0:8001->8001/tcp
```

---

## Production Deployment

### Environment Variables

For production, update these in `docker-compose.yml` or use a `.env` file:

```bash
# Strong passwords
POSTGRES_PASSWORD: <strong-password>
MINIO_ROOT_PASSWORD: <strong-password>
PGADMIN_DEFAULT_PASSWORD: <strong-password>

# Disable debug mode
DEBUG: "false"

# Secure CORS
BACKEND_CORS_ORIGINS: https://yourdomain.com

# SSL for MinIO
MINIO_SECURE: "true"
```

### SSL/TLS

Add reverse proxy (nginx/traefik) in front of services:
- Backend: HTTPS on 443
- Frontend: HTTPS on 443
- MinIO: HTTPS on 443 (separate subdomain)

### Scaling

Scale Celery workers:
```bash
docker-compose up -d --scale celery-worker=4
```

---

## Data Backup

### Backup Database

```bash
# Create backup
docker-compose exec postgres pg_dump -U reims reims > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T postgres psql -U reims reims < backup_20251104.sql
```

### Backup MinIO

```bash
# Export MinIO data
docker-compose exec minio mc mirror local/reims /backup/reims

# Or use volume backup
docker run --rm -v reims_minio-data:/data -v $(pwd):/backup alpine tar czf /backup/minio-backup.tar.gz /data
```

---

## Performance Tuning

### PostgreSQL

Edit `docker-compose.yml` to add:
```yaml
postgres:
  environment:
    # Increase shared buffers
    POSTGRES_INITDB_ARGS: "-c shared_buffers=256MB -c max_connections=200"
```

### Celery

Adjust worker concurrency:
```yaml
celery-worker:
  command: celery -A celery_worker.celery_app worker --loglevel=info --concurrency=8
```

### Redis

Increase memory limit:
```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

---

## Monitoring

### Health Checks

All services have health checks configured. Check status:
```bash
docker-compose ps
```

### Logs

```bash
# All logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Service-specific
docker-compose logs backend
```

### Metrics

- **Flower**: http://localhost:5555 - Celery task metrics
- **RedisInsight**: http://localhost:8001 - Redis metrics
- **pgAdmin**: http://localhost:5050 - Database queries and stats

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review this documentation
3. Check `REIMS2_Build_Till_Now.md` for system details
4. Check `CASH_FLOW_TEMPLATE_IMPLEMENTATION.md` for Cash Flow details

---

**Last Updated**: November 4, 2025  
**Version**: Cash Flow Template v1.0  
**Status**: Production Ready

