# PostgreSQL Database Quick Reference

## 🚀 Quick Access

### Database Connection
```bash
# Access database CLI
docker exec -it reims-postgres psql -U reims -d reims

# Via pgAdmin (Web UI)
# http://localhost:5050
# Email: admin@pgadmin.com
# Password: admin
```

### Connection Info
| Parameter | Value |
|-----------|-------|
| **Host** | localhost (or `postgres` inside Docker network) |
| **Port** | 5433 (external), 5432 (internal) |
| **Database** | reims |
| **User** | reims |
| **Password** | reims |
| **Volume** | reims_postgres-data |

## 📊 Database Status

### Quick Checks
```bash
# Check if running
docker ps | grep reims-postgres

# Check database size
docker exec reims-postgres psql -U reims -d reims -c "\l+"

# Count tables
docker exec reims-postgres psql -U reims -d reims -c "\dt" | wc -l

# Check chart of accounts
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM chart_of_accounts;"

# Check current migration
docker exec reims-backend alembic current
```

## 💾 Backup & Restore

### Quick Backup
```bash
# Run automated backup script
./backup-database.sh

# Or manual backup
docker exec reims-postgres pg_dump -U reims -d reims \
  | gzip > ~/backups/reims-backup-$(date +%Y%m%d).sql.gz
```

### Quick Restore
```bash
# Stop services
docker compose stop backend celery-worker

# Restore database
gunzip < ~/backups/reims-backup-20251107.sql.gz \
  | docker exec -i reims-postgres psql -U reims -d reims

# Restart
docker compose up -d
```

## 🧪 Test Persistence

```bash
# Run automated test
./test_database_persistence.sh
```

## 🔍 Common Queries

### Check Table Sizes
```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size,
    n_live_tup AS rows
FROM pg_tables t
LEFT JOIN pg_stat_user_tables s ON t.tablename = s.relname
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size('public.'||tablename) DESC
LIMIT 10;
"
```

### Check Data Counts
```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    'users' as table_name, COUNT(*) as rows FROM users
UNION ALL
SELECT 'properties', COUNT(*) FROM properties
UNION ALL
SELECT 'chart_of_accounts', COUNT(*) FROM chart_of_accounts
UNION ALL
SELECT 'lenders', COUNT(*) FROM lenders
UNION ALL
SELECT 'balance_sheet_data', COUNT(*) FROM balance_sheet_data
UNION ALL
SELECT 'income_statement_data', COUNT(*) FROM income_statement_data;
"
```

### List All Tables
```bash
docker exec reims-postgres psql -U reims -d reims -c "\dt"
```

## 🔧 Migrations

### Check Migration Status
```bash
# Current version
docker exec reims-backend alembic current

# Show history
docker exec reims-backend alembic history

# Show all revisions
docker exec reims-backend alembic show
```

### Apply Migrations
```bash
# Upgrade to latest
docker exec reims-backend alembic upgrade head

# Downgrade one version
docker exec reims-backend alembic downgrade -1
```

### Create New Migration
```bash
# Auto-generate from models
docker exec reims-backend alembic revision --autogenerate -m "description"

# Create blank migration
docker exec reims-backend alembic revision -m "description"
```

## 📦 Volume Management

### Check Volume
```bash
# List volumes
docker volume ls | grep postgres

# Inspect volume
docker volume inspect reims_postgres-data

# Check volume size
docker run --rm -v reims_postgres-data:/data ubuntu du -sh /data
```

### Backup Volume
```bash
# Stop services
docker compose stop postgres backend celery-worker

# Backup entire volume
docker run --rm \
  -v reims_postgres-data:/data:ro \
  -v ~/backups:/backup \
  ubuntu tar czf /backup/postgres-volume-$(date +%Y%m%d).tar.gz -C /data .

# Restart
docker compose up -d
```

## 🐛 Troubleshooting

### Database Won't Start
```bash
# Check logs
docker compose logs postgres

# Check volume permissions
docker run --rm -v reims_postgres-data:/data ubuntu ls -la /data
```

### Reset Database (⚠️ DESTRUCTIVE)
```bash
# Stop all services
docker compose down

# Remove volume
docker volume rm reims_postgres-data

# Restart (will reinitialize)
docker compose up -d
```

### Fix Permissions
```bash
docker run --rm -v reims_postgres-data:/data ubuntu chown -R 999:999 /data
docker compose restart postgres
```

## ⚠️ Important Notes

### Data Persists ✅
- Container restarts
- `docker compose down` + `up`
- System reboots
- Container recreation

### Data is Deleted ❌
- `docker compose down -v` (with `-v` flag)
- `docker volume rm reims_postgres-data`
- `docker system prune --volumes`

## 📚 Database Schema

### Current Tables (13+)
1. users
2. properties
3. financial_periods
4. document_uploads
5. chart_of_accounts (300+ rows)
6. balance_sheet_data
7. income_statement_data
8. cash_flow_data
9. cash_flow_headers
10. cash_flow_adjustments
11. cash_account_reconciliations
12. rent_roll_data
13. validation_rules
14. validation_results
15. extraction_templates
16. extraction_logs
17. audit_trail
18. financial_metrics
19. lenders (30+ rows)

### Key Seeded Data
- **Chart of Accounts:** 300+ entries
- **Lenders:** 30+ entries
- **Validation Rules:** Multiple rules
- **Extraction Templates:** Document parsers

## 🔗 Full Documentation

- **[DATABASE_PERSISTENCE.md](DATABASE_PERSISTENCE.md)** - Complete guide (400+ lines)
- **[DOCKER_COMPOSE_README.md](DOCKER_COMPOSE_README.md)** - Stack overview
- **[backend/README.md](backend/README.md)** - Backend docs

## ⚡ Quick Commands

```bash
# Start everything
docker compose up -d

# Stop everything (keeps data)
docker compose down

# View logs
docker compose logs -f postgres

# Backup database
./backup-database.sh

# Test persistence
./test_database_persistence.sh

# Access database
docker exec -it reims-postgres psql -U reims -d reims

# Check migration
docker exec reims-backend alembic current
```

---

**Status:** ✅ Production Ready  
**Last Updated:** November 7, 2025

