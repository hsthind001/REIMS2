# REIMS2 Audit Rules Implementation Scripts

## Overview

This directory contains SQL implementation scripts for deploying comprehensive audit rules to the REIMS2 database. These scripts implement the complete audit framework documented in `/home/hsthind/REIMS Audit Rules/`.

## 📁 Files

| Script | Description | Rules | Priority |
|--------|-------------|-------|----------|
| `00_MASTER_EXECUTION_SCRIPT.sql` | **Master script** - executes all scripts in order | All | - |
| `01_balance_sheet_rules.sql` | Balance Sheet validation rules | 30 | HIGH |
| `02_income_statement_rules.sql` | Income Statement validation rules | 16 | HIGH |
| `03_prevention_rules.sql` | Prevention rules (data quality at entry) | 15 | MEDIUM |
| `04_auto_resolution_rules.sql` | Auto-resolution rules (automatic fixes) | 15 | MEDIUM |
| `05_forensic_audit_framework.sql` | Forensic audit & fraud detection | 30+ | LOW |

## 🚀 Quick Start

### Option 1: Execute Master Script (Recommended)

Execute all scripts in one go:

```bash
# From the project root
cd /home/hsthind/Documents/GitHub/REIMS2

# Via Docker (recommended)
docker compose exec -T postgres psql -U reims -d reims < implementation_scripts/00_MASTER_EXECUTION_SCRIPT.sql

# Or directly via psql
psql -U reims -d reims -h localhost -p 5433 -f implementation_scripts/00_MASTER_EXECUTION_SCRIPT.sql
```

### Option 2: Execute Individual Scripts

Execute scripts in order:

```bash
cd implementation_scripts

# 1. Balance Sheet Rules
docker compose exec -T postgres psql -U reims -d reims < 01_balance_sheet_rules.sql

# 2. Income Statement Rules
docker compose exec -T postgres psql -U reims -d reims < 02_income_statement_rules.sql

# 3. Prevention Rules
docker compose exec -T postgres psql -U reims -d reims < 03_prevention_rules.sql

# 4. Auto-Resolution Rules
docker compose exec -T postgres psql -U reims -d reims < 04_auto_resolution_rules.sql

# 5. Forensic Audit Framework
docker compose exec -T postgres psql -U reims -d reims < 05_forensic_audit_framework.sql
```

## 📊 What Gets Deployed

### Current Status (After Phase 1 & 2)
- ✅ 53 Validation Rules
- ✅ 10 Reconciliation Rules
- ✅ 10 Calculated Rules
- ✅ 15 Alert Rules
- ❌ 0 Prevention Rules
- ❌ 0 Auto-Resolution Rules
- ❌ 0 Forensic Audit Rules

### After Full Deployment
- ✅ **83** Validation Rules (+30)
- ✅ **10** Reconciliation Rules (no change)
- ✅ **10** Calculated Rules (no change)
- ✅ **15** Alert Rules (no change)
- ✅ **15** Prevention Rules (+15)
- ✅ **15** Auto-Resolution Rules (+15)
- ✅ **30+** Forensic Audit Rules (+30)

**Total: 168+ Active Rules**

## 📋 Script Details

### 01_balance_sheet_rules.sql

Implements remaining 30 Balance Sheet validation rules including:
- Current Assets composition and tracking
- Property & Equipment depreciation patterns
- Other Assets (deposits, loan costs, amortization)
- Current Liabilities tracking
- Capital account validation

**Key Rules:**
- BS-3 through BS-32: Asset/liability tracking
- BS-35: Change in Total Capital

### 02_income_statement_rules.sql

Implements 16 additional Income Statement validation rules including:
- Total Income composition
- Reimbursement component validation
- Variable income tracking
- Expense category composition
- Below-the-line pattern validation

**Key Rules:**
- IS-4 through IS-25: Revenue, expense, and pattern validation

### 03_prevention_rules.sql

Implements 15 prevention rules to stop bad data at entry:
- Negative payment prevention
- Escrow overdraft prevention
- Duplicate entry prevention
- Overlapping lease prevention
- Invalid account code prevention

**All prevention rules run before data is saved**

### 04_auto_resolution_rules.sql

Implements 15 auto-resolution rules for automatic fixes:
- Rounding difference auto-fix (< $1)
- Missing calculation auto-population
- Data cleaning (spaces, case, formats)
- Small reconciliation differences
- Standard business rule application

**Some rules require approval, others run automatically**

### 05_forensic_audit_framework.sql

Implements comprehensive forensic audit framework:
- Document completeness checks (3 rules)
- Mathematical integrity tests (6 rules)
- Fraud detection algorithms (8 rules)
- Collections analysis (3 rules)
- Debt service & liquidity (5 rules)
- Performance metrics (4 rules)
- Tenant & lease analysis (7 rules)
- Materiality thresholds

**Creates new tables:**
- `forensic_audit_rules`
- `materiality_thresholds`

## ⚙️ Configuration

### Prerequisites

1. **Database Connection**: Ensure PostgreSQL is running
   ```bash
   docker compose ps postgres
   ```

2. **Database Access**: Verify credentials
   - User: `reims`
   - Database: `reims`
   - Password: From `.env` file

3. **Backup**: Create backup before deployment (optional but recommended)
   ```bash
   docker compose exec postgres pg_dump -U reims reims > backup_before_rules_$(date +%Y%m%d).sql
   ```

### Post-Deployment Verification

After running scripts, verify deployment:

```sql
-- Check rule counts
SELECT 'validation_rules' as table, COUNT(*) FROM validation_rules WHERE is_active = true
UNION ALL
SELECT 'reconciliation_rules', COUNT(*) FROM reconciliation_rules WHERE is_active = true
UNION ALL
SELECT 'calculated_rules', COUNT(*) FROM calculated_rules WHERE is_active = true
UNION ALL
SELECT 'alert_rules', COUNT(*) FROM alert_rules WHERE is_active = true
UNION ALL
SELECT 'prevention_rules', COUNT(*) FROM prevention_rules WHERE is_active = true
UNION ALL
SELECT 'auto_resolution_rules', COUNT(*) FROM auto_resolution_rules WHERE is_active = true
UNION ALL
SELECT 'forensic_audit_rules', COUNT(*) FROM forensic_audit_rules WHERE is_active = true;
```

Expected output:
```
table                   | count
------------------------|-------
validation_rules        | 83
reconciliation_rules    | 10
calculated_rules        | 10
alert_rules            | 15
prevention_rules       | 15
auto_resolution_rules  | 15
forensic_audit_rules   | 30+
```

## 🔧 Troubleshooting

### Error: "relation does not exist"

Some rules reference tables that might not exist. Check table structure:
```sql
\d prevention_rules
\d auto_resolution_rules
\d forensic_audit_rules
```

If tables don't exist, they will be created by the scripts.

### Error: "duplicate key value violates unique constraint"

Scripts are idempotent but some rules may have been partially deployed. To reset:

```sql
-- WARNING: This deletes custom rules you may have added
DELETE FROM validation_rules WHERE rule_name LIKE 'bs_%' OR rule_name LIKE 'is_%';
DELETE FROM prevention_rules;
DELETE FROM auto_resolution_rules;
DELETE FROM forensic_audit_rules;
```

Then re-run the scripts.

### Error: "column does not exist"

Check if your database schema matches expected structure. Some scripts may need adjustment based on your actual schema.

## 📖 Documentation References

- **Audit Rules Documentation**: `/home/hsthind/REIMS Audit Rules/`
- **Gap Analysis**: `/home/hsthind/Documents/GitHub/REIMS2/AUDIT_RULES_GAP_ANALYSIS.md`
- **Coverage Dashboard**: `/home/hsthind/Documents/GitHub/REIMS2/RULE_COVERAGE_DASHBOARD.md`

## 🎯 Next Steps

After deploying these scripts:

1. **Review Dashboard**: Check `RULE_COVERAGE_DASHBOARD.md` for updated coverage
2. **Test Rules**: Upload test documents to verify rules execute correctly
3. **Configure Alerts**: Set up notification channels for critical alerts
4. **Train Users**: Educate team on prevention rules and auto-resolution
5. **Monitor Performance**: Review rule execution times and optimize if needed

## 📝 Maintenance

### Adding New Rules

To add custom rules, follow the pattern in existing scripts:

```sql
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    is_active
) VALUES (
    'custom_rule_name',
    'Description of what this rule checks',
    'document_type', -- e.g., 'balance_sheet'
    'check_type',    -- e.g., 'balance_check'
    'formula',
    'Error message shown to users',
    'error',         -- or 'warning', 'info'
    true
);
```

### Disabling Rules

To temporarily disable a rule without deleting:

```sql
UPDATE validation_rules SET is_active = false WHERE rule_name = 'rule_to_disable';
```

### Rule Versioning

All rule insertions should track version and date:

```sql
-- Add metadata columns if needed
ALTER TABLE validation_rules ADD COLUMN deployed_date TIMESTAMP DEFAULT NOW();
ALTER TABLE validation_rules ADD COLUMN deployed_version VARCHAR(20) DEFAULT '1.0';
```

## 🔐 Security Notes

- These scripts create rules that validate sensitive financial data
- Review prevention rules to ensure they align with business policies
- Auto-resolution rules modify data automatically - review carefully
- Forensic audit rules may flag sensitive transactions - limit access

## 📞 Support

For issues or questions:
1. Check `AUDIT_RULES_GAP_ANALYSIS.md` for detailed rule documentation
2. Review PostgreSQL logs: `docker compose logs postgres`
3. Verify database schema compatibility
4. Contact: [Your support contact]

---

**Version**: 1.0
**Last Updated**: 2025-12-28
**Compatibility**: REIMS2 PostgreSQL Database
