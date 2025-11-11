#!/usr/bin/env python3
"""
Verify extraction template and fuzzy matching configuration
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any

def load_template_requirements(json_path: str) -> Dict:
    """Load template requirements"""
    with open(json_path, 'r') as f:
        return json.load(f)


def extract_sql_extraction_template(sql_path: str) -> Dict:
    """Extract balance sheet template from SQL seed file"""
    with open(sql_path, 'r') as f:
        content = f.read()
    
    # Find the balance_sheet template INSERT
    pattern = r"INSERT INTO extraction_templates.*?template_name.*?'(standard_balance_sheet)'.*?document_type.*?'balance_sheet'.*?template_structure.*?'({.*?})'::jsonb.*?keywords.*?ARRAY\[(.*?)\].*?extraction_rules.*?'({.*?})'::jsonb"
    
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}
    
    try:
        template_structure = json.loads(match.group(2).replace("'", '"'))
        keywords_raw = match.group(3)
        keywords = [k.strip().strip("'").strip('"') for k in keywords_raw.split(',')]
        extraction_rules = json.loads(match.group(4).replace("'", '"'))
        
        return {
            "template_name": match.group(1),
            "document_type": "balance_sheet",
            "template_structure": template_structure,
            "keywords": keywords,
            "extraction_rules": extraction_rules
        }
    except Exception as e:
        print(f"Error parsing SQL template: {e}")
        return {}


def extract_fuzzy_matching_config(parser_file_path: str) -> Dict:
    """Extract fuzzy matching configuration from parser"""
    try:
        with open(parser_file_path, 'r') as f:
            content = f.read()
        
        config = {}
        
        # Look for fuzzy matching threshold
        threshold_pattern = r'FUZZY_MATCH_THRESHOLD\s*=\s*(\d+)|fuzzy.*?threshold.*?(\d+)|threshold.*?(\d+)'
        threshold_matches = re.finditer(threshold_pattern, content, re.IGNORECASE)
        
        thresholds = []
        for match in threshold_matches:
            for group in match.groups():
                if group:
                    thresholds.append(int(group))
        
        if thresholds:
            config['threshold_found'] = thresholds
            config['primary_threshold'] = max(thresholds)  # Use highest threshold found
        
        # Look for Levenshtein distance usage
        if 'levenshtein' in content.lower() or 'fuzz' in content.lower():
            config['uses_levenshtein'] = True
        else:
            config['uses_levenshtein'] = False
        
        # Check for fuzzy matching functions
        fuzzy_funcs = re.findall(r'def\s+(fuzzy_match\w*|match_account\w*|find_best_match\w*)\s*\(', content)
        config['fuzzy_functions'] = fuzzy_funcs
        
        return config
    except FileNotFoundError:
        return {"error": "Parser file not found"}


def verify_extraction_logic(template_reqs: Dict, sql_template: Dict, fuzzy_config: Dict) -> Dict:
    """Verify extraction logic alignment"""
    
    results = {
        "template_structure": {"status": "unknown", "details": []},
        "keywords": {"status": "unknown", "details": []},
        "fuzzy_matching": {"status": "unknown", "details": []},
        "extraction_rules": {"status": "unknown", "details": []},
        "summary": {}
    }
    
    # Verify template structure
    if sql_template and 'template_structure' in sql_template:
        structure = sql_template['template_structure']
        
        # Check required sections
        required_sections = ['ASSETS', 'LIABILITIES', 'CAPITAL']
        if 'sections' in structure:
            found_sections = [s['name'] for s in structure['sections']]
            all_present = all(req in found_sections for req in required_sections)
            
            results["template_structure"]["status"] = "✅ COMPLETE" if all_present else "⚠️ INCOMPLETE"
            results["template_structure"]["details"].append(f"Sections: {', '.join(found_sections)}")
            results["template_structure"]["found_sections"] = found_sections
            results["template_structure"]["required_sections"] = required_sections
        else:
            results["template_structure"]["status"] = "❌ MISSING"
            results["template_structure"]["details"].append("No sections found")
    else:
        results["template_structure"]["status"] = "❌ MISSING"
        results["template_structure"]["details"].append("Template structure not found")
    
    # Verify keywords
    if sql_template and 'keywords' in sql_template:
        sql_keywords = set([k.lower() for k in sql_template['keywords']])
        template_keywords = set([k.lower() for k in template_reqs['keywords'].get('required_keywords', [])])
        
        matched = sql_keywords & template_keywords
        coverage = len(matched) / len(template_keywords) * 100 if template_keywords else 0
        
        results["keywords"]["status"] = "✅ COMPLETE" if coverage >= 80 else "⚠️ PARTIAL"
        results["keywords"]["details"].append(f"Coverage: {coverage:.1f}% ({len(matched)}/{len(template_keywords)} keywords)")
        results["keywords"]["sql_keywords"] = list(sql_keywords)
        results["keywords"]["template_keywords"] = list(template_keywords)
        results["keywords"]["matched"] = list(matched)
    else:
        results["keywords"]["status"] = "❌ MISSING"
        results["keywords"]["details"].append("Keywords not found")
    
    # Verify fuzzy matching (CRITICAL - must be 85%+)
    template_threshold = template_reqs['extraction_rules'].get('fuzzy_matching_threshold', 85)
    
    if fuzzy_config and 'primary_threshold' in fuzzy_config:
        actual_threshold = fuzzy_config['primary_threshold']
        
        if actual_threshold >= template_threshold:
            results["fuzzy_matching"]["status"] = "✅ CORRECT"
            results["fuzzy_matching"]["details"].append(f"Threshold: {actual_threshold}% (required: {template_threshold}%)")
        else:
            results["fuzzy_matching"]["status"] = "❌ TOO LOW"
            results["fuzzy_matching"]["details"].append(f"Threshold: {actual_threshold}% (required: {template_threshold}%)")
        
        results["fuzzy_matching"]["actual_threshold"] = actual_threshold
        results["fuzzy_matching"]["required_threshold"] = template_threshold
        results["fuzzy_matching"]["uses_levenshtein"] = fuzzy_config.get('uses_levenshtein', False)
        results["fuzzy_matching"]["functions"] = fuzzy_config.get('fuzzy_functions', [])
    elif fuzzy_config and 'threshold_found' in fuzzy_config:
        thresholds = fuzzy_config['threshold_found']
        results["fuzzy_matching"]["status"] = "⚠️ MULTIPLE THRESHOLDS"
        results["fuzzy_matching"]["details"].append(f"Found thresholds: {thresholds}")
        results["fuzzy_matching"]["threshold_found"] = thresholds
    else:
        results["fuzzy_matching"]["status"] = "❌ NOT FOUND"
        results["fuzzy_matching"]["details"].append("Could not find fuzzy matching threshold")
    
    # Verify extraction rules
    if sql_template and 'extraction_rules' in sql_template:
        rules = sql_template['extraction_rules']
        
        checks = []
        
        # Check for confidence weights
        if 'confidence_weights' in rules:
            checks.append("✅ Confidence weights defined")
        else:
            checks.append("⚠️ No confidence weights")
        
        # Check for fuzzy match threshold in rules
        if 'fuzzy_match_threshold' in rules:
            threshold = rules['fuzzy_match_threshold']
            if threshold >= template_threshold:
                checks.append(f"✅ Fuzzy match threshold: {threshold}")
            else:
                checks.append(f"❌ Fuzzy match threshold too low: {threshold} (need {template_threshold})")
        
        # Check for section detection
        if 'section_detection' in rules:
            checks.append("✅ Section detection configured")
        else:
            checks.append("⚠️ No section detection")
        
        results["extraction_rules"]["status"] = "✅ PRESENT"
        results["extraction_rules"]["details"] = checks
        results["extraction_rules"]["rules"] = rules
    else:
        results["extraction_rules"]["status"] = "❌ MISSING"
        results["extraction_rules"]["details"] = ["Extraction rules not found"]
    
    # Summary
    statuses = [
        results["template_structure"]["status"],
        results["keywords"]["status"],
        results["fuzzy_matching"]["status"],
        results["extraction_rules"]["status"]
    ]
    
    if all("✅" in s for s in statuses):
        overall = "✅ FULLY ALIGNED"
    elif any("❌" in s for s in statuses):
        overall = "❌ CRITICAL ISSUES"
    else:
        overall = "⚠️ NEEDS ATTENTION"
    
    results["summary"] = {
        "overall_status": overall,
        "template_structure": results["template_structure"]["status"],
        "keywords": results["keywords"]["status"],
        "fuzzy_matching": results["fuzzy_matching"]["status"],
        "extraction_rules": results["extraction_rules"]["status"]
    }
    
    return results


def generate_extraction_report(results: Dict, output_path: str):
    """Generate markdown report"""
    
    report = []
    report.append("# Balance Sheet Extraction Logic Verification Report\n\n")
    report.append(f"## Overall Status: {results['summary']['overall_status']}\n\n")
    report.append("---\n\n")
    
    # Template Structure
    report.append("## 1. Template Structure\n\n")
    report.append(f"**Status:** {results['template_structure']['status']}\n\n")
    
    for detail in results['template_structure']['details']:
        report.append(f"- {detail}\n")
    
    if 'found_sections' in results['template_structure']:
        report.append(f"\n**Found Sections:**\n")
        for section in results['template_structure']['found_sections']:
            report.append(f"- {section}\n")
    
    report.append("\n---\n\n")
    
    # Keywords
    report.append("## 2. Keywords\n\n")
    report.append(f"**Status:** {results['keywords']['status']}\n\n")
    
    for detail in results['keywords']['details']:
        report.append(f"- {detail}\n")
    
    if 'matched' in results['keywords']:
        report.append(f"\n**Matched Keywords:**\n")
        for kw in sorted(results['keywords']['matched'])[:10]:
            report.append(f"- {kw}\n")
        if len(results['keywords']['matched']) > 10:
            report.append(f"- ... and {len(results['keywords']['matched']) - 10} more\n")
    
    report.append("\n---\n\n")
    
    # Fuzzy Matching (CRITICAL)
    report.append("## 3. Fuzzy Matching Configuration ⚠️ CRITICAL\n\n")
    report.append(f"**Status:** {results['fuzzy_matching']['status']}\n\n")
    
    for detail in results['fuzzy_matching']['details']:
        report.append(f"- {detail}\n")
    
    if 'actual_threshold' in results['fuzzy_matching']:
        actual = results['fuzzy_matching']['actual_threshold']
        required = results['fuzzy_matching']['required_threshold']
        
        report.append(f"\n**Configuration:**\n")
        report.append(f"- **Required Threshold:** {required}%\n")
        report.append(f"- **Actual Threshold:** {actual}%\n")
        report.append(f"- **Uses Levenshtein:** {results['fuzzy_matching'].get('uses_levenshtein', 'Unknown')}\n")
        
        if results['fuzzy_matching'].get('functions'):
            report.append(f"- **Fuzzy Functions:** {', '.join(results['fuzzy_matching']['functions'])}\n")
        
        if actual < required:
            report.append(f"\n⚠️ **ACTION REQUIRED:** Increase fuzzy matching threshold from {actual}% to {required}%\n")
    
    report.append("\n---\n\n")
    
    # Extraction Rules
    report.append("## 4. Extraction Rules\n\n")
    report.append(f"**Status:** {results['extraction_rules']['status']}\n\n")
    
    for detail in results['extraction_rules']['details']:
        report.append(f"{detail}\n")
    
    report.append("\n---\n\n")
    
    # Recommendations
    report.append("## Recommendations\n\n")
    
    issues = []
    if "❌" in results['summary']['fuzzy_matching'] or "⚠️" in results['summary']['fuzzy_matching']:
        issues.append("**CRITICAL:** Verify and adjust fuzzy matching threshold to meet template requirements (85%+)")
    
    if "❌" in results['summary']['template_structure']:
        issues.append("Fix template structure to include all required sections")
    
    if "❌" in results['summary']['keywords']:
        issues.append("Add missing keywords to template")
    
    if "❌" in results['summary']['extraction_rules']:
        issues.append("Configure extraction rules properly")
    
    if issues:
        for i, issue in enumerate(issues, 1):
            report.append(f"{i}. {issue}\n")
    else:
        report.append("✅ No critical issues found. Extraction logic is properly configured.\n")
    
    report.append("\n---\n\n")
    report.append("## Conclusion\n\n")
    
    if results['summary']['overall_status'] == "✅ FULLY ALIGNED":
        report.append("**Status: PRODUCTION READY ✅**\n\n")
        report.append("Extraction logic is properly configured and aligned with template requirements.\n")
    elif results['summary']['overall_status'] == "⚠️ NEEDS ATTENTION":
        report.append("**Status: NEEDS ATTENTION ⚠️**\n\n")
        report.append("Some configurations need adjustment. Address the issues above before production deployment.\n")
    else:
        report.append("**Status: CRITICAL ISSUES ❌**\n\n")
        report.append("Critical configuration issues found. Must be fixed before production deployment.\n")
    
    # Save report
    with open(output_path, 'w') as f:
        f.write(''.join(report))


def main():
    """Main execution"""
    template_req_path = "/home/gurpyar/Documents/R/REIMS2/backend/balance_sheet_template_requirements.json"
    sql_template_path = "/home/gurpyar/Documents/R/REIMS2/backend/scripts/seed_extraction_templates.sql"
    parser_path = "/home/gurpyar/Documents/R/REIMS2/backend/app/utils/financial_table_parser.py"
    output_report_path = "/home/gurpyar/Documents/R/REIMS2/backend/extraction_template_verification.md"
    output_json_path = "/home/gurpyar/Documents/R/REIMS2/backend/extraction_template_verification.json"
    
    print("=" * 80)
    print("VERIFYING EXTRACTION LOGIC AND FUZZY MATCHING")
    print("=" * 80)
    print()
    
    # Load template requirements
    print("📄 Loading template requirements...")
    template_reqs = load_template_requirements(template_req_path)
    print(f"   Required fuzzy matching threshold: {template_reqs['extraction_rules'].get('fuzzy_matching_threshold')}%")
    print()
    
    # Extract SQL template
    print("📄 Extracting SQL extraction template...")
    sql_template = extract_sql_extraction_template(sql_template_path)
    if sql_template:
        print(f"   ✅ Found {sql_template.get('template_name', 'unknown')} template")
    else:
        print("   ⚠️ Could not extract SQL template")
    print()
    
    # Extract fuzzy matching config
    print("📄 Extracting fuzzy matching configuration...")
    fuzzy_config = extract_fuzzy_matching_config(parser_path)
    if 'error' not in fuzzy_config:
        print(f"   Found {len(fuzzy_config.get('fuzzy_functions', []))} fuzzy matching functions")
        if 'primary_threshold' in fuzzy_config:
            print(f"   Primary threshold: {fuzzy_config['primary_threshold']}%")
    else:
        print(f"   ⚠️ {fuzzy_config['error']}")
    print()
    
    # Verify
    print("🔍 Verifying extraction logic alignment...")
    results = verify_extraction_logic(template_reqs, sql_template, fuzzy_config)
    print()
    
    # Display summary
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()
    print(f"Overall Status: {results['summary']['overall_status']}")
    print()
    print("Component Status:")
    print(f"  - Template Structure: {results['summary']['template_structure']}")
    print(f"  - Keywords: {results['summary']['keywords']}")
    print(f"  - Fuzzy Matching: {results['summary']['fuzzy_matching']}")
    print(f"  - Extraction Rules: {results['summary']['extraction_rules']}")
    print()
    
    # Save results
    print("💾 Saving verification results...")
    
    with open(output_json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"   ✅ JSON saved to: {output_json_path}")
    
    generate_extraction_report(results, output_report_path)
    print(f"   ✅ Report saved to: {output_report_path}")
    print()
    
    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

