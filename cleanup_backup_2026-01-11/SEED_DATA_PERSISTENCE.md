# Seed Data Persistence Guide

## ✅ All Seed Data is Persistent and Permanent

Your extraction templates, validation rules, chart of accounts, and lenders are fully persistent and will survive all container operations.

---

## 📦 What Seed Data is Persistent

### 1. Extraction Templates (4 Templates) ✅
**Stored in:** `extraction_templates` database table

Templates for parsing PDF documents:
- ✅ `standard_balance_sheet` - Balance sheet extraction
- ✅ `standard_income_statement` - Income statement extraction  
- ✅ `standard_cash_flow` - Cash flow statement extraction
- ✅ `standard_rent_roll` - Rent roll extraction

**Each template includes:**
- Document structure definitions
- Keywords for classification
- Extraction rules (regex patterns, fuzzy matching)
- Confidence weights
- Field validations

**Source file:** `backend/scripts/seed_extraction_templates.sql`

### 2. Validation Rules (8 Rules) ✅
**Stored in:** `validation_rules` database table

Business logic validation rules:
1. ✅ `balance_sheet_equation` - Assets = Liabilities + Equity
2. ✅ `balance_sheet_subtotals` - Current + Non-current = Total
3. ✅ `income_statement_calculation` - Net Income formula
4. ✅ `noi_calculation` - Net Operating Income formula
5. ✅ `occupancy_rate_range` - 0-100% validation
6. ✅ `rent_roll_total_rent` - Sum validation
7. ✅ `cash_flow_balance` - Operating + Investing + Financing
8. ✅ `cash_flow_ending_balance` - Beginning + Net = Ending

**Source file:** `backend/scripts/seed_validation_rules.sql`

### 3. Chart of Accounts (300+ Accounts) ✅
**Stored in:** `chart_of_accounts` database table

Pre-seeded account codes:
- ✅ 200+ Balance Sheet accounts (0000-3999)
- ✅ 100+ Income Statement accounts (4000-7999)
- ✅ 120+ Cash Flow specific accounts
- ✅ Account names, descriptions, and categories

**Source files:**
- `seed_balance_sheet_template_accounts.sql`
- `seed_balance_sheet_template_accounts_part2.sql`
- `seed_income_statement_template_accounts.sql`
- `seed_income_statement_template_accounts_part2.sql`
- `seed_cash_flow_specific_accounts.sql`
- `seed_cash_flow_accounts_comprehensive.sql`

### 4. Lenders (30+ Entries) ✅
**Stored in:** `lenders` database table

Pre-seeded lender information:
- ✅ Major commercial lenders (CIBC, KeyBank, Wells Fargo, etc.)
- ✅ Lender names and codes
- ✅ Contact information

**Source file:** `backend/scripts/seed_lenders.sql`

---

## 🏗️ How Seed Data Persistence Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Seed Files (SQL) - Version Controlled                 │
│  Location: /backend/scripts/seed_*.sql                 │
│  • In Git repository                                    │
│  • Mounted via bind mount in docker-compose            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓ (on first startup)
┌─────────────────────────────────────────────────────────┐
│  db-init Container                                      │
│  • Runs seed SQL files                                 │
│  • Checks if already seeded (idempotent)               │
│  • Populates database tables                           │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓ (data inserted)
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL Database Tables                             │
│  • extraction_templates (4 rows)                        │
│  • validation_rules (8 rows)                            │
│  • chart_of_accounts (300+ rows)                        │
│  • lenders (30+ rows)                                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓ (stored in)
┌─────────────────────────────────────────────────────────┐
│  Docker Volume: postgres-data                           │
│  • Persistent storage                                   │
│  • Survives container restarts                          │
│  • Survives down/up cycles                              │
└─────────────────────────────────────────────────────────┘
```

### First Startup Flow

1. **PostgreSQL starts** with `postgres-data` volume
2. **db-init container** runs:
   ```bash
   # Check if already seeded (checks for specific account code)
   SEED_CHECK = "SELECT COUNT(*) FROM chart_of_accounts WHERE account_code = '4010-0000'"
   
   # If count is 0, run seeding:
   if [ "$SEED_CHECK" -eq "0" ]; then
     psql -f scripts/seed_balance_sheet_template_accounts.sql
     psql -f scripts/seed_income_statement_template_accounts.sql
     psql -f scripts/seed_validation_rules.sql
     psql -f scripts/seed_extraction_templates.sql
     psql -f scripts/seed_lenders.sql
     psql -f scripts/seed_cash_flow_accounts.sql
   fi
   ```
3. **Data persists** in PostgreSQL tables
4. **Backend starts** and uses the seeded data

### Subsequent Startups

1. PostgreSQL starts with existing volume
2. db-init checks seed status (finds data already exists)
3. Skips seeding: `"ℹ️ Database already seeded, skipping"`
4. Backend starts immediately with existing data

---

## 🔍 Verify Seed Data Exists

### Quick Verification

```bash
# Check extraction templates (should be 4)
docker exec reims-postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) as template_count FROM extraction_templates;"

# Check validation rules (should be 8)
docker exec reims-postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) as rule_count FROM validation_rules;"

# Check chart of accounts (should be 300+)
docker exec reims-postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) as account_count FROM chart_of_accounts;"

# Check lenders (should be 30+)
docker exec reims-postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) as lender_count FROM lenders;"
```

### Detailed Verification

```bash
# List all extraction templates
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    id,
    template_name,
    document_type,
    is_default,
    array_length(keywords, 1) as keyword_count
FROM extraction_templates
ORDER BY document_type;
"

# List all validation rules
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    id,
    rule_name,
    document_type,
    rule_type,
    severity,
    is_active
FROM validation_rules
ORDER BY document_type, id;
"

# Sample chart of accounts
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    account_code,
    account_name,
    account_type,
    category
FROM chart_of_accounts
ORDER BY account_code
LIMIT 20;
"

# Sample lenders
docker exec reims-postgres psql -U reims -d reims -c "
SELECT 
    id,
    lender_name,
    lender_code
FROM lenders
ORDER BY lender_name
LIMIT 10;
"
```

---

## 🧪 Test Seed Data Persistence

### Test Script

Save as `test_seed_data_persistence.sh`:

```bash
#!/bin/bash

echo "=== Testing Seed Data Persistence ==="
echo ""

# 1. Check current seed data counts
echo "📊 Current seed data counts:"
TEMPLATES=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM extraction_templates;" | xargs)
RULES=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM validation_rules;" | xargs)
ACCOUNTS=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM chart_of_accounts;" | xargs)
LENDERS=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM lenders;" | xargs)

echo "  Extraction Templates: $TEMPLATES"
echo "  Validation Rules: $RULES"
echo "  Chart of Accounts: $ACCOUNTS"
echo "  Lenders: $LENDERS"
echo ""

# 2. Restart PostgreSQL
echo "🔄 Restarting PostgreSQL..."
docker compose restart postgres
sleep 5
echo "✅ PostgreSQL restarted"
echo ""

# 3. Verify counts still match
echo "📊 Verifying counts after restart:"
TEMPLATES_AFTER=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM extraction_templates;" | xargs)
RULES_AFTER=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM validation_rules;" | xargs)
ACCOUNTS_AFTER=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM chart_of_accounts;" | xargs)
LENDERS_AFTER=$(docker exec reims-postgres psql -U reims -d reims -t -c \
  "SELECT COUNT(*) FROM lenders;" | xargs)

echo "  Extraction Templates: $TEMPLATES_AFTER"
echo "  Validation Rules: $RULES_AFTER"
echo "  Chart of Accounts: $ACCOUNTS_AFTER"
echo "  Lenders: $LENDERS_AFTER"
echo ""

# 4. Compare
if [ "$TEMPLATES" = "$TEMPLATES_AFTER" ] && \
   [ "$RULES" = "$RULES_AFTER" ] && \
   [ "$ACCOUNTS" = "$ACCOUNTS_AFTER" ] && \
   [ "$LENDERS" = "$LENDERS_AFTER" ]; then
    echo "✅ All seed data persisted successfully!"
else
    echo "❌ Seed data counts changed after restart!"
    exit 1
fi
```

---

## 💾 Backup Seed Data

### Export Seed Data to SQL

```bash
# Create backup directory
mkdir -p ~/backups/seed-data

# Export extraction templates
docker exec reims-postgres pg_dump -U reims -d reims \
  --table=extraction_templates \
  --data-only --inserts \
  > ~/backups/seed-data/extraction_templates_$(date +%Y%m%d).sql

# Export validation rules
docker exec reims-postgres pg_dump -U reims -d reims \
  --table=validation_rules \
  --data-only --inserts \
  > ~/backups/seed-data/validation_rules_$(date +%Y%m%d).sql

# Export chart of accounts
docker exec reims-postgres pg_dump -U reims -d reims \
  --table=chart_of_accounts \
  --data-only --inserts \
  > ~/backups/seed-data/chart_of_accounts_$(date +%Y%m%d).sql

# Export lenders
docker exec reims-postgres pg_dump -U reims -d reims \
  --table=lenders \
  --data-only --inserts \
  > ~/backups/seed-data/lenders_$(date +%Y%m%d).sql
```

### Export All Seed Data at Once

```bash
# Export all seed tables
docker exec reims-postgres pg_dump -U reims -d reims \
  --table=extraction_templates \
  --table=validation_rules \
  --table=chart_of_accounts \
  --table=lenders \
  --data-only --inserts \
  | gzip > ~/backups/seed-data/all_seed_data_$(date +%Y%m%d).sql.gz
```

---

## 🔄 Re-seed Data (If Needed)

### When to Re-seed

Re-seed if:
- Seed data was accidentally deleted
- You want to reset to default values
- You've updated seed files and want to apply changes

### Option 1: Re-run Specific Seed File

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

### Option 2: Force Re-seeding via db-init

```bash
# Delete a marker account to trigger re-seeding
docker exec reims-postgres psql -U reims -d reims -c \
  "DELETE FROM chart_of_accounts WHERE account_code = '4010-0000';"

# Restart db-init to trigger seeding
docker compose up -d db-init

# Check logs
docker compose logs db-init
```

### Option 3: Manual Re-seeding

```bash
# Clear existing data
docker exec reims-postgres psql -U reims -d reims -c "
TRUNCATE extraction_templates CASCADE;
TRUNCATE validation_rules CASCADE;
TRUNCATE chart_of_accounts CASCADE;
TRUNCATE lenders CASCADE;
"

# Re-run db-init
docker compose up -d db-init
```

---

## 🔧 Update Seed Data

### Modify Existing Templates/Rules

1. **Edit the seed SQL file:**
   ```bash
   vim /home/gurpyar/Documents/R/REIMS2/backend/scripts/seed_extraction_templates.sql
   ```

2. **Clear existing data:**
   ```sql
   -- Seed files already include DELETE statements
   DELETE FROM extraction_templates WHERE template_name IN (...);
   ```

3. **Re-run the seed file:**
   ```bash
   docker exec reims-postgres psql -U reims -d reims \
     -f /app/scripts/seed_extraction_templates.sql
   ```

### Add New Templates/Rules

1. **Option A: Edit existing seed file**
   - Add new INSERT statements to seed file
   - Re-run seed file

2. **Option B: Create new seed file**
   ```bash
   # Create new seed file
   vim /home/gurpyar/Documents/R/REIMS2/backend/scripts/seed_custom_templates.sql
   
   # Run it
   docker exec reims-postgres psql -U reims -d reims \
     -f /app/scripts/seed_custom_templates.sql
   ```

3. **Option C: Insert directly**
   ```bash
   docker exec reims-postgres psql -U reims -d reims -c "
   INSERT INTO extraction_templates (
     template_name, document_type, ...
   ) VALUES (...);
   "
   ```

---

## 📊 Seed Data Structure

### Extraction Templates Table

```sql
CREATE TABLE extraction_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) UNIQUE NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    template_structure JSONB,
    keywords TEXT[],
    extraction_rules JSONB,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Validation Rules Table

```sql
CREATE TABLE validation_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    rule_description TEXT,
    document_type VARCHAR(50) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    rule_formula TEXT,
    error_message TEXT,
    severity VARCHAR(20) DEFAULT 'error',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 🎯 Best Practices

### 1. Version Control
- ✅ Seed files are in Git repository
- ✅ Track changes to seed files
- ✅ Commit updates to seed data

### 2. Documentation
- ✅ Document seed file changes
- ✅ Note why templates/rules were modified
- ✅ Keep changelog of seed data versions

### 3. Testing
- ✅ Test seed files before committing
- ✅ Verify counts after seeding
- ✅ Check that application works with new seed data

### 4. Backup
- ✅ Export seed data periodically
- ✅ Keep backup before making changes
- ✅ Include seed data in database backups

### 5. Idempotency
- ✅ Seed files include DELETE before INSERT
- ✅ Safe to run multiple times
- ✅ Won't create duplicates

---

## 📚 Seed File Locations

All seed files are in: `/home/gurpyar/Documents/R/REIMS2/backend/scripts/`

| File | Purpose | Rows |
|------|---------|------|
| `seed_extraction_templates.sql` | PDF extraction templates | 4 |
| `seed_validation_rules.sql` | Data validation rules | 8 |
| `seed_balance_sheet_template_accounts.sql` | BS accounts (part 1) | 100+ |
| `seed_balance_sheet_template_accounts_part2.sql` | BS accounts (part 2) | 100+ |
| `seed_income_statement_template_accounts.sql` | IS accounts (part 1) | 50+ |
| `seed_income_statement_template_accounts_part2.sql` | IS accounts (part 2) | 50+ |
| `seed_cash_flow_specific_accounts.sql` | Cash flow accounts | 30+ |
| `seed_cash_flow_accounts_comprehensive.sql` | Cash flow comprehensive | 120+ |
| `seed_lenders.sql` | Lender information | 30+ |

---

## ✅ Summary

### Your Seed Data is Persistent ✅

1. ✅ **Extraction Templates** - 4 templates for document parsing
2. ✅ **Validation Rules** - 8 rules for data validation
3. ✅ **Chart of Accounts** - 300+ accounts for all statement types
4. ✅ **Lenders** - 30+ lender records

### How Persistence Works ✅

1. ✅ Seed **files** stored in codebase (version controlled)
2. ✅ Seed **data** stored in PostgreSQL tables
3. ✅ PostgreSQL data stored in `postgres-data` volume
4. ✅ Volume persists across all container operations
5. ✅ Seeding is idempotent (safe to run multiple times)

### What You Can Do ✅

1. ✅ Verify seed data exists
2. ✅ Export seed data to SQL files
3. ✅ Re-seed if needed
4. ✅ Update seed files
5. ✅ Add new templates/rules

### What's Already Working ✅

- ✅ Automatic seeding on first startup
- ✅ Smart check (skips if already seeded)
- ✅ All data persists in PostgreSQL volume
- ✅ Survives restarts and down/up cycles
- ✅ Backed up with database backups

**Your seed data is permanent and will survive all normal operations!**

---

**Last Updated:** November 7, 2025  
**Status:** ✅ Production Ready  
**Location:** `/home/gurpyar/Documents/R/REIMS2/backend/scripts/`

