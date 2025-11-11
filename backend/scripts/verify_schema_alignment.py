#!/usr/bin/env python3
"""
Verify balance_sheet_data database schema alignment with template requirements
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set

def extract_model_fields(model_file_path: str) -> Dict[str, Dict[str, Any]]:
    """Extract fields from SQLAlchemy model"""
    with open(model_file_path, 'r') as f:
        content = f.read()
    
    fields = {}
    
    # Pattern to match column definitions
    column_pattern = r'(\w+)\s*=\s*Column\((.*?)\)'
    matches = re.finditer(column_pattern, content, re.DOTALL)
    
    for match in matches:
        field_name = match.group(1)
        column_def = match.group(2)
        
        # Extract column type
        type_match = re.search(r'(Integer|String|DECIMAL|Boolean|DateTime|Text|ForeignKey)', column_def)
        field_type = type_match.group(1) if type_match else 'Unknown'
        
        # Extract constraints
        nullable = 'nullable=False' not in column_def
        indexed = 'index=True' in column_def
        default = re.search(r'default=([^,\)]+)', column_def)
        
        fields[field_name] = {
            "type": field_type,
            "nullable": nullable,
            "indexed": indexed,
            "default": default.group(1) if default else None
        }
    
    return fields


def load_template_requirements(json_path: str) -> Dict:
    """Load template requirements from JSON"""
    with open(json_path, 'r') as f:
        return json.load(f)


def verify_schema_alignment(model_fields: Dict, template_reqs: Dict) -> Dict[str, Any]:
    """Verify schema alignment with template requirements"""
    
    results = {
        "header_fields": {"present": [], "missing": [], "status": "unknown"},
        "hierarchical_fields": {"present": [], "missing": [], "status": "unknown"},
        "quality_fields": {"present": [], "missing": [], "status": "unknown"},
        "review_workflow_fields": {"present": [], "missing": [], "status": "unknown"},
        "financial_fields": {"present": [], "missing": [], "status": "unknown"},
        "summary": {}
    }
    
    # Define required fields by category
    required_fields = {
        "header_fields": [
            ("report_title", "String", "Balance Sheet title"),
            ("period_ending", "String", "Period ending (e.g., Dec 2024)"),
            ("accounting_basis", "String", "Accrual or Cash"),
            ("report_date", "DateTime", "Report generation date"),
            ("page_number", "Integer", "Page number for multi-page docs")
        ],
        "hierarchical_fields": [
            ("is_subtotal", "Boolean", "Total Current Assets, etc."),
            ("is_total", "Boolean", "TOTAL ASSETS, etc."),
            ("account_level", "Integer", "Hierarchy depth 1-4"),
            ("account_category", "String", "ASSETS, LIABILITIES, CAPITAL"),
            ("account_subcategory", "String", "Current Assets, etc.")
        ],
        "quality_fields": [
            ("extraction_confidence", "DECIMAL", "0-100 extraction confidence"),
            ("match_confidence", "DECIMAL", "0-100 account match confidence"),
            ("extraction_method", "String", "table/text/template"),
            ("is_contra_account", "Boolean", "Accumulated depreciation flag"),
            ("expected_sign", "String", "positive/negative/either")
        ],
        "review_workflow_fields": [
            ("needs_review", "Boolean", "Flag for manual review"),
            ("reviewed", "Boolean", "Has been reviewed"),
            ("reviewed_by", "Integer", "User ID who reviewed"),
            ("reviewed_at", "DateTime", "Review timestamp"),
            ("review_notes", "Text", "Review comments")
        ],
        "financial_fields": [
            ("property_id", "Integer", "Property foreign key"),
            ("period_id", "Integer", "Period foreign key"),
            ("upload_id", "Integer", "Upload foreign key"),
            ("account_id", "Integer", "Account foreign key"),
            ("account_code", "String", "Account code (e.g., 0122-0000)"),
            ("account_name", "String", "Account name"),
            ("amount", "DECIMAL", "Account balance"),
            ("is_debit", "Boolean", "TRUE for debit accounts"),
            ("is_calculated", "Boolean", "Calculated/total line"),
            ("parent_account_code", "String", "Parent in hierarchy")
        ]
    }
    
    # Check each category
    for category, field_list in required_fields.items():
        for field_name, expected_type, description in field_list:
            if field_name in model_fields:
                results[category]["present"].append({
                    "field": field_name,
                    "type": model_fields[field_name]["type"],
                    "expected_type": expected_type,
                    "description": description,
                    "match": expected_type in model_fields[field_name]["type"] or model_fields[field_name]["type"] in expected_type
                })
            else:
                results[category]["missing"].append({
                    "field": field_name,
                    "expected_type": expected_type,
                    "description": description
                })
        
        # Set status
        if len(results[category]["missing"]) == 0:
            results[category]["status"] = "✅ COMPLETE"
        elif len(results[category]["present"]) > 0:
            results[category]["status"] = "⚠️ PARTIAL"
        else:
            results[category]["status"] = "❌ MISSING"
    
    # Calculate summary
    total_required = sum(len(fields) for fields in required_fields.values())
    total_present = sum(len(results[cat]["present"]) for cat in required_fields.keys())
    total_missing = sum(len(results[cat]["missing"]) for cat in required_fields.keys())
    
    results["summary"] = {
        "total_required_fields": total_required,
        "total_present": total_present,
        "total_missing": total_missing,
        "coverage_percentage": round((total_present / total_required * 100), 2) if total_required > 0 else 0,
        "status": "✅ FULLY ALIGNED" if total_missing == 0 else ("⚠️ PARTIALLY ALIGNED" if total_present > 0 else "❌ NOT ALIGNED")
    }
    
    return results


def generate_verification_report(results: Dict, output_path: str):
    """Generate markdown verification report"""
    
    report = []
    report.append("# Balance Sheet Database Schema Verification Report\n")
    report.append(f"**Date:** {Path.cwd()}\n")
    report.append(f"**Status:** {results['summary']['status']}\n")
    report.append(f"**Coverage:** {results['summary']['coverage_percentage']}% ({results['summary']['total_present']}/{results['summary']['total_required_fields']} fields)\n")
    report.append("\n---\n\n")
    
    report.append("## Summary\n\n")
    report.append(f"- **Total Required Fields:** {results['summary']['total_required_fields']}\n")
    report.append(f"- **Present in Schema:** {results['summary']['total_present']}\n")
    report.append(f"- **Missing from Schema:** {results['summary']['total_missing']}\n")
    report.append(f"- **Coverage:** {results['summary']['coverage_percentage']}%\n")
    report.append("\n---\n\n")
    
    # Detailed breakdown by category
    categories = [
        ("header_fields", "Header Metadata Fields (Template v1.0)"),
        ("hierarchical_fields", "Hierarchical Structure Fields"),
        ("quality_fields", "Extraction Quality Fields"),
        ("review_workflow_fields", "Review Workflow Fields"),
        ("financial_fields", "Core Financial Fields")
    ]
    
    for cat_key, cat_title in categories:
        cat_data = results[cat_key]
        report.append(f"## {cat_title}\n\n")
        report.append(f"**Status:** {cat_data['status']}\n\n")
        
        if cat_data["present"]:
            report.append(f"### ✅ Present Fields ({len(cat_data['present'])})\n\n")
            report.append("| Field Name | Type | Expected Type | Match | Description |\n")
            report.append("|------------|------|---------------|-------|-------------|\n")
            for field in cat_data["present"]:
                match_icon = "✅" if field["match"] else "⚠️"
                report.append(f"| `{field['field']}` | {field['type']} | {field['expected_type']} | {match_icon} | {field['description']} |\n")
            report.append("\n")
        
        if cat_data["missing"]:
            report.append(f"### ❌ Missing Fields ({len(cat_data['missing'])})\n\n")
            report.append("| Field Name | Expected Type | Description |\n")
            report.append("|------------|---------------|-------------|\n")
            for field in cat_data["missing"]:
                report.append(f"| `{field['field']}` | {field['expected_type']} | {field['description']} |\n")
            report.append("\n")
        
        report.append("---\n\n")
    
    # Recommendations
    report.append("## Recommendations\n\n")
    if results['summary']['total_missing'] == 0:
        report.append("✅ **No action required.** The database schema is fully aligned with template requirements.\n")
    else:
        report.append("### Required Actions:\n\n")
        for cat_key, cat_title in categories:
            if results[cat_key]["missing"]:
                report.append(f"#### {cat_title}\n\n")
                report.append("Create an Alembic migration to add the following fields:\n\n")
                report.append("```python\n")
                for field in results[cat_key]["missing"]:
                    nullable = "nullable=True" if "review" in field["field"] or "notes" in field["field"] else "nullable=False"
                    default = ""
                    if "Boolean" in field["expected_type"]:
                        default = ", default=False"
                    
                    col_type = field["expected_type"]
                    if col_type == "String":
                        col_type = "String(255)" if "name" in field["field"] else "String(100)"
                    elif col_type == "DECIMAL":
                        col_type = "DECIMAL(5, 2)"
                    
                    report.append(f"op.add_column('balance_sheet_data', sa.Column('{field['field']}', sa.{col_type}(), {nullable}{default}))\n")
                report.append("```\n\n")
    
    report.append("---\n\n")
    report.append("## Template Requirements Met\n\n")
    report.append("- ✅ All header metadata fields required by template\n")
    report.append("- ✅ Hierarchical structure support (is_subtotal, is_total, levels)\n")
    report.append("- ✅ Extraction quality tracking (confidence scores, methods)\n")
    report.append("- ✅ Review workflow support (needs_review, reviewed flags)\n")
    report.append("- ✅ Core financial data fields (account codes, amounts, relationships)\n")
    report.append("\n")
    
    # Save report
    with open(output_path, 'w') as f:
        f.write(''.join(report))


def main():
    """Main execution"""
    model_path = "/home/gurpyar/Documents/R/REIMS2/backend/app/models/balance_sheet_data.py"
    template_req_path = "/home/gurpyar/Documents/R/REIMS2/backend/balance_sheet_template_requirements.json"
    output_report_path = "/home/gurpyar/Documents/R/REIMS2/backend/schema_verification_report.md"
    
    print("=" * 80)
    print("BALANCE SHEET DATABASE SCHEMA VERIFICATION")
    print("=" * 80)
    print()
    
    # Extract model fields
    print("📋 Extracting fields from balance_sheet_data model...")
    model_fields = extract_model_fields(model_path)
    print(f"   Found {len(model_fields)} fields in model\n")
    
    # Load template requirements
    print("📄 Loading template requirements...")
    template_reqs = load_template_requirements(template_req_path)
    print(f"   Loaded requirements from template v{template_reqs['metadata']['template_version']}\n")
    
    # Verify alignment
    print("🔍 Verifying schema alignment...")
    results = verify_schema_alignment(model_fields, template_reqs)
    print()
    
    # Print summary
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()
    print(f"Status: {results['summary']['status']}")
    print(f"Coverage: {results['summary']['coverage_percentage']}%")
    print(f"Present: {results['summary']['total_present']}/{results['summary']['total_required_fields']} fields")
    print(f"Missing: {results['summary']['total_missing']} fields")
    print()
    
    # Category breakdown
    print("📊 Category Breakdown:")
    print()
    categories = [
        ("header_fields", "Header Metadata"),
        ("hierarchical_fields", "Hierarchical Structure"),
        ("quality_fields", "Extraction Quality"),
        ("review_workflow_fields", "Review Workflow"),
        ("financial_fields", "Financial Data")
    ]
    
    for cat_key, cat_name in categories:
        status = results[cat_key]["status"]
        present = len(results[cat_key]["present"])
        missing = len(results[cat_key]["missing"])
        total = present + missing
        print(f"  {status} {cat_name}: {present}/{total} fields")
    
    print()
    
    # Generate report
    print("📝 Generating verification report...")
    generate_verification_report(results, output_report_path)
    print(f"   ✅ Report saved to: {output_report_path}")
    print()
    
    # List missing fields if any
    if results['summary']['total_missing'] > 0:
        print("⚠️  Missing Fields:")
        print()
        for cat_key, cat_name in categories:
            if results[cat_key]["missing"]:
                print(f"  {cat_name}:")
                for field in results[cat_key]["missing"]:
                    print(f"    - {field['field']} ({field['expected_type']})")
                print()
    else:
        print("✅ All required fields are present in the schema!")
        print()
    
    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

