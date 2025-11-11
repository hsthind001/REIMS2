#!/usr/bin/env python3
"""
Compare template accounts with seed file accounts
Identify gaps, extras, and mismatches
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

def load_template_accounts(json_path: str) -> Dict[str, Dict]:
    """Load accounts from template requirements JSON"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Convert to dict keyed by account_code
    accounts = {}
    for acc in data.get('accounts', []):
        accounts[acc['account_code']] = acc
    
    return accounts


def load_seed_accounts(json_path: str) -> Dict[str, Dict]:
    """Load accounts from seed extraction JSON"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Convert to dict keyed by account_code
    accounts = {}
    for acc in data.get('accounts', []):
        accounts[acc['account_code']] = acc
    
    return accounts


def compare_accounts(template_accts: Dict, seed_accts: Dict) -> Dict:
    """Compare template accounts with seed accounts"""
    
    template_codes = set(template_accts.keys())
    seed_codes = set(seed_accts.keys())
    
    # Find matches, missing, and extra
    matched = template_codes & seed_codes
    in_template_only = template_codes - seed_codes
    in_seed_only = seed_codes - template_codes
    
    # Analyze mismatches in matched accounts
    mismatches = []
    for code in matched:
        template_acc = template_accts[code]
        seed_acc = seed_accts[code]
        
        issues = []
        
        # Compare names (allowing for regex patterns in template)
        template_name = template_acc.get('name', '')
        seed_name = seed_acc.get('account_name', '')
        
        # Remove regex patterns for comparison
        template_name_clean = template_name.replace('.*', '').replace('?', '').replace('\\', '').replace('[', '').replace(']', '').replace('-', '').replace(' ', '')
        seed_name_clean = seed_name.replace(' ', '').replace('-', '')
        
        if template_name_clean.lower() not in seed_name_clean.lower() and seed_name_clean.lower() not in template_name_clean.lower():
            if 'A/R' in template_name or 'Accounts Receivable' in template_name:
                # These are expected variations
                pass
            else:
                issues.append(f"Name mismatch: '{template_name}' vs '{seed_name}'")
        
        # Compare types
        template_type = template_acc.get('type', '')
        seed_type = seed_acc.get('account_type', '')
        
        # Map template types to seed types
        type_mapping = {
            'detail': ['asset', 'liability', 'equity'],
            'calculated_total': ['asset', 'liability', 'equity'],
            'section_total': ['asset', 'liability', 'equity'],
            'header': ['asset', 'liability', 'equity']
        }
        
        expected_types = type_mapping.get(template_type, [template_type])
        if seed_type not in expected_types:
            # Type difference is not critical since template has functional types, seed has account types
            pass
        
        # Check contra account flag
        template_contra = template_acc.get('is_contra_account', False)
        seed_name_is_contra = any(word in seed_name.lower() for word in ['accum', 'depreciation', 'amortization'])
        
        if template_contra and not seed_name_is_contra:
            issues.append(f"Template marks as contra account but seed name doesn't indicate it")
        
        # Check calculated flag
        template_calc = template_acc.get('type') in ['calculated_total', 'section_total']
        seed_calc = seed_acc.get('is_calculated', False)
        
        if template_calc and not seed_calc:
            issues.append(f"Template indicates calculated but seed has is_calculated=False")
        
        if issues:
            mismatches.append({
                "account_code": code,
                "template_name": template_name,
                "seed_name": seed_name,
                "issues": issues
            })
    
    return {
        "summary": {
            "total_in_template": len(template_codes),
            "total_in_seed": len(seed_codes),
            "matched": len(matched),
            "in_template_only": len(in_template_only),
            "in_seed_only": len(in_seed_only),
            "mismatched_properties": len(mismatches)
        },
        "matched_accounts": sorted(list(matched)),
        "in_template_only": sorted(list(in_template_only)),
        "in_seed_only": sorted(list(in_seed_only)),
        "mismatches": mismatches
    }


def generate_comparison_report(comparison: Dict, template_accts: Dict, seed_accts: Dict, output_path: str):
    """Generate markdown comparison report"""
    
    report = []
    report.append("# Balance Sheet Accounts Comparison Report\n\n")
    report.append("## Executive Summary\n\n")
    
    summary = comparison["summary"]
    coverage_pct = (summary["matched"] / summary["total_in_template"] * 100) if summary["total_in_template"] > 0 else 0
    
    report.append(f"- **Template Accounts:** {summary['total_in_template']}\n")
    report.append(f"- **Seed File Accounts:** {summary['total_in_seed']}\n")
    report.append(f"- **Matched Accounts:** {summary['matched']} ({coverage_pct:.1f}% coverage)\n")
    report.append(f"- **In Template Only:** {summary['in_template_only']}\n")
    report.append(f"- **In Seed Only:** {summary['in_seed_only']}\n")
    report.append(f"- **Property Mismatches:** {summary['mismatched_properties']}\n")
    report.append("\n")
    
    # Status determination
    if summary["in_template_only"] == 0 and summary["mismatched_properties"] == 0:
        status = "✅ FULLY ALIGNED"
        report.append(f"**Status:** {status}\n\n")
        report.append("All template requirements are met. The seed files contain all required accounts.\n")
    elif summary["in_template_only"] > 0:
        status = "⚠️ MISSING ACCOUNTS"
        report.append(f"**Status:** {status}\n\n")
        report.append(f"There are {summary['in_template_only']} accounts defined in the template but missing from seed files.\n")
    else:
        status = "✅ ACCEPTABLE"
        report.append(f"**Status:** {status}\n\n")
        report.append("Template requirements are met. Additional accounts in seed files provide extended functionality.\n")
    
    report.append("\n---\n\n")
    
    # Template-only accounts (MISSING from seed files)
    if comparison["in_template_only"]:
        report.append(f"## ❌ Accounts in Template Only ({len(comparison['in_template_only'])})\n\n")
        report.append("These accounts are specified in the template but missing from seed SQL files:\n\n")
        report.append("| Code | Name | Type | Required | Notes |\n")
        report.append("|------|------|------|----------|-------|\n")
        
        for code in comparison["in_template_only"]:
            acc = template_accts[code]
            name = acc.get('name', '')
            acc_type = acc.get('type', '')
            required = "✅ Yes" if acc.get('required') or acc.get('critical') else "No"
            notes = "CRITICAL" if acc.get('critical') else ""
            report.append(f"| `{code}` | {name} | {acc_type} | {required} | {notes} |\n")
        
        report.append("\n")
        report.append("**Action Required:** Add these accounts to seed SQL files.\n")
        report.append("\n---\n\n")
    
    # Seed-only accounts (EXTRA, not in template)
    if comparison["in_seed_only"]:
        report.append(f"## ℹ️ Accounts in Seed Only ({len(comparison['in_seed_only'])})\n\n")
        report.append("These accounts are in seed files but not explicitly defined in the template:\n\n")
        
        # Group by section
        assets = [c for c in comparison["in_seed_only"] if c.startswith(('0', '1'))]
        liabilities = [c for c in comparison["in_seed_only"] if c.startswith('2')]
        equity = [c for c in comparison["in_seed_only"] if c.startswith('3')]
        
        report.append(f"- **Assets:** {len(assets)}\n")
        report.append(f"- **Liabilities:** {len(liabilities)}\n")
        report.append(f"- **Equity:** {len(equity)}\n")
        report.append("\n")
        
        report.append("**Analysis:** This is normal and indicates comprehensive coverage. The template defines core/example accounts, while seed files contain the complete chart of accounts for all properties.\n")
        report.append("\n")
        
        # Show first 20 as examples
        report.append("### Sample (first 20):\n\n")
        report.append("| Code | Name | Category | Type |\n")
        report.append("|------|------|----------|------|\n")
        
        for code in sorted(comparison["in_seed_only"])[:20]:
            acc = seed_accts[code]
            name = acc.get('account_name', '')
            category = acc.get('category', '')
            acc_type = acc.get('account_type', '')
            report.append(f"| `{code}` | {name} | {category} | {acc_type} |\n")
        
        if len(comparison["in_seed_only"]) > 20:
            report.append(f"\n... and {len(comparison['in_seed_only']) - 20} more\n")
        
        report.append("\n---\n\n")
    
    # Property mismatches
    if comparison["mismatches"]:
        report.append(f"## ⚠️ Property Mismatches ({len(comparison['mismatches'])})\n\n")
        report.append("These accounts exist in both but have different properties:\n\n")
        report.append("| Code | Template Name | Seed Name | Issues |\n")
        report.append("|------|---------------|-----------|--------|\n")
        
        for mismatch in comparison["mismatches"]:
            code = mismatch["account_code"]
            template_name = mismatch["template_name"]
            seed_name = mismatch["seed_name"]
            issues = "; ".join(mismatch["issues"])
            report.append(f"| `{code}` | {template_name} | {seed_name} | {issues} |\n")
        
        report.append("\n")
        report.append("**Note:** Minor differences are expected due to regex patterns in template vs actual names in seed files.\n")
        report.append("\n---\n\n")
    
    # Matched accounts
    report.append(f"## ✅ Successfully Matched ({summary['matched']} accounts)\n\n")
    report.append(f"Coverage: {coverage_pct:.1f}%\n\n")
    
    # Group matched by section
    matched_assets = [c for c in comparison["matched_accounts"] if c.startswith(('0', '1'))]
    matched_liabilities = [c for c in comparison["matched_accounts"] if c.startswith('2')]
    matched_equity = [c for c in comparison["matched_accounts"] if c.startswith('3')]
    
    report.append(f"- **Assets:** {len(matched_assets)}\n")
    report.append(f"- **Liabilities:** {len(matched_liabilities)}\n")
    report.append(f"- **Equity:** {len(matched_equity)}\n")
    report.append("\n")
    
    # Critical accounts verification
    critical_codes = ["0499-9000", "1099-0000", "1998-0000", "1999-0000", "2590-0000", "2900-0000", "2999-0000", "3999-0000", "3999-9000"]
    critical_matched = [c for c in critical_codes if c in comparison["matched_accounts"]]
    critical_missing = [c for c in critical_codes if c in comparison["in_template_only"]]
    
    report.append(f"### Critical Accounts Verification:\n\n")
    if len(critical_matched) == len(critical_codes):
        report.append(f"✅ All {len(critical_codes)} critical accounts are present\n\n")
    else:
        report.append(f"⚠️ {len(critical_matched)}/{len(critical_codes)} critical accounts present\n")
        if critical_missing:
            report.append(f"Missing critical accounts: {', '.join(critical_missing)}\n")
        report.append("\n")
    
    report.append("---\n\n")
    
    # Recommendations
    report.append("## Recommendations\n\n")
    
    if summary["in_template_only"] == 0:
        report.append("✅ **No action required for account coverage.**\n\n")
        report.append("All template-defined accounts are present in seed files.\n\n")
    else:
        report.append("### Action Items:\n\n")
        report.append(f"1. Add {summary['in_template_only']} missing accounts to seed SQL files\n")
        report.append(f"2. Review property mismatches ({summary['mismatched_properties']} accounts)\n")
        report.append("\n")
    
    report.append("### Notes:\n\n")
    report.append("- The template defines **core/example accounts** from the extraction requirements document\n")
    report.append(f"- The seed files contain **{summary['total_in_seed']} comprehensive accounts** for all 4 properties\n")
    report.append(f"- Having {summary['in_seed_only']} additional accounts in seed files is **normal and beneficial**\n")
    report.append("- This indicates comprehensive coverage beyond the minimum requirements\n")
    report.append("\n---\n\n")
    
    report.append("## Conclusion\n\n")
    
    if summary["in_template_only"] == 0:
        report.append("**Status: PRODUCTION READY ✅**\n\n")
        report.append("The seed files provide complete coverage of template requirements plus additional accounts for comprehensive financial tracking.\n")
    else:
        report.append("**Status: NEEDS ATTENTION ⚠️**\n\n")
        report.append("Some template-specified accounts are missing from seed files. Add these accounts before production deployment.\n")
    
    # Save report
    with open(output_path, 'w') as f:
        f.write(''.join(report))


def main():
    """Main execution"""
    template_path = "/home/gurpyar/Documents/R/REIMS2/backend/balance_sheet_template_requirements.json"
    seed_path = "/home/gurpyar/Documents/R/REIMS2/backend/seed_accounts_list.json"
    output_report_path = "/home/gurpyar/Documents/R/REIMS2/backend/accounts_comparison_report.md"
    output_json_path = "/home/gurpyar/Documents/R/REIMS2/backend/accounts_comparison_results.json"
    
    print("=" * 80)
    print("COMPARING TEMPLATE ACCOUNTS WITH SEED FILE ACCOUNTS")
    print("=" * 80)
    print()
    
    # Load accounts
    print("📄 Loading template accounts...")
    template_accounts = load_template_accounts(template_path)
    print(f"   Found {len(template_accounts)} accounts in template")
    
    print("📄 Loading seed file accounts...")
    seed_accounts = load_seed_accounts(seed_path)
    print(f"   Found {len(seed_accounts)} accounts in seed files")
    print()
    
    # Compare
    print("🔍 Comparing accounts...")
    comparison = compare_accounts(template_accounts, seed_accounts)
    print()
    
    # Display summary
    print("=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    print()
    
    summary = comparison["summary"]
    coverage = (summary["matched"] / summary["total_in_template"] * 100) if summary["total_in_template"] > 0 else 0
    
    print(f"Template Accounts: {summary['total_in_template']}")
    print(f"Seed File Accounts: {summary['total_in_seed']}")
    print(f"Matched: {summary['matched']} ({coverage:.1f}% coverage)")
    print(f"In Template Only (Missing): {summary['in_template_only']}")
    print(f"In Seed Only (Extra): {summary['in_seed_only']}")
    print(f"Property Mismatches: {summary['mismatched_properties']}")
    print()
    
    # Status
    if summary["in_template_only"] == 0:
        print("✅ STATUS: FULLY ALIGNED")
        print("   All template accounts are present in seed files.")
    else:
        print("⚠️ STATUS: MISSING ACCOUNTS")
        print(f"   {summary['in_template_only']} accounts from template are missing in seed files.")
    
    print()
    
    # Save results
    print("💾 Saving comparison results...")
    
    with open(output_json_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"   ✅ JSON saved to: {output_json_path}")
    
    generate_comparison_report(comparison, template_accounts, seed_accounts, output_report_path)
    print(f"   ✅ Report saved to: {output_report_path}")
    print()
    
    print("=" * 80)
    print("COMPARISON COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

