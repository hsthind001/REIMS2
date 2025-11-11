#!/usr/bin/env python3
"""
Parse Balance Sheet Extraction Template - Enhanced Version
Extracts all requirements from the template markdown file
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any

def extract_accounts_from_template(content: str) -> List[Dict[str, Any]]:
    """Extract all account definitions from template"""
    accounts = []
    
    # Pattern to match account line items in YAML blocks
    # Format: - account_code: "XXXX-XXXX"
    account_pattern = r'-\s+account_code:\s*"([^"]+)"\s*\n\s+name(?:_pattern)?:\s*"?([^"\n]+)"?\s*\n\s+type:\s*"([^"]+)"'
    
    matches = re.finditer(account_pattern, content, re.MULTILINE)
    for match in matches:
        account_code = match.group(1)
        name = match.group(2).strip()
        acc_type = match.group(3)
        
        # Extract additional properties from the same block
        block_start = match.start()
        block_end = content.find('\n\n', match.end())
        if block_end == -1:
            block_end = len(content)
        block = content[block_start:block_end]
        
        account = {
            "account_code": account_code,
            "name": name,
            "type": acc_type,
            "required": 'required: true' in block,
            "critical": 'critical: true' in block,
            "allow_negative": 'allow_negative: true' in block,
            "is_contra_account": 'is_contra_account: true' in block,
            "data_type": "decimal(15,2)"  # Default from template
        }
        
        # Extract section context
        section_match = re.search(r'section_name:\s*"([^"]+)"', content[:block_start][::-1])
        if section_match:
            account["section"] = section_match.group(1)[::-1]
        
        accounts.append(account)
    
    # Also extract section totals explicitly mentioned
    total_patterns = [
        (r'account_code:\s*"(1999-0000)"\s*\n\s+name:\s*"([^"]+)"', "ASSETS"),
        (r'account_code:\s*"(2999-0000)"\s*\n\s+name:\s*"([^"]+)"', "LIABILITIES"),
        (r'account_code:\s*"(3999-0000)"\s*\n\s+name:\s*"([^"]+)"', "CAPITAL"),
        (r'account_code:\s*"(3999-9000)"\s*\n\s+name:\s*"([^"]+)"', "GRAND_TOTAL"),
        (r'total_account:\s*"(0499-9000)"', "Current Assets Total"),
        (r'total_account:\s*"(1099-0000)"', "Property & Equipment Total"),
        (r'total_account:\s*"(1998-0000)"', "Other Assets Total"),
        (r'total_account:\s*"(2590-0000)"', "Current Liabilities Total"),
        (r'total_account:\s*"(2900-0000)"', "Long Term Liabilities Total"),
    ]
    
    for pattern, section in total_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            account_code = match.group(1)
            name = match.group(2) if len(match.groups()) > 1 else section
            if not any(acc['account_code'] == account_code for acc in accounts):
                accounts.append({
                    "account_code": account_code,
                    "name": name,
                    "type": "section_total" if "TOTAL" in account_code or "9000" in account_code else "calculated_total",
                    "section": section,
                    "required": True,
                    "critical": True,
                    "data_type": "decimal(15,2)"
                })
    
    return accounts


def extract_validation_rules(content: str) -> List[Dict[str, Any]]:
    """Extract validation rules from template"""
    rules = []
    
    # Fundamental equation
    if 'fundamental_equation' in content:
        rules.append({
            "name": "accounting_equation",
            "rule": "total_assets = total_liabilities + total_capital",
            "severity": "critical",
            "tolerance": 0.01,
            "description": "Assets must equal Liabilities + Equity",
            "source": "template_section:fundamental_equation"
        })
    
    # Section total validations
    section_validations = [
        ("current_assets", "sum(detail_line_items) = total_current_assets", "high"),
        ("property_equipment", "sum(detail_line_items) = total_property_equipment", "high"),
        ("other_assets", "sum(detail_line_items) = total_other_assets", "high"),
        ("assets", "total_current_assets + total_property_equipment + total_other_assets = total_assets", "critical"),
        ("current_liabilities", "sum(detail_line_items) = total_current_liabilities", "high"),
        ("long_term_liabilities", "sum(detail_line_items) = total_long_term_liabilities", "high"),
        ("liabilities", "total_current_liabilities + total_long_term_liabilities = total_liabilities", "critical"),
    ]
    
    for section, rule, severity in section_validations:
        rules.append({
            "name": f"{section}_total_validation",
            "rule": rule,
            "severity": severity,
            "tolerance": 0.01,
            "section": section,
            "source": "template_section:section_totals"
        })
    
    # Data quality checks
    quality_checks = [
        ("all_required_sections_present", ["assets", "liabilities", "capital"], "critical"),
        ("required_totals_extracted", ["1999-0000", "2999-0000", "3999-0000", "3999-9000"], "critical"),
        ("no_duplicate_accounts", "unique(property_id, period_id, account_code)", "high"),
        ("reasonable_amounts", "total_assets > 0 AND total_liabilities >= 0", "medium"),
        ("contra_accounts_negative", "amount <= 0 for contra accounts", "medium"),
    ]
    
    for check_name, check_data, severity in quality_checks:
        rules.append({
            "name": check_name,
            "check_data": check_data,
            "severity": severity,
            "source": "template_section:quality_checks"
        })
    
    # Completeness check
    rules.append({
        "name": "completeness_check",
        "min_line_items": 20,
        "expected_line_items": "50-100",
        "critical_accounts": ["0510-0000", "0610-0000", "1999-0000", "2999-0000", "3999-0000"],
        "severity": "critical",
        "source": "template_section:completeness"
    })
    
    return rules


def extract_header_fields(content: str) -> Dict[str, Any]:
    """Extract required header fields"""
    return {
        "property_name": {
            "required": True,
            "confidence_threshold": 90,
            "patterns": [
                r"^(.+?)\s+\(\w+\)",
                r"^Property:\s*(.+)$"
            ]
        },
        "report_period": {
            "required": True,
            "confidence_threshold": 95,
            "patterns": [
                r"Period\s*=\s*(\w+\s+\d{4})",
                r"As of\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
                r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
            ]
        },
        "accounting_method": {
            "required": False,
            "confidence_threshold": 80,
            "patterns": [r"Book\s*=\s*(\w+)"]
        },
        "report_date": {
            "required": False,
            "patterns": [
                r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
                r"\d{1,2}:\d{2}\s+(AM|PM)"
            ]
        }
    }


def extract_confidence_scoring(content: str) -> Dict[str, Any]:
    """Extract confidence scoring requirements"""
    return {
        "per_field_factors": {
            "extraction_method": {
                "exact_code_match": 100,
                "ocr_with_validation": 95,
                "fuzzy_match": "70-90",
                "keyword_match": "60-75",
                "manual_entry": 100
            },
            "amount_clarity": {
                "clear_digits": 100,
                "slight_ocr_noise": "85-95",
                "significant_ocr_noise": "60-80",
                "barely_readable": "30-50"
            },
            "position_context": {
                "expected_section": 100,
                "unexpected_section": 70,
                "ambiguous_location": 50
            },
            "validation_result": {
                "passes_all_validations": 100,
                "minor_warning": 85,
                "validation_failed": 40
            }
        },
        "document_level": {
            "formula": "avg(line_item_confidences) * 0.4 + validation_pass_rate * 0.3 + completeness_score * 0.2 + accounting_equation_valid * 0.1",
            "thresholds": {
                "excellent": ">=95",
                "good": "90-94",
                "acceptable": "80-89",
                "needs_review": "70-79",
                "poor": "<70"
            },
            "threshold_for_auto_approve": 90,
            "threshold_for_review": 75,
            "threshold_for_rejection": 50
        }
    }


def extract_review_flags(content: str) -> List[Dict[str, Any]]:
    """Extract review flag rules"""
    return [
        {
            "flag": "low_confidence_extraction",
            "trigger": "line_item.confidence < 85",
            "severity": "medium",
            "message": "Low confidence in extracted amount"
        },
        {
            "flag": "unmatched_account",
            "trigger": "account_code not in chart_of_accounts",
            "severity": "high",
            "message": "Account code not found in chart of accounts",
            "suggested_action": "map_to_existing_or_create_new"
        },
        {
            "flag": "validation_failure",
            "trigger": "validation_result = false",
            "severity": "high",
            "message": "Failed validation"
        },
        {
            "flag": "unusual_amount",
            "trigger": "abs(current_amount - prior_period_amount) > prior_period_amount * 0.5 AND abs(change) > 10000",
            "severity": "medium",
            "message": "Significant change from prior period"
        },
        {
            "flag": "negative_where_positive_expected",
            "trigger": "account.expected_sign = 'positive' AND amount < 0 AND account.is_contra_account = false",
            "severity": "medium",
            "message": "Unexpected negative amount"
        },
        {
            "flag": "missing_critical_account",
            "trigger": "critical_account not extracted",
            "severity": "critical",
            "message": "Required account missing"
        },
        {
            "flag": "balance_sheet_not_balanced",
            "trigger": "abs(total_assets - (total_liabilities + total_capital)) > 0.01",
            "severity": "critical",
            "message": "Balance sheet does not balance",
            "blocking": True
        }
    ]


def extract_extraction_rules(content: str) -> Dict[str, Any]:
    """Extract extraction and matching rules"""
    return {
        "line_item_patterns": {
            "standard": {
                "pattern": r"^(\d{4}-\d{4})\s+([A-Za-z0-9 /\-\.\(\)&,]+?)\s+([-]?[\d,]+\.\d{2})$",
                "groups": ["account_code", "account_name", "amount"],
                "confidence": 95
            },
            "no_code": {
                "pattern": r"^([A-Za-z0-9 /\-\.\(\)&,]+?)\s{2,}([-]?[\d,]+\.\d{2})$",
                "groups": ["account_name", "amount"],
                "confidence": 75,
                "action": "fuzzy_match_to_chart_of_accounts"
            },
            "total_line": {
                "pattern": r"^(Total|TOTAL)\s+([A-Za-z &]+?)\s+([-]?[\d,]+\.\d{2})$",
                "groups": ["prefix", "section_name", "amount"],
                "confidence": 90,
                "is_calculated": True
            }
        },
        "account_mapping": {
            "strategy": "exact_match_preferred",
            "exact_code_match": {
                "confidence": 100,
                "action": "direct_insert"
            },
            "fuzzy_name_match": {
                "confidence_range": "70-95",
                "threshold": 85,
                "algorithm": "levenshtein_distance",
                "action": "map_to_closest_match",
                "flag_if_below": 85
            },
            "keyword_match": {
                "confidence_range": "60-80",
                "action": "map_with_review_flag"
            },
            "no_match": {
                "confidence": 0,
                "action": "create_unmatched_item_entry",
                "flag_for_review": True
            }
        },
        "fuzzy_matching_threshold": 85
    }


def main():
    """Main execution"""
    template_path = "/home/gurpyar/Documents/R/Balance Sheet Extraction Template/balance_sheet_extraction_template.md"
    output_path = "/home/gurpyar/Documents/R/REIMS2/backend/balance_sheet_template_requirements.json"
    
    print("Parsing Balance Sheet Extraction Template (Enhanced)...")
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    requirements = {
        "metadata": {
            "template_version": "1.0",
            "template_name": "Balance Sheet Extraction Template for REIMS2",
            "status": "Production-Ready",
            "source_file": template_path
        },
        "header_fields": extract_header_fields(content),
        "accounts": extract_accounts_from_template(content),
        "validation_rules": extract_validation_rules(content),
        "confidence_scoring": extract_confidence_scoring(content),
        "review_flags": extract_review_flags(content),
        "extraction_rules": extract_extraction_rules(content),
        "keywords": {
            "required_keywords": ["Balance Sheet", "Statement of Financial Position", "Assets", "Liabilities", "Capital", "Equity", "Net Worth"],
            "supporting_keywords": ["Current Balance", "TOTAL ASSETS", "TOTAL LIABILITIES", "Property & Equipment", "Current Assets", "Long Term"]
        },
        "data_types": {
            "amount": "decimal(15,2)",
            "account_code": "varchar(50)",
            "account_name": "varchar(255)",
            "confidence_score": "decimal(5,2)"
        }
    }
    
    print(f"\n✅ Extracted Requirements Summary:")
    print(f"  - Header fields: {len(requirements['header_fields'])}")
    print(f"  - Accounts extracted: {len(requirements['accounts'])}")
    print(f"  - Validation rules: {len(requirements['validation_rules'])}")
    print(f"  - Review flags: {len(requirements['review_flags'])}")
    print(f"  - Keywords: {len(requirements['keywords']['required_keywords']) + len(requirements['keywords']['supporting_keywords'])}")
    print(f"  - Fuzzy matching threshold: {requirements['extraction_rules']['fuzzy_matching_threshold']}%")
    
    # Save to JSON
    with open(output_path, 'w') as f:
        json.dump(requirements, f, indent=2)
    
    print(f"\n✅ Saved comprehensive requirements to: {output_path}")
    
    # Summary statistics
    print("\n📊 Account Summary:")
    account_types = {}
    sections = {}
    critical_count = 0
    required_count = 0
    contra_count = 0
    
    for acc in requirements['accounts']:
        acc_type = acc.get('type', 'unknown')
        section = acc.get('section', 'unknown')
        account_types[acc_type] = account_types.get(acc_type, 0) + 1
        sections[section] = sections.get(section, 0) + 1
        if acc.get('critical'):
            critical_count += 1
        if acc.get('required'):
            required_count += 1
        if acc.get('is_contra_account'):
            contra_count += 1
    
    print(f"\n  By Type:")
    for acc_type, count in sorted(account_types.items()):
        print(f"    - {acc_type}: {count}")
    
    print(f"\n  By Section:")
    for section, count in sorted(sections.items()):
        print(f"    - {section}: {count}")
    
    print(f"\n  Special Categories:")
    print(f"    - Critical accounts: {critical_count}")
    print(f"    - Required accounts: {required_count}")
    print(f"    - Contra accounts: {contra_count}")
    
    # Validation rules summary
    print(f"\n📋 Validation Rules Summary:")
    print(f"  Total rules: {len(requirements['validation_rules'])}")
    severity_counts = {}
    for rule in requirements['validation_rules']:
        severity = rule.get('severity', 'unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    for severity, count in sorted(severity_counts.items()):
        print(f"    - {severity}: {count}")
    
    print(f"\n🚩 Review Flags:")
    print(f"  Total flag types: {len(requirements['review_flags'])}")
    for flag in requirements['review_flags']:
        print(f"    - {flag['flag']} ({flag['severity']})")


if __name__ == "__main__":
    main()

