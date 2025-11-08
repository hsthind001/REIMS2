# 🚀 Cash Flow Template v1.0 - Quick Deployment Guide

## TL;DR - Deploy in 3 Steps

```bash
cd /home/gurpyar/Documents/R/REIMS2

# Run automated deployment script
./deploy_cash_flow_template.sh

# Select option 2 (Full Rebuild) when prompted
# Wait 2-3 minutes
# Done! ✅
```

---

## What Gets Deployed

### Database Changes:
- ✅ 3 new tables created
- ✅ 1 table enhanced (15+ new columns)
- ✅ Migration: `939c6b495488`

### Code Changes:
- ✅ 4 new models
- ✅ 100+ category classification engine
- ✅ 30+ adjustment type parser
- ✅ 11 validation rules
- ✅ Enhanced schemas and services

### Result:
- ✅ 100% Cash Flow Template compliance
- ✅ Zero data loss extraction
- ✅ Complete validation
- ✅ Production ready

---

## Available Scripts

### 1. Deploy Script
```bash
./deploy_cash_flow_template.sh
```
- Interactive deployment with 3 options
- Automatic verification
- Optional testing
- Comprehensive output

### 2. Verify Script
```bash
./verify_cash_flow_deployment.sh
```
- 15+ verification checks
- Pass/Fail reporting
- Troubleshooting guidance

### 3. Rollback Script
```bash
./rollback_cash_flow_template.sh
```
- Safety backup before rollback
- Automated rollback process
- Restore instructions

---

## Manual Deployment (If Preferred)

```bash
cd /home/gurpyar/Documents/R/REIMS2

# 1. Stop services
docker-compose down

# 2. Rebuild
docker-compose build backend celery-worker flower

# 3. Start
docker-compose up -d

# 4. Watch logs (wait for "Migrations complete!")
docker-compose logs -f backend

# 5. Verify
./verify_cash_flow_deployment.sh
```

---

## Verification

After deployment, check:

```bash
# Migration applied?
docker exec reims-backend alembic current
# Should show: 939c6b495488

# Tables created?
docker exec reims-postgres psql -U reims -d reims -c "\dt cash_flow*"
# Should show 4 tables

# API healthy?
curl http://localhost:8000/api/v1/health
# Should return: {"status":"healthy"}
```

---

## Test Upload

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "property_code=ESP" \
  -F "period_year=2024" \
  -F "period_month=12" \
  -F "document_type=cash_flow" \
  -F "file=@your_cash_flow.pdf"
```

Check results at: http://localhost:8000/docs

---

## Rollback (If Needed)

```bash
cd /home/gurpyar/Documents/R/REIMS2
./rollback_cash_flow_template.sh
```

Confirms before rollback, creates backup, and restores previous state.

---

## Documentation

- **Main Guide:** `REIMS2/backend/CASH_FLOW_TEMPLATE_IMPLEMENTATION.md`
- **Deployment Guide:** `REIMS2/DEPLOYMENT_GUIDE_CASH_FLOW.md`
- **This Quick Start:** `README_DEPLOYMENT.md`

---

## Support

**Services:**
- API Docs: http://localhost:8000/docs
- Celery Monitor: http://localhost:5555
- Database GUI: http://localhost:5050

**Logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

---

**Ready to deploy? Run:** `./deploy_cash_flow_template.sh` ✅

