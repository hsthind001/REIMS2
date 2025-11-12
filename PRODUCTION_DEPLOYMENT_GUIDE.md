# REIMS 2.0 - Production Deployment Guide

**Version**: 2.0.0  
**Status**: Ready for Production  
**Last Updated**: November 11, 2025

---

## Prerequisites

✅ All 8 sprints complete  
✅ All services implemented  
✅ All database migrations created  
✅ All tests passing

---

## Step 1: Environment Configuration

### 1.1 Copy Production Template

```bash
cp .env.production.template .env.production
```

### 1.2 Update Critical Values

Edit `.env.production` and update:

**MUST CHANGE**:
- `POSTGRES_PASSWORD` - Secure database password
- `MINIO_SECRET_KEY` - Secure MinIO password  
- `SECRET_KEY` - Long random string for JWT
- `SLACK_WEBHOOK_URL` - Your Slack webhook (if using)
- `ALERT_EMAIL_TO` - Email addresses for alerts

**OPTIONAL (for integrations)**:
- `QUICKBOOKS_CLIENT_ID` / `QUICKBOOKS_CLIENT_SECRET`
- `YARDI_API_KEY` / `YARDI_PASSWORD`

### 1.3 Update docker-compose.yml

```bash
# Use .env.production instead of .env
# Update docker-compose.yml to use env_file: .env.production
```

---

## Step 2: Database Setup

### 2.1 Run All Migrations

```bash
# Stop services
docker compose down

# Start database only
docker compose up -d postgres

# Wait for database
sleep 10

# Run migrations
docker compose run --rm backend alembic upgrade head

# Verify tables (should see 38+ tables)
docker exec reims-postgres psql -U reims -d reims -c "\dt" | wc -l
```

### 2.2 Verify Critical Tables

```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT tablename FROM pg_tables 
WHERE schemaname='public' 
AND tablename IN (
  'extraction_field_metadata',
  'anomaly_detections',
  'alert_rules',
  'alerts',
  'roles',
  'permissions',
  'api_keys',
  'webhooks',
  'notifications'
);
"
```

Expected: All 9 tables present

---

## Step 3: Service Startup

### 3.1 Build Images

```bash
# Rebuild all images with production code
docker compose build --no-cache
```

### 3.2 Start All Services

```bash
docker compose up -d
```

### 3.3 Verify Health

```bash
# Check all services running
docker compose ps

# Expected: All services "Up" and healthy

# Test backend API
curl http://localhost:8000/api/v1/health

# Expected: {"status":"healthy","api":"ok","database":"connected","redis":"connected"}

# Test frontend
curl http://localhost:5173

# Expected: HTML response
```

---

## Step 4: AI Model Setup

### 4.1 Download AI Models (First Time Only)

```bash
# Trigger first extraction to download LayoutLMv3 (~500MB)
# This will take 1-2 minutes

# Monitor download progress
docker compose logs -f backend | grep -i "download\|layoutlm"
```

### 4.2 Verify Models Loaded

```bash
docker exec reims-backend python3 -c "
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
print('LayoutLMv3: OK')
import easyocr
reader = easyocr.Reader(['en'])
print('EasyOCR: OK')
"
```

---

## Step 5: Configure Automated Backups

### 5.1 Setup Cron Job

```bash
bash scripts/setup-backup-cron.sh
```

Choose: **Daily at 2:00 AM**

### 5.2 Test Backup

```bash
# Run manual backup
bash scripts/backup-volumes.sh

# Check backup files created
ls -lh backups/

# Expected:
# postgres_YYYYMMDD_HHMMSS.sql.gz
# minio_YYYYMMDD_HHMMSS/
```

### 5.3 Test Restore (Optional, on test system only!)

```bash
# NEVER run this on production without backup!
bash scripts/restore-volumes.sh
```

---

## Step 6: Configure Alerts (Optional)

### 6.1 Email Alerts (if using)

If using Postal email server:

```bash
# Add Postal container to docker-compose.yml
# Configure SMTP_HOST=postal in .env.production
```

If using external SMTP (Gmail, SendGrid, etc.):

```bash
# Update .env.production with external SMTP settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 6.2 Slack Alerts (if using)

1. Create Slack Incoming Webhook:
   - Go to https://api.slack.com/apps
   - Create app → Incoming Webhooks
   - Copy webhook URL

2. Update `.env.production`:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   SLACK_ENABLED=true
   ```

3. Test:
   ```bash
   curl -X POST http://localhost:8000/api/v1/alerts/test \
     -H "Content-Type: application/json" \
     -d '{"channels": ["slack"]}'
   ```

---

## Step 7: Run End-to-End Test

### 7.1 Test Extraction Workflow

```bash
# 1. Upload document via UI (http://localhost:5173)
# 2. Navigate to Documents page
# 3. Click "Extract" on uploaded document
# 4. Monitor extraction progress
# 5. Verify results display with confidence indicators
```

### 7.2 Test Ensemble Voting

```bash
# After extraction completes:
# 1. Check extraction_field_metadata table
# 2. Verify multiple engines ran (engine_name column)
# 3. Check confidence scores
# 4. Verify ensemble resolution_method

docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
  extraction_engine,
  COUNT(*) as field_count,
  AVG(confidence_score) as avg_confidence
FROM extraction_field_metadata
GROUP BY extraction_engine
ORDER BY avg_confidence DESC;
"
```

### 7.3 Test Anomaly Detection

```bash
# Trigger anomaly detection
curl -X POST http://localhost:8000/api/v1/anomalies/detect \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "table_name": "balance_sheet",
    "lookback_months": 12,
    "method": "statistical"
  }'
```

### 7.4 Test Caching

```bash
# Extract same document twice
# Second extraction should be much faster (<5 seconds vs 30+ seconds)

# Check cache statistics
curl http://localhost:8000/api/v1/cache/stats
```

---

## Step 8: Production Hardening (Optional)

### 8.1 Enable HTTPS

```bash
# Add SSL certificates to nginx/traefik reverse proxy
# Update BACKEND_CORS_ORIGINS to include https://
```

### 8.2 Database Connection Pooling

```bash
# Already configured in SQLAlchemy
# Default: pool_size=5, max_overflow=10
```

### 8.3 Rate Limiting

```bash
# Already implemented in PublicAPIService
# Default: 100 requests/hour per API key
```

### 8.4 Monitoring Setup

```bash
# Consider adding:
# - Prometheus for metrics
# - Grafana for dashboards
# - Sentry for error tracking
```

---

## Step 9: Validation Checklist

Before going live, verify:

- ✅ All Docker services healthy (`docker compose ps`)
- ✅ Database migrations applied (`alembic current`)
- ✅ Backend API responding (`curl localhost:8000/api/v1/health`)
- ✅ Frontend accessible (`curl localhost:5173`)
- ✅ AI models downloaded (check `/app/.cache/huggingface/`)
- ✅ Backups configured (`crontab -l`)
- ✅ Alerts tested (email/Slack)
- ✅ End-to-end extraction works
- ✅ Ensemble voting operational
- ✅ Anomaly detection functional
- ✅ RBAC permissions working
- ✅ All tests passing (`pytest`)

---

## Step 10: Go Live!

### 10.1 Start Production Services

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 10.2 Monitor Logs

```bash
# Watch for any errors
docker compose logs -f backend celery-worker

# Monitor resource usage
docker stats
```

### 10.3 Celebrate! 🎉

```bash
echo "REIMS 2.0 is now LIVE and world-class! 🏆"
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker compose logs backend --tail=100

# Common issues:
# - Import errors → Check service dependencies
# - Database connection → Check POSTGRES_* env vars
# - Redis connection → Check REDIS_* env vars
```

### AI Models Won't Load

```bash
# Manual download
docker exec -it reims-backend bash
python3 -c "from transformers import LayoutLMv3Processor; LayoutLMv3Processor.from_pretrained('microsoft/layoutlmv3-base')"
exit
```

### Extraction Fails

```bash
# Check Celery worker
docker compose logs celery-worker --tail=100

# Check extraction logs table
docker exec reims-postgres psql -U reims -d reims -c "
SELECT * FROM extraction_logs 
ORDER BY created_at DESC 
LIMIT 10;
"
```

---

## Maintenance

### Daily

- Monitor `docker stats` for resource usage
- Check `docker compose logs` for errors
- Verify backups ran (`ls -lh backups/`)

### Weekly

- Review anomaly detections (`/anomalies dashboard`)
- Check alert delivery rates
- Review cache hit rates
- Monitor model performance

### Monthly

- Update dependencies (`pip list --outdated`)
- Review user access logs
- Test disaster recovery
- Archive old backups

---

## Support

For issues or questions:
- Check documentation in `docs/` directory
- Review service logs
- Check Task Master tasks for implementation details
- Refer to PRD files in `/PRD files - 09-11-2025/`

---

**Deployment Complete!** 🚀  
**REIMS 2.0 is now world-class!** 🏆

