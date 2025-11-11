#!/usr/bin/env python3
"""
Verify validation rules alignment between template and implementation
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any

def load_template_validation_rules(json_path: str) -> List[Dict]:
    """Load validation rules from template requirements"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data.get('validation_rules', [])


def extract_seed_validation_rules(seed_data_path: str) -> List[Dict]:
    """Extract validation rules from seed_data.py"""
    with open(seed_data_path, 'r') as f:
        content = f.read()
    
    rules = []
    
    # Find the seed_validation_rules function
    func_match = re.search(r'def seed_validation_rules\(db: Session\):(.*?)(?=\ndef |$)', content, re.DOTALL)
    if not func_match:
        return rules
    
    func_content = func_match.group(1)
    
    # Extract individual rule dictionaries
    rule_pattern = r'\{[^}]*"name":\s*"([^"]+)"[^}]*"description":\s*"([^"]+)"[^}]*"doc_type":\s*"([^"]+)"[^}]*"severity":\s*"([^"]+)"[^}]*\}'
    
    matches = re.finditer(rule_pattern, func_content, re.DOTALL)
    for match in matches:
        name = match.group(1)
        description = match.group(2)
        doc_type = match.group(3)
        severity = match.group(4)
        
        # Only include balance_sheet rules
        if doc_type == "balance_sheet":
            # Extract formula if present
            rule_dict = match.group(0)
            formula_match = re.search(r'"formula":\s*"([^"]+)"', rule_dict)
            formula = formula_match.group(1) if formula_match else None
            
            rules.append({
                "name": name,
                "description": description,
                "doc_type": doc_type,
                "severity": severity,
                "formula": formula
            })
    
    return rules


def compare_validation_rules(template_rules: List[Dict], seed_rules: List[Dict]) -> Dict:
    """Compare template validation rules with implemented rules"""
    
    # Create name-based lookup
    template_by_name = {r['name']: r for r in template_rules}
    seed_by_name = {r['name']: r for r in seed_rules}
    
    template_names = set(template_by_name.keys())
    seed_names = set(seed_by_name.keys())
    
    # Find matches, missing, and extra
    matched = template_names & seed_names
    in_template_only = template_names - seed_names
    in_seed_only = seed_names - template_names
    
    # Analyze mismatches
    mismatches = []
    for name in matched:
        template_rule = template_by_name[name]
        seed_rule = seed_by_name[name]
        
        issues = []
        
        # Compare severity
        template_sev = template_rule.get('severity', '')
        seed_sev = seed_rule.get('severity', '')
        if template_sev != seed_sev:
            issues.append(f"Severity mismatch: template={template_sev}, seed={seed_sev}")
        
        # Compare formulas if present
        template_formula = template_rule.get('rule') or template_rule.get('formula')
        seed_formula = seed_rule.get('formula')
        
        if template_formula and seed_formula:
            # Normalize for comparison
            template_norm = template_formula.replace(' ', '').lower()
            seed_norm = seed_formula.replace(' ', '').lower()
            if template_norm not in seed_norm and seed_norm not in template_norm:
                issues.append(f"Formula difference detected")
        
        if issues:
            mismatches.append({
                "name": name,
                "issues": issues,
                "template": template_rule,
                "seed": seed_rule
            })
    
    return {
        "summary": {
            "total_in_template": len(template_names),
            "total_in_seed": len(seed_names),
            "matched": len(matched),
            "in_template_only": len(in_template_only),
            "in_seed_only": len(in_seed_only),
            "mismatches": len(mismatches)
        },
        "matched_rules": sorted(list(matched)),
        "in_template_only": sorted(list(in_template_only)),
        "in_seed_only": sorted(list(in_seed_only)),
        "mismatches": mismatches
    }


def generate_validation_report(comparison: Dict, template_rules: List[Dict], seed_rules: List[Dict], output_path: str):
    """Generate markdown comparison report"""
    
    report = []
    report.append("# Balance Sheet Validation Rules Verification Report\n\n")
    report.append("## Summary\n\n")
    
    summary = comparison["summary"]
    coverage_pct = (summary["matched"] / summary["total_in_template"] * 100) if summary["total_in_template"] > 0 else 0
    
    report.append(f"- **Template Rules:** {summary['total_in_template']}\n")
    report.append(f"- **Implemented Rules:** {summary['total_in_seed']}\n")
    report.append(f"- **Matched Rules:** {summary['matched']} ({coverage_pct:.1f}% coverage)\n")
    report.append(f"- **In Template Only:** {summary['in_template_only']}\n")
    report.append(f"- **In Seed Only:** {summary['in_seed_only']}\n")
    report.append(f"- **Mismatches:** {summary['mismatches']}\n")
    report.append("\n")
    
    # Status determination
    if summary["in_template_only"] == 0:
        status = "✅ FULLY ALIGNED"
        report.append(f"**Status:** {status}\n\n")
    else:
        status = "⚠️ MISSING RULES"
        report.append(f"**Status:** {status}\n\n")
    
    report.append("---\n\n")
    
    # Template-only rules (MISSING)
    if comparison["in_template_only"]:
        report.append(f"## ❌ Rules in Template Only ({len(comparison['in_template_only'])})\n\n")
        report.append("| Rule Name | Severity | Description |\n")
        report.append("|-----------|----------|-------------|\n")
        
        template_by_name = {r['name']: r for r in template_rules}
        for rule_name in comparison["in_template_only"]:
            rule = template_by_name[rule_name]
            severity = rule.get('severity', 'unknown')
            desc = rule.get('description') or rule.get('rule', '')
            report.append(f"| `{rule_name}` | {severity} | {desc} |\n")
        
        report.append("\n**Action Required:** Implement these validation rules.\n\n")
        report.append("---\n\n")
    
    # Seed-only rules (EXTRA)
    if comparison["in_seed_only"]:
        report.append(f"## ℹ️ Rules in Seed Only ({len(comparison['in_seed_only'])})\n\n")
        report.append("These rules are implemented but not in template (likely comprehensive coverage):\n\n")
        
        seed_by_name = {r['name']: r for r in seed_rules}
        report.append("| Rule Name | Severity | Description |\n")
        report.append("|-----------|----------|-------------|\n")
        
        for rule_name in comparison["in_seed_only"][:10]:  # Show first 10
            rule = seed_by_name[rule_name]
            severity = rule.get('severity', 'unknown')
            desc = rule.get('description', '')
            report.append(f"| `{rule_name}` | {severity} | {desc} |\n")
        
        if len(comparison["in_seed_only"]) > 10:
            report.append(f"\n... and {len(comparison['in_seed_only']) - 10} more\n")
        
        report.append("\n---\n\n")
    
    # Matched rules
    report.append(f"## ✅ Successfully Matched ({summary['matched']} rules)\n\n")
    
    # Group by severity
    template_by_name = {r['name']: r for r in template_rules}
    critical = [r for r in comparison["matched_rules"] if template_by_name[r].get('severity') == 'critical']
    high = [r for r in comparison["matched_rules"] if template_by_name[r].get('severity') == 'high']
    medium = [r for r in comparison["matched_rules"] if template_by_name[r].get('severity') == 'medium']
    
    report.append(f"- **Critical:** {len(critical)}\n")
    report.append(f"- **High:** {len(high)}\n")
    report.append(f"- **Medium:** {len(medium)}\n")
    report.append("\n")
    
    # List critical rules
    if critical:
        report.append("### Critical Rules:\n\n")
        for rule_name in critical:
            rule = template_by_name[rule_name]
            report.append(f"- ✅ `{rule_name}`: {rule.get('description') or rule.get('rule', '')}\n")
        report.append("\n")
    
    report.append("---\n\n")
    
    # Recommendations
    report.append("## Recommendations\n\n")
    
    if summary["in_template_only"] == 0:
        report.append("✅ **No action required.** All template validation rules are implemented.\n\n")
    else:
        report.append("### Action Items:\n\n")
        report.append(f"1. Implement {summary['in_template_only']} missing validation rules\n")
        report.append(f"2. Review {summary['mismatches']} mismatched rules\n")
        report.append("\n")
    
    report.append("---\n\n")
    
    report.append("## Conclusion\n\n")
    
    if summary["in_template_only"] == 0:
        report.append("**Status: VALIDATION COMPLETE ✅**\n\n")
        report.append("All template-specified validation rules are implemented in the system.\n")
    else:
        report.append("**Status: NEEDS ATTENTION ⚠️**\n\n")
        report.append("Some template validation rules are missing. Implement these before production.\n")
    
    # Save report
    with open(output_path, 'w') as f:
        f.write(''.join(report))


def main():
    """Main execution"""
    template_path = "/home/gurpyar/Documents/R/REIMS2/backend/balance_sheet_template_requirements.json"
    seed_data_path = "/home/gurpyar/Documents/R/REIMS2/backend/app/db/seed_data.py"
    output_report_path = "/home/gurpyar/Documents/R/REIMS2/backend/validation_rules_comparison.md"
    output_json_path = "/home/gurpyar/Documents/R/REIMS2/backend/validation_rules_comparison.json"
    
    print("=" * 80)
    print("VERIFYING VALIDATION RULES ALIGNMENT")
    print("=" * 80)
    print()
    
    # Load template rules
    print("📄 Loading template validation rules...")
    template_rules = load_template_validation_rules(template_path)
    print(f"   Found {len(template_rules)} rules in template")
    
    # Extract seed rules
    print("📄 Extracting implemented validation rules...")
    seed_rules = extract_seed_validation_rules(seed_data_path)
    print(f"   Found {len(seed_rules)} balance sheet rules implemented")
    print()
    
    # Compare
    print("🔍 Comparing validation rules...")
    comparison = compare_validation_rules(template_rules, seed_rules)
    print()
    
    # Display summary
    print("=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    print()
    
    summary = comparison["summary"]
    coverage = (summary["matched"] / summary["total_in_template"] * 100) if summary["total_in_template"] > 0 else 0
    
    print(f"Template Rules: {summary['total_in_template']}")
    print(f"Implemented Rules: {summary['total_in_seed']}")
    print(f"Matched: {summary['matched']} ({coverage:.1f}% coverage)")
    print(f"In Template Only (Missing): {summary['in_template_only']}")
    print(f"In Seed Only (Extra): {summary['in_seed_only']}")
    print(f"Mismatches: {summary['mismatches']}")
    print()
    
    # Status
    if summary["in_template_only"] == 0:
        print("✅ STATUS: FULLY ALIGNED")
        print("   All template validation rules are implemented.")
    else:
        print("⚠️ STATUS: MISSING RULES")
        print(f"   {summary['in_template_only']} rules from template are not implemented.")
    
    print()
    
    # Save results
    print("💾 Saving comparison results...")
    
    with open(output_json_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"   ✅ JSON saved to: {output_json_path}")
    
    generate_validation_report(comparison, template_rules, seed_rules, output_report_path)
    print(f"   ✅ Report saved to: {output_report_path}")
    print()
    
    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

