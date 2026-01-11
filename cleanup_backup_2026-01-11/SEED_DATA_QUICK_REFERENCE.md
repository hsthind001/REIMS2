# Seed Data Quick Reference

## 🎯 What Seed Data is Persistent

| Data Type | Table | Count | Status |
|-----------|-------|-------|--------|
| **Extraction Templates** | `extraction_templates` | 4 | ✅ Persistent |
| **Validation Rules** | `validation_rules` | 8 | ✅ Persistent |
| **Chart of Accounts** | `chart_of_accounts` | 300+ | ✅ Persistent |
| **Lenders** | `lenders` | 30+ | ✅ Persistent |

## ⚡ Quick Commands

### Check Seed Data
```bash
# Count all seed data
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    'Extraction Templates' as data_type, COUNT(*) FROM extraction_templates
UNION ALL
SELECT 'Validation Rules', COUNT(*) FROM validation_rules
UNION ALL
SELECT 'Chart of Accounts', COUNT(*) FROM chart_of_accounts
UNION ALL
SELECT 'Lenders', COUNT(*) FROM lenders;
"
```

### List Extraction Templates
```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT template_name, document_type, is_default 
FROM extraction_templates 
ORDER BY document_type;
"
```

### List Validation Rules
```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT rule_name, document_type, severity, is_active 
FROM validation_rules 
ORDER BY document_type;
"
```

### Sample Chart of Accounts
```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT account_code, account_name, account_type 
FROM chart_of_accounts 
ORDER BY account_code 
LIMIT 20;
"
```

### Sample Lenders
```bash
docker exec reims-postgres psql -U reims -d reims -c "
SELECT lender_name, lender_code 
FROM lenders 
ORDER BY lender_name 
LIMIT 10;
"
```

## 🧪 Test Persistence
```bash
./test_seed_data_persistence.sh
```

## 💾 Backup Seed Data
```bash
# Backup all seed data
./backup-seed-data.sh

# Backup to specific location
mkdir -p ~/backups/seed-data
docker exec reims-postgres pg_dump -U reims -d reims \
  --table=extraction_templates \
  --table=validation_rules \
  --table=chart_of_accounts \
  --table=lenders \
  --data-only --inserts \
  | gzip > ~/backups/seed-data/all_seed_data_$(date +%Y%m%d).sql.gz
```

## 🔄 Re-seed Data
```bash
# Re-seed extraction templates
docker exec reims-postgres psql -U reims -d reims \
  -f /app/scripts/seed_extraction_templates.sql

# Re-seed validation rules
docker exec reims-postgres psql -U reims -d reims \
  -f /app/scripts/seed_validation_rules.sql

# Re-seed chart of accounts
docker exec reims-postgres psql -U reims -d reims \
  -f /app/scripts/seed_balance_sheet_template_accounts.sql

# Re-seed lenders
docker exec reims-postgres psql -U reims -d reims \
  -f /app/scripts/seed_lenders.sql
```

## 📁 Seed File Locations

All seed files are in: `/home/gurpyar/Documents/R/REIMS2/backend/scripts/`

- `seed_extraction_templates.sql` - 4 PDF extraction templates
- `seed_validation_rules.sql` - 8 validation rules
- `seed_balance_sheet_template_accounts.sql` - Balance sheet accounts
- `seed_income_statement_template_accounts.sql` - Income statement accounts
- `seed_cash_flow_accounts_comprehensive.sql` - Cash flow accounts
- `seed_lenders.sql` - 30+ lenders

## 🔍 Verify Seeding Status

```bash
# Check if db-init completed seeding
docker compose logs db-init | grep -E "(Seeding|seeded)"

# Should show:
# ✅ All seed files loaded
# OR
# ℹ️  Database already seeded, skipping
```

## ⚠️ Important Notes

✅ **Seed Data Persists:**
- Stored in PostgreSQL database tables
- Survives container restarts
- Survives `docker compose down` + `up`
- Backed up with database backups

✅ **Seed Files (Source):**
- Stored in codebase (Git)
- Mounted via bind mount
- Used only during initial seeding
- Version controlled

## 📚 Full Documentation

- **[SEED_DATA_PERSISTENCE.md](SEED_DATA_PERSISTENCE.md)** - Complete guide
- **[DATABASE_PERSISTENCE.md](DATABASE_PERSISTENCE.md)** - Database overview
- **[PERSISTENCE_COMPLETE_SUMMARY.md](PERSISTENCE_COMPLETE_SUMMARY.md)** - All data

## 🎯 Expected Counts

After initial seeding, you should have:
- **4** extraction templates (balance_sheet, income_statement, cash_flow, rent_roll)
- **8** validation rules (equation checks, range checks, etc.)
- **300+** chart of accounts (all account codes)
- **30+** lenders (major commercial lenders)

If counts don't match, run:
```bash
docker compose up -d db-init
docker compose logs db-init
```

---

**Status:** ✅ All seed data is persistent  
**Location:** PostgreSQL database + Version-controlled seed files  
**Last Updated:** November 7, 2025

