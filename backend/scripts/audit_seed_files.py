#!/usr/bin/env python3
"""
Comprehensive Seed Files Audit Script

Audits all seed files for data accuracy, integrity, and consistency.
Generates detailed report of findings.

Usage:
    python backend/scripts/audit_seed_files.py
    
Or from Docker:
    docker exec reims-backend python3 backend/scripts/audit_seed_files.py
"""

import sys
import os
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal
from app.models.property import Property
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.validation_rule import ValidationRule
from app.models.extraction_template import ExtractionTemplate


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


# Expected property names from PDF documents
EXPECTED_PROPERTIES = {
    "ESP001": "Eastern Shore Plaza",
    "HMND001": "Hammond Aire Shopping Center",
    "TCSH001": "The Crossings of Spring Hill",
    "WEND001": "Wendover Commons"
}

# Seed files that should be loaded
EXPECTED_SEED_FILES = {
    "chart_of_accounts": [
        "seed_balance_sheet_template_accounts.sql",
        "seed_balance_sheet_template_accounts_part2.sql",
        "seed_income_statement_template_accounts.sql",
        "seed_income_statement_template_accounts_part2.sql"
    ],
    "validation_rules": ["seed_validation_rules.sql"],
    "extraction_templates": ["seed_extraction_templates.sql"],
    "lenders": ["seed_lenders.sql"]
}


class AuditResult:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
        self.successes = []
    
    def add_issue(self, severity, category, message, details=None):
        item = {
            'severity': severity,
            'category': category,
            'message': message,
            'details': details
        }
        if severity == 'critical':
            self.issues.append(item)
        elif severity == 'warning':
            self.warnings.append(item)
        else:
            self.info.append(item)
    
    def add_success(self, message):
        self.successes.append(message)


def audit_properties(db: Session, result: AuditResult):
    """Audit properties against expected values"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Auditing Properties{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")
    
    for code, expected_name in EXPECTED_PROPERTIES.items():
        prop = db.query(Property).filter(Property.property_code == code).first()
        
        if not prop:
            result.add_issue('critical', 'Properties', f"Property {code} not found in database", expected_name)
            print(f"{Colors.RED}❌ {code}: Missing from database{Colors.ENDC}")
        elif prop.property_name != expected_name:
            result.add_issue('critical', 'Properties', f"Property {code} has wrong name", 
                           f"Expected: '{expected_name}', Got: '{prop.property_name}'")
            print(f"{Colors.RED}❌ {code}: {prop.property_name}{Colors.ENDC}")
            print(f"    Expected: {expected_name}")
        else:
            result.add_success(f"{code}: {prop.property_name}")
            print(f"{Colors.GREEN}✅ {code}: {prop.property_name}{Colors.ENDC}")


def audit_chart_of_accounts(db: Session, result: AuditResult):
    """Audit chart of accounts for integrity issues"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Auditing Chart of Accounts{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")
    
    # Count total accounts
    total = db.query(ChartOfAccounts).count()
    print(f"Total accounts: {Colors.BOLD}{total}{Colors.ENDC}\n")
    
    if total == 0:
        result.add_issue('critical', 'Chart of Accounts', "No accounts found in database", 
                       "Run seed files to populate")
        print(f"{Colors.RED}❌ No accounts in database!{Colors.ENDC}\n")
        return
    
    # Check 1: Duplicates
    duplicates = db.execute(text("""
        SELECT account_code, COUNT(*) as count
        FROM chart_of_accounts 
        GROUP BY account_code 
        HAVING COUNT(*) > 1
    """)).fetchall()
    
    if duplicates:
        for dup in duplicates:
            result.add_issue('critical', 'Chart of Accounts', 
                           f"Duplicate account code: {dup[0]}", f"Appears {dup[1]} times")
            print(f"{Colors.RED}❌ Duplicate code: {dup[0]} ({dup[1]} times){Colors.ENDC}")
    else:
        result.add_success("No duplicate account codes")
        print(f"{Colors.GREEN}✅ No duplicate codes{Colors.ENDC}")
    
    # Check 2: Orphaned parents
    orphans = db.execute(text("""
        SELECT account_code, parent_account_code
        FROM chart_of_accounts 
        WHERE parent_account_code IS NOT NULL 
        AND parent_account_code NOT IN (SELECT account_code FROM chart_of_accounts)
    """)).fetchall()
    
    if orphans:
        for orphan in orphans:
            result.add_issue('critical', 'Chart of Accounts',
                           f"Orphaned parent reference: {orphan[0]}", 
                           f"Parent {orphan[1]} does not exist")
            print(f"{Colors.RED}❌ Orphan: {orphan[0]} → {orphan[1]}{Colors.ENDC}")
    else:
        result.add_success("No orphaned parent references")
        print(f"{Colors.GREEN}✅ No orphaned parents{Colors.ENDC}")
    
    # Check 3: Whitespace issues
    whitespace = db.execute(text("""
        SELECT account_code, account_name
        FROM chart_of_accounts 
        WHERE account_name LIKE '%  %' OR account_name != TRIM(account_name)
    """)).fetchall()
    
    if whitespace:
        for ws in whitespace:
            result.add_issue('warning', 'Chart of Accounts',
                           f"Whitespace issue: {ws[0]}", ws[1])
            print(f"{Colors.YELLOW}⚠️  Whitespace: {ws[0]} - {ws[1]}{Colors.ENDC}")
    else:
        result.add_success("No whitespace issues")
        print(f"{Colors.GREEN}✅ No whitespace issues{Colors.ENDC}")
    
    # Check 4: Invalid account types
    invalid_types = db.execute(text("""
        SELECT account_code, account_type
        FROM chart_of_accounts 
        WHERE account_type NOT IN ('asset', 'liability', 'equity', 'income', 'expense')
    """)).fetchall()
    
    if invalid_types:
        for inv in invalid_types:
            result.add_issue('critical', 'Chart of Accounts',
                           f"Invalid account type: {inv[0]}", inv[1])
            print(f"{Colors.RED}❌ Invalid type: {inv[0]} - {inv[1]}{Colors.ENDC}")
    else:
        result.add_success("All account types valid")
        print(f"{Colors.GREEN}✅ All types valid{Colors.ENDC}")
    
    # Check 5: Common typos
    typos = db.execute(text("""
        SELECT account_code, account_name
        FROM chart_of_accounts
        WHERE 
            account_name ILIKE '%managment%' OR
            account_name ILIKE '%recievable%' OR
            account_name ILIKE '%commision%' OR
            account_name ILIKE '%expence%' OR
            account_name ILIKE '%accomodation%'
    """)).fetchall()
    
    if typos:
        for typo in typos:
            result.add_issue('warning', 'Chart of Accounts',
                           f"Possible typo: {typo[0]}", typo[1])
            print(f"{Colors.YELLOW}⚠️  Typo: {typo[0]} - {typo[1]}{Colors.ENDC}")
    else:
        result.add_success("No common typos found")
        print(f"{Colors.GREEN}✅ No typos detected{Colors.ENDC}")


def audit_validation_rules(db: Session, result: AuditResult):
    """Audit validation rules"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Auditing Validation Rules{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")
    
    total = db.query(ValidationRule).count()
    print(f"Total rules: {Colors.BOLD}{total}{Colors.ENDC}\n")
    
    if total == 0:
        result.add_issue('critical', 'Validation Rules', 
                       "No validation rules in database",
                       "Run seed_validation_rules.sql")
        print(f"{Colors.RED}❌ No validation rules seeded!{Colors.ENDC}")
        print(f"    {Colors.YELLOW}Action needed: Run scripts/seed_validation_rules.sql{Colors.ENDC}\n")
        return
    
    # Check for invalid severity
    invalid_severity = db.execute(text("""
        SELECT rule_name, severity
        FROM validation_rules
        WHERE severity NOT IN ('error', 'warning', 'info')
    """)).fetchall()
    
    if invalid_severity:
        for inv in invalid_severity:
            result.add_issue('warning', 'Validation Rules',
                           f"Invalid severity: {inv[0]}", inv[1])
            print(f"{Colors.YELLOW}⚠️  Invalid severity: {inv[0]} - {inv[1]}{Colors.ENDC}")
    else:
        result.add_success("All severities valid")
        print(f"{Colors.GREEN}✅ All severities valid{Colors.ENDC}")


def audit_extraction_templates(db: Session, result: AuditResult):
    """Audit extraction templates"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Auditing Extraction Templates{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")
    
    total = db.query(ExtractionTemplate).count()
    print(f"Total templates: {Colors.BOLD}{total}{Colors.ENDC}\n")
    
    if total == 0:
        result.add_issue('critical', 'Extraction Templates',
                       "No extraction templates in database",
                       "Run seed_extraction_templates.sql")
        print(f"{Colors.RED}❌ No extraction templates seeded!{Colors.ENDC}")
        print(f"    {Colors.YELLOW}Action needed: Run scripts/seed_extraction_templates.sql{Colors.ENDC}\n")
        return
    
    # Check for required document types
    templates = db.query(ExtractionTemplate).all()
    found_types = {t.document_type for t in templates}
    expected_types = {'balance_sheet', 'income_statement', 'cash_flow', 'rent_roll'}
    missing_types = expected_types - found_types
    
    if missing_types:
        result.add_issue('warning', 'Extraction Templates',
                       "Missing templates", f"Missing: {', '.join(missing_types)}")
        print(f"{Colors.YELLOW}⚠️  Missing templates: {', '.join(missing_types)}{Colors.ENDC}")
    else:
        result.add_success("All document types have templates")
        print(f"{Colors.GREEN}✅ All document types covered{Colors.ENDC}")


def audit_lenders(db: Session, result: AuditResult):
    """Audit lenders table"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Auditing Lenders{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")
    
    total = db.execute(text("SELECT COUNT(*) FROM lenders")).scalar()
    print(f"Total lenders: {Colors.BOLD}{total or 0}{Colors.ENDC}\n")
    
    if not total or total == 0:
        result.add_issue('warning', 'Lenders',
                       "No lenders in database",
                       "Run seed_lenders.sql if lender tracking is needed")
        print(f"{Colors.YELLOW}⚠️  No lenders seeded{Colors.ENDC}")
        print(f"    {Colors.CYAN}Info: Run scripts/seed_lenders.sql if needed{Colors.ENDC}\n")
        return
    
    result.add_success(f"{total} lenders seeded")
    print(f"{Colors.GREEN}✅ {total} lenders seeded{Colors.ENDC}")


def generate_report(result: AuditResult):
    """Generate audit report"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}AUDIT SUMMARY{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}{'='*60}{Colors.ENDC}\n")
    
    # Summary statistics
    total_checks = len(result.successes) + len(result.issues) + len(result.warnings) + len(result.info)
    
    print(f"{Colors.BOLD}Statistics:{Colors.ENDC}")
    print(f"  {Colors.GREEN}✅ Passed: {len(result.successes)}{Colors.ENDC}")
    print(f"  {Colors.RED}❌ Critical Issues: {len(result.issues)}{Colors.ENDC}")
    print(f"  {Colors.YELLOW}⚠️  Warnings: {len(result.warnings)}{Colors.ENDC}")
    print(f"  {Colors.CYAN}ℹ️  Info: {len(result.info)}{Colors.ENDC}")
    print(f"  {Colors.BOLD}Total Checks: {total_checks}{Colors.ENDC}\n")
    
    # Overall status
    if len(result.issues) == 0:
        if len(result.warnings) == 0:
            print(f"{Colors.BOLD}{Colors.GREEN}🎉 ALL CHECKS PASSED! Data integrity verified.{Colors.ENDC}\n")
            return True
        else:
            print(f"{Colors.BOLD}{Colors.YELLOW}⚠️  Some warnings found. Review recommended.{Colors.ENDC}\n")
            return True
    else:
        print(f"{Colors.BOLD}{Colors.RED}❌ CRITICAL ISSUES FOUND! Action required.{Colors.ENDC}\n")
        
        # List critical issues
        if result.issues:
            print(f"{Colors.BOLD}Critical Issues:{Colors.ENDC}")
            for i, issue in enumerate(result.issues, 1):
                print(f"  {i}. [{issue['category']}] {issue['message']}")
                if issue['details']:
                    print(f"     Details: {issue['details']}")
            print()
        
        # List warnings
        if result.warnings:
            print(f"{Colors.BOLD}Warnings:{Colors.ENDC}")
            for i, warning in enumerate(result.warnings, 1):
                print(f"  {i}. [{warning['category']}] {warning['message']}")
                if warning['details']:
                    print(f"     Details: {warning['details']}")
            print()
        
        return False


def main():
    """Main audit function"""
    try:
        db = SessionLocal()
        result = AuditResult()
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'*'*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}      REIMS2 SEED FILES COMPREHENSIVE AUDIT{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'*'*60}{Colors.ENDC}")
        
        # Run all audits
        audit_properties(db, result)
        audit_chart_of_accounts(db, result)
        audit_validation_rules(db, result)
        audit_extraction_templates(db, result)
        audit_lenders(db, result)
        
        # Generate summary report
        success = generate_report(result)
        
        # Exit code
        sys.exit(0 if success and len(result.issues) == 0 else 1)
        
    except Exception as e:
        print(f"\n{Colors.RED}ERROR: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

