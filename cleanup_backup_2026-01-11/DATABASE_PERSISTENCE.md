# PostgreSQL Database Persistence Guide

## ✅ Database Persistence is Fully Configured

Your PostgreSQL database schema, tables, and all data are persistent and will save permanently across all container operations.

## 🎯 What's Configured

### 1. Named Volume for Data Persistence
```yaml
volumes:
  postgres-data:
    driver: local
```

PostgreSQL stores all data in the `postgres-data` volume:
- All database schemas
- All tables and indexes
- All data rows
- All user permissions
- Transaction logs (WAL)

### 2. PGDATA Configuration
```yaml
environment:
  PGDATA: /var/lib/postgresql/data/pgdata
volumes:
  - postgres-data:/var/lib/postgresql/data
```

This ensures PostgreSQL stores data in the persistent volume with proper subdirectory structure.

### 3. Automatic Database Initialization
The `db-init` service handles:
- ✅ Creating all base tables (SQLAlchemy models)
- ✅ Running 19 Alembic migrations
- ✅ Seeding 300+ chart of accounts entries
- ✅ Seeding 30+ lenders
- ✅ Seeding validation rules
- ✅ Seeding extraction templates
- ✅ Smart seeding (checks if already seeded)

### 4. Service Dependencies
```yaml
backend:
  depends_on:
    db-init:
      condition: service_completed_successfully
    postgres:
      condition: service_healthy
```

Ensures backend starts only after database is fully initialized.

## 📦 What's Persisted

### Database Objects
- ✅ **13+ Tables**: users, properties, financial_periods, chart_of_accounts, etc.
- ✅ **Indexes**: Primary keys, foreign keys, unique constraints
- ✅ **Constraints**: CHECK constraints, NOT NULL constraints
- ✅ **Sequences**: Auto-increment IDs
- ✅ **Views**: Any database views created
- ✅ **Functions**: Any stored procedures/functions

### Application Data
- ✅ **Users**: All user accounts and profiles
- ✅ **Properties**: All property records
- ✅ **Financial Data**: Balance sheets, income statements, cash flows
- ✅ **Documents**: Document upload metadata (files in MinIO)
- ✅ **Chart of Accounts**: 300+ pre-seeded accounts
- ✅ **Lenders**: 30+ pre-seeded lenders
- ✅ **Validation Rules**: All validation configurations
- ✅ **Extraction Templates**: Document parsing templates
- ✅ **Audit Trails**: All audit log entries

### Migration History
- ✅ **alembic_version table**: Tracks which migrations have been applied
- ✅ **19 migrations**: All schema changes tracked

## 🔍 Current Database Schema

### Core Tables (13+)
1. **users** - User accounts
2. **properties** - Property records
3. **financial_periods** - Time periods (monthly/quarterly)
4. **document_uploads** - Document metadata
5. **chart_of_accounts** - 300+ account codes
6. **balance_sheet_data** - Balance sheet line items
7. **income_statement_data** - Income statement line items
8. **cash_flow_data** - Cash flow statement data
9. **cash_flow_headers** - Cash flow headers (v1.0)
10. **cash_flow_adjustments** - Cash flow adjustments (v1.0)
11. **cash_account_reconciliations** - Cash reconciliations (v1.0)
12. **rent_roll_data** - Rent roll information
13. **validation_rules** - Data validation rules
14. **validation_results** - Validation outcomes
15. **extraction_templates** - Document extraction configs
16. **extraction_logs** - Extraction history
17. **audit_trail** - Complete audit log
18. **financial_metrics** - Calculated metrics
19. **lenders** - Lender information

## 🚀 How It Works

### First-Time Startup
```bash
docker compose up -d
```

**What happens:**
1. PostgreSQL starts and creates volume
2. `db-init` waits for PostgreSQL healthy
3. Creates all base tables (SQLAlchemy)
4. Runs 19 Alembic migrations in order
5. Seeds database (if not already seeded)
6. Backend starts after initialization complete

**Total time:** ~15-20 seconds

### Subsequent Startups
```bash
docker compose down
docker compose up -d
```

**What happens:**
1. PostgreSQL starts with existing volume
2. All data is already there
3. `db-init` checks seed status (skips if done)
4. Backend starts immediately

**Total time:** ~5-10 seconds (much faster!)

## 🔒 What Persists Across

### ✅ Container Restarts
```bash
docker compose restart postgres
```
**Result:** All data intact

### ✅ Container Removal & Recreation
```bash
docker compose down
docker compose up -d
```
**Result:** All data intact

### ✅ Image Updates
```bash
docker compose pull postgres
docker compose up -d
```
**Result:** All data intact

### ✅ System Reboots
```bash
sudo reboot
# After reboot:
docker compose up -d
```
**Result:** All data intact

### ✅ Adding New Migrations
```bash
# Create new migration
docker exec reims-backend alembic revision --autogenerate -m "add new table"

# Apply migration
docker compose restart backend
```
**Result:** New schema changes applied, existing data intact

## ⚠️ Data is ONLY Lost When

1. **Volume deletion with `-v` flag:**
   ```bash
   docker compose down -v  # ⚠️ DELETES ALL DATA
   ```

2. **Manual volume removal:**
   ```bash
   docker volume rm reims_postgres-data  # ⚠️ DELETES ALL DATA
   ```

3. **System prune with volumes:**
   ```bash
   docker system prune --volumes  # ⚠️ DELETES UNUSED VOLUMES
   ```

4. **Disk failure** (make backups!)

## 🧪 Verify Persistence

### Check Volume Exists
```bash
docker volume ls | grep postgres
# Should show: reims_postgres-data
```

### Check Volume Details
```bash
docker volume inspect reims_postgres-data
```

### Check Database Size
```bash
docker exec reims-postgres psql -U reims -d reims -c "\l+"
```

### Check Table Count
```bash
docker exec reims-postgres psql -U reims -d reims -c "\dt"
```

### Check Data Rows
```bash
# Check chart of accounts (should have 300+ rows)
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM chart_of_accounts;"

# Check lenders (should have 30+ rows)
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM lenders;"

# Check migration history
docker exec reims-postgres psql -U reims -d reims -c "SELECT * FROM alembic_version;"
```

### Check All Tables and Row Counts
```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = tablename) AS columns
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
"
```

## 💾 Backup & Restore

### Automated Backup Script

Create `/home/gurpyar/backup-database.sh`:

```bash
#!/bin/bash
# Backup PostgreSQL database

BACKUP_DIR="$HOME/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER="reims-postgres"
DB_NAME="reims"
DB_USER="reims"

mkdir -p "$BACKUP_DIR"

echo "🔄 Backing up PostgreSQL database..."

# Method 1: pg_dump (SQL format - human readable)
docker exec $CONTAINER pg_dump -U $DB_USER -d $DB_NAME \
  | gzip > "$BACKUP_DIR/reims-db-$TIMESTAMP.sql.gz"

echo "✅ Backup complete: reims-db-$TIMESTAMP.sql.gz"
echo "📁 Location: $BACKUP_DIR"
echo "📊 Size: $(du -h $BACKUP_DIR/reims-db-$TIMESTAMP.sql.gz | cut -f1)"

# Keep only last 7 days
find "$BACKUP_DIR" -name "reims-db-*.sql.gz" -mtime +7 -delete
echo "🧹 Old backups cleaned (kept last 7 days)"
```

Make it executable:
```bash
chmod +x /home/gurpyar/backup-database.sh
```

### Manual Backup Methods

#### Method 1: SQL Dump (Recommended)
```bash
# Create backup directory
mkdir -p ~/backups/postgres

# Backup database (compressed)
docker exec reims-postgres pg_dump -U reims -d reims \
  | gzip > ~/backups/postgres/reims-backup-$(date +%Y%m%d).sql.gz

# Backup database (plain SQL)
docker exec reims-postgres pg_dump -U reims -d reims \
  > ~/backups/postgres/reims-backup-$(date +%Y%m%d).sql
```

#### Method 2: Custom Format (Faster, Compressed)
```bash
docker exec reims-postgres pg_dump -U reims -d reims -Fc \
  > ~/backups/postgres/reims-backup-$(date +%Y%m%d).dump
```

#### Method 3: Directory Format (Parallel Backup)
```bash
mkdir -p ~/backups/postgres/backup-$(date +%Y%m%d)
docker exec reims-postgres pg_dump -U reims -d reims -Fd \
  -f /tmp/backup
docker cp reims-postgres:/tmp/backup ~/backups/postgres/backup-$(date +%Y%m%d)
```

#### Method 4: Volume Backup (Full Binary Copy)
```bash
# Stop database
docker compose stop postgres backend celery-worker

# Backup volume
docker run --rm \
  -v reims_postgres-data:/data:ro \
  -v ~/backups/postgres:/backup \
  ubuntu tar czf /backup/postgres-volume-$(date +%Y%m%d).tar.gz -C /data .

# Restart
docker compose up -d
```

### Restore Methods

#### Restore from SQL Dump (Compressed)
```bash
# Stop services that use database
docker compose stop backend celery-worker

# Drop and recreate database
docker exec reims-postgres psql -U reims -c "DROP DATABASE IF EXISTS reims;"
docker exec reims-postgres psql -U reims -c "CREATE DATABASE reims;"

# Restore
gunzip < ~/backups/postgres/reims-backup-20251107.sql.gz \
  | docker exec -i reims-postgres psql -U reims -d reims

# Restart services
docker compose up -d
```

#### Restore from SQL Dump (Plain)
```bash
docker compose stop backend celery-worker
docker exec reims-postgres psql -U reims -c "DROP DATABASE IF EXISTS reims;"
docker exec reims-postgres psql -U reims -c "CREATE DATABASE reims;"
cat ~/backups/postgres/reims-backup-20251107.sql \
  | docker exec -i reims-postgres psql -U reims -d reims
docker compose up -d
```

#### Restore from Custom Format
```bash
docker compose stop backend celery-worker
docker exec reims-postgres psql -U reims -c "DROP DATABASE IF EXISTS reims;"
docker exec reims-postgres psql -U reims -c "CREATE DATABASE reims;"
cat ~/backups/postgres/reims-backup-20251107.dump \
  | docker exec -i reims-postgres pg_restore -U reims -d reims
docker compose up -d
```

#### Restore from Volume Backup
```bash
# Stop all services
docker compose down

# Delete existing volume
docker volume rm reims_postgres-data

# Create new volume
docker volume create reims_postgres-data

# Restore data
docker run --rm \
  -v reims_postgres-data:/data \
  -v ~/backups/postgres:/backup \
  ubuntu bash -c "cd /data && tar xzf /backup/postgres-volume-20251107.tar.gz"

# Start services (db-init will run migrations if needed)
docker compose up -d
```

### Automated Daily Backups (Cron)

```bash
# Edit crontab
crontab -e

# Add daily backup at 3 AM
0 3 * * * /home/gurpyar/backup-database.sh > /dev/null 2>&1

# Or use the inline version:
0 3 * * * docker exec reims-postgres pg_dump -U reims -d reims | gzip > /home/gurpyar/backups/postgres/reims-db-$(date +\%Y\%m\%d).sql.gz 2>&1

# Clean old backups (keep 7 days)
0 4 * * * find /home/gurpyar/backups/postgres -name "reims-db-*.sql.gz" -mtime +7 -delete > /dev/null 2>&1
```

## 🔧 Database Migrations

### Current Migration Status
```bash
# Check current migration version
docker exec reims-backend alembic current

# Show migration history
docker exec reims-backend alembic history

# Show pending migrations
docker exec reims-backend alembic heads
```

### Create New Migration
```bash
# Auto-generate migration from model changes
docker exec reims-backend alembic revision --autogenerate -m "add new feature"

# Create blank migration (manual)
docker exec reims-backend alembic revision -m "custom changes"
```

### Apply Migrations
```bash
# Apply all pending migrations
docker exec reims-backend alembic upgrade head

# Apply specific migration
docker exec reims-backend alembic upgrade <revision>

# Rollback one migration
docker exec reims-backend alembic downgrade -1

# Rollback to specific version
docker exec reims-backend alembic downgrade <revision>
```

### Migration Best Practices
1. **Always backup before migrations**
2. **Test migrations in development first**
3. **Review auto-generated migrations** (they may need adjustments)
4. **Never delete migration files** (they're tracked in `alembic_version`)
5. **Migrations are part of your codebase** (commit them to git)

## 🔍 Database Monitoring

### Connection Info
```bash
# Access database directly
docker exec -it reims-postgres psql -U reims -d reims

# Via pgAdmin (Web UI)
# http://localhost:5050
# Email: admin@pgadmin.com
# Password: admin
```

### Database Statistics
```bash
# Database size
docker exec reims-postgres psql -U reims -d reims -c "\l+"

# Table sizes
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
"

# Index sizes
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size('public.'||indexname)) AS size
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY pg_relation_size('public.'||indexname) DESC;
"

# Active connections
docker exec reims-postgres psql -U reims -d reims -c "
SELECT COUNT(*) as connections, state 
FROM pg_stat_activity 
WHERE datname = 'reims' 
GROUP BY state;
"
```

### Performance Monitoring
```bash
# Slow queries
docker exec reims-postgres psql -U reims -d reims -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '1 second'
ORDER BY duration DESC;
"

# Table statistics
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    relname as table_name,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
"
```

## 🐛 Troubleshooting

### Issue: Database Not Initializing
**Symptoms:** `db-init` container fails or exits with error

**Solutions:**
```bash
# Check logs
docker compose logs db-init

# Check PostgreSQL is healthy
docker compose ps postgres

# Manually run initialization
docker compose up db-init

# If migrations fail, check alembic version
docker exec reims-postgres psql -U reims -d reims -c "SELECT * FROM alembic_version;"
```

### Issue: Migration Conflicts
**Symptoms:** "multiple heads" error, migration fails

**Solutions:**
```bash
# Check for multiple heads
docker exec reims-backend alembic heads

# Merge heads (creates merge migration)
docker exec reims-backend alembic merge heads -m "merge migrations"

# Apply merged migration
docker exec reims-backend alembic upgrade head
```

### Issue: Data Disappeared
**Diagnosis:**
```bash
# 1. Check if volume exists
docker volume inspect reims_postgres-data

# 2. Check if data is in volume
docker run --rm -v reims_postgres-data:/data ubuntu ls -la /data

# 3. Check PostgreSQL data directory
docker exec reims-postgres ls -la /var/lib/postgresql/data/pgdata

# 4. Try connecting to database
docker exec reims-postgres psql -U reims -d reims -c "\dt"
```

**Common Causes:**
- Ran `docker compose down -v` (deletes volumes)
- Volume corruption (rare)
- Disk full (check: `df -h`)

### Issue: Permission Denied
**Symptoms:** PostgreSQL won't start, permission errors in logs

**Solutions:**
```bash
# Check ownership in volume
docker run --rm -v reims_postgres-data:/data ubuntu ls -la /data

# Fix permissions (if needed)
docker run --rm -v reims_postgres-data:/data ubuntu chown -R 999:999 /data

# Restart PostgreSQL
docker compose restart postgres
```

### Issue: Database Corruption
**Symptoms:** "invalid page header", "could not read block"

**Solutions:**
```bash
# 1. Stop all services
docker compose down

# 2. Restore from backup
# (see Restore Methods above)

# 3. If no backup, try recovery mode
docker run --rm -v reims_postgres-data:/data ubuntu \
  touch /data/pgdata/recovery.signal

# 4. Start PostgreSQL
docker compose up -d postgres

# 5. Check logs
docker compose logs -f postgres
```

## 📊 Testing Persistence

### Quick Test Script
```bash
#!/bin/bash
# test_db_persistence.sh

echo "🧪 Testing Database Persistence"

# 1. Insert test data
echo "1️⃣ Inserting test data..."
docker exec reims-postgres psql -U reims -d reims -c "
INSERT INTO users (email, full_name, is_active, created_at)
VALUES ('test-persistence@example.com', 'Test User', true, NOW())
ON CONFLICT (email) DO NOTHING;
"

# 2. Verify data
echo "2️⃣ Verifying data..."
docker exec reims-postgres psql -U reims -d reims -t -c "
SELECT email FROM users WHERE email = 'test-persistence@example.com';
"

# 3. Restart PostgreSQL
echo "3️⃣ Restarting PostgreSQL..."
docker compose restart postgres
sleep 5

# 4. Verify after restart
echo "4️⃣ Verifying after restart..."
docker exec reims-postgres psql -U reims -d reims -t -c "
SELECT email FROM users WHERE email = 'test-persistence@example.com';
"

# 5. Full down/up cycle
echo "5️⃣ Testing full down/up cycle..."
docker compose down
docker compose up -d postgres
sleep 10

# 6. Final verification
echo "6️⃣ Final verification..."
docker exec reims-postgres psql -U reims -d reims -t -c "
SELECT email FROM users WHERE email = 'test-persistence@example.com';
"

echo "✅ Persistence test complete!"
```

## 🎓 Best Practices

1. **Regular Backups**
   - Daily automated backups via cron
   - Test restore procedures monthly
   - Keep at least 7 days of backups
   - Store backups on separate disk/server

2. **Migration Management**
   - Review auto-generated migrations
   - Test migrations in development
   - Backup before production migrations
   - Keep migrations in version control

3. **Monitoring**
   - Check database size weekly
   - Monitor connection counts
   - Watch for slow queries
   - Review table bloat

4. **Security**
   - Change default passwords in production
   - Use environment variables for credentials
   - Restrict network access
   - Enable SSL/TLS for connections

5. **Maintenance**
   - Regular VACUUM operations (PostgreSQL does this automatically)
   - Monitor disk space
   - Update PostgreSQL image periodically
   - Review and optimize indexes

## 📚 Related Documentation

- **[DOCKER_COMPOSE_README.md](DOCKER_COMPOSE_README.md)** - Full stack overview
- **[MINIO_PERSISTENCE.md](MINIO_PERSISTENCE.md)** - MinIO storage persistence
- **[backend/README.md](backend/README.md)** - Backend application docs
- **[PostgreSQL Documentation](https://www.postgresql.org/docs/17/)** - Official docs

## ✅ Summary

Your PostgreSQL database is **production-ready** with:

1. ✅ **Persistent volume** (`postgres-data`)
2. ✅ **19 migrations** tracked in Alembic
3. ✅ **13+ tables** with proper schemas
4. ✅ **300+ chart of accounts** pre-seeded
5. ✅ **30+ lenders** pre-seeded
6. ✅ **Automatic initialization** on first startup
7. ✅ **Smart seeding** (checks if already done)
8. ✅ **Health checks** for reliable startup
9. ✅ **Backup procedures** documented
10. ✅ **pgAdmin GUI** at http://localhost:5050

**Your database schema, tables, and all data are persistent and permanent!** 🎉

---

**Last Updated:** November 7, 2025  
**Status:** ✅ Production Ready

