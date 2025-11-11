#!/usr/bin/env python3
"""
Extract all accounts from Balance Sheet seed SQL files
"""
import json
import re
import csv
from pathlib import Path
from typing import List, Dict, Any

def parse_sql_insert(sql_content: str) -> List[Dict[str, Any]]:
    """Parse INSERT statements from SQL file"""
    accounts = []
    
    # Pattern to match INSERT INTO chart_of_accounts (...) VALUES
    # Handles multi-line VALUES sections
    pattern = r"INSERT INTO chart_of_accounts.*?VALUES\s*\n(.*?)(?:ON CONFLICT|;)"
    
    matches = re.finditer(pattern, sql_content, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        values_section = match.group(1)
        
        # Extract individual value tuples
        # Pattern: ('code', 'name', 'type', ...)
        tuple_pattern = r"\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']*)',\s*'([^']*)',\s*ARRAY\[([^\]]*)\],\s*(TRUE|FALSE),\s*(\d+),\s*(TRUE|FALSE),\s*'([^']*)'\)"
        
        tuple_matches = re.finditer(tuple_pattern, values_section, re.MULTILINE)
        
        for tuple_match in tuple_matches:
            account = {
                "account_code": tuple_match.group(1),
                "account_name": tuple_match.group(2),
                "account_type": tuple_match.group(3),
                "category": tuple_match.group(4),
                "subcategory": tuple_match.group(5) if tuple_match.group(5) else None,
                "parent_account_code": tuple_match.group(6) if tuple_match.group(6) else None,
                "document_types": [dt.strip().strip("'") for dt in tuple_match.group(7).split(',') if dt.strip()],
                "is_calculated": tuple_match.group(8) == 'TRUE',
                "display_order": int(tuple_match.group(9)),
                "is_active": tuple_match.group(10) == 'TRUE',
                "expected_sign": tuple_match.group(11) if tuple_match.group(11) else 'positive'
            }
            accounts.append(account)
    
    return accounts


def categorize_accounts(accounts: List[Dict]) -> Dict[str, Any]:
    """Categorize and analyze accounts"""
    stats = {
        "total": len(accounts),
        "by_type": {},
        "by_category": {},
        "by_section": {},
        "by_subcategory": {},
        "calculated_accounts": [],
        "contra_accounts": [],
        "critical_accounts": []
    }
    
    # Identify critical accounts (totals and grand totals)
    critical_codes = [
        "0499-9000",  # Total Current Assets
        "1099-0000",  # Total Property & Equipment
        "1998-0000",  # Total Other Assets
        "1999-0000",  # TOTAL ASSETS
        "2590-0000",  # Total Current Liabilities
        "2900-0000",  # Total Long Term Liabilities
        "2999-0000",  # TOTAL LIABILITIES
        "3999-0000",  # TOTAL CAPITAL
        "3999-9000"   # TOTAL LIABILITIES & CAPITAL
    ]
    
    for account in accounts:
        # Type
        acc_type = account["account_type"]
        stats["by_type"][acc_type] = stats["by_type"].get(acc_type, 0) + 1
        
        # Category
        category = account["category"]
        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        # Section (based on account code range)
        code = account["account_code"]
        if code.startswith(('0', '1')):
            section = "ASSETS"
        elif code.startswith('2'):
            section = "LIABILITIES"
        elif code.startswith('3'):
            section = "CAPITAL/EQUITY"
        else:
            section = "OTHER"
        stats["by_section"][section] = stats["by_section"].get(section, 0) + 1
        
        # Subcategory
        if account["subcategory"]:
            stats["by_subcategory"][account["subcategory"]] = stats["by_subcategory"].get(account["subcategory"], 0) + 1
        
        # Calculated accounts
        if account["is_calculated"]:
            stats["calculated_accounts"].append(account["account_code"])
        
        # Contra accounts (based on naming)
        if any(keyword in account["account_name"].lower() for keyword in ['accum', 'amort', 'depreciation', 'amortization']):
            stats["contra_accounts"].append(account["account_code"])
        
        # Critical accounts
        if code in critical_codes:
            stats["critical_accounts"].append(account["account_code"])
    
    return stats


def save_to_csv(accounts: List[Dict], csv_path: str):
    """Save accounts to CSV file"""
    if not accounts:
        return
    
    # Define field order
    fieldnames = [
        "account_code",
        "account_name",
        "account_type",
        "category",
        "subcategory",
        "parent_account_code",
        "document_types",
        "is_calculated",
        "display_order",
        "is_active",
        "expected_sign"
    ]
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for account in accounts:
            row = account.copy()
            # Convert array to string
            row["document_types"] = ",".join(row["document_types"])
            writer.writerow(row)


def main():
    """Main execution"""
    sql_file1 = "/home/gurpyar/Documents/R/REIMS2/backend/scripts/seed_balance_sheet_template_accounts.sql"
    sql_file2 = "/home/gurpyar/Documents/R/REIMS2/backend/scripts/seed_balance_sheet_template_accounts_part2.sql"
    output_csv = "/home/gurpyar/Documents/R/REIMS2/backend/seed_accounts_list.csv"
    output_json = "/home/gurpyar/Documents/R/REIMS2/backend/seed_accounts_list.json"
    
    print("=" * 80)
    print("EXTRACTING ACCOUNTS FROM SEED SQL FILES")
    print("=" * 80)
    print()
    
    all_accounts = []
    
    # Parse first file
    print(f"📄 Parsing: {Path(sql_file1).name}")
    with open(sql_file1, 'r') as f:
        sql_content1 = f.read()
    accounts1 = parse_sql_insert(sql_content1)
    print(f"   Found {len(accounts1)} accounts")
    all_accounts.extend(accounts1)
    
    # Parse second file
    print(f"📄 Parsing: {Path(sql_file2).name}")
    with open(sql_file2, 'r') as f:
        sql_content2 = f.read()
    accounts2 = parse_sql_insert(sql_content2)
    print(f"   Found {len(accounts2)} accounts")
    all_accounts.extend(accounts2)
    
    print()
    print(f"✅ Total accounts extracted: {len(all_accounts)}")
    print()
    
    # Categorize accounts
    print("📊 Analyzing accounts...")
    stats = categorize_accounts(all_accounts)
    
    print()
    print("=" * 80)
    print("ACCOUNT STATISTICS")
    print("=" * 80)
    print()
    print(f"Total Accounts: {stats['total']}")
    print()
    
    print("By Type:")
    for acc_type, count in sorted(stats["by_type"].items()):
        print(f"  - {acc_type}: {count}")
    print()
    
    print("By Category:")
    for category, count in sorted(stats["by_category"].items()):
        print(f"  - {category}: {count}")
    print()
    
    print("By Section:")
    for section, count in sorted(stats["by_section"].items()):
        print(f"  - {section}: {count}")
    print()
    
    print(f"Special Account Types:")
    print(f"  - Calculated/Total accounts: {len(stats['calculated_accounts'])}")
    print(f"  - Contra accounts: {len(stats['contra_accounts'])}")
    print(f"  - Critical accounts: {len(stats['critical_accounts'])}")
    print()
    
    print("Critical Accounts (Totals):")
    for code in stats['critical_accounts']:
        account = next(acc for acc in all_accounts if acc['account_code'] == code)
        print(f"  - {code}: {account['account_name']}")
    print()
    
    # Save to files
    print("💾 Saving extracted accounts...")
    save_to_csv(all_accounts, output_csv)
    print(f"   ✅ CSV saved to: {output_csv}")
    
    with open(output_json, 'w') as f:
        json.dump({
            "metadata": {
                "total_accounts": len(all_accounts),
                "source_files": [sql_file1, sql_file2]
            },
            "accounts": all_accounts,
            "statistics": stats
        }, f, indent=2)
    print(f"   ✅ JSON saved to: {output_json}")
    print()
    
    # Account code ranges
    print("📋 Account Code Ranges:")
    print(f"  - Assets (0100-1999): {sum(1 for acc in all_accounts if acc['account_code'].startswith(('0', '1')))}")
    print(f"  - Liabilities (2000-2999): {sum(1 for acc in all_accounts if acc['account_code'].startswith('2'))}")
    print(f"  - Capital/Equity (3000-3999): {sum(1 for acc in all_accounts if acc['account_code'].startswith('3'))}")
    print()
    
    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

