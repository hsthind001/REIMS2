#!/usr/bin/env python3
"""
Parse Balance Sheet Extraction Template to extract all requirements
"""
import json
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any

def parse_template_file(template_path: str) -> Dict[str, Any]:
    """Parse the balance sheet extraction template markdown file"""
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    requirements = {
        "metadata": {
            "template_version": "1.0",
            "template_name": "Balance Sheet Extraction Template for REIMS2",
            "status": "Production-Ready"
        },
        "header_fields": {},
        "accounts": [],
        "validation_rules": [],
        "confidence_scoring": {},
        "review_flags": [],
        "extraction_rules": {},
        "data_types": {},
        "keywords": {}
    }
    
    # Extract header fields
    header_match = re.search(r'### \*\*Header Information\*\*\s+```yaml\n(.*?)\n```', content, re.DOTALL)
    if header_match:
        header_yaml = header_match.group(1)
        try:
            header_data = yaml.safe_load(header_yaml)
            if 'header_extraction' in header_data:
                requirements["header_fields"] = header_data['header_extraction']
        except:
            pass
    
    # Extract all account codes from YAML sections
    yaml_sections = re.findall(r'```yaml\n(.*?)\n```', content, re.DOTALL)
    
    for yaml_section in yaml_sections:
        try:
            data = yaml.safe_load(yaml_section)
            if isinstance(data, dict):
                # Check for section definitions (assets, liabilities, capital)
                if 'section_name' in data:
                    extract_accounts_from_section(data, requirements["accounts"])
                elif 'account_code' in data and 'name' in data:
                    # Single account definition
                    requirements["accounts"].append({
                        "account_code": data.get('account_code'),
                        "name": data.get('name'),
                        "type": data.get('type'),
                        "required": data.get('required', False),
                        "critical": data.get('critical', False)
                    })
        except:
            continue
    
    # Extract validation rules
    validation_sections = [
        'fundamental_equation',
        'section_totals',
        'quality_checks',
        'completeness'
    ]
    
    for section in validation_sections:
        pattern = rf'{section}:\s+```yaml\n(.*?)\n```'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                validation_data = yaml.safe_load(match.group(1))
                if isinstance(validation_data, dict):
                    validation_data['section_name'] = section
                    requirements["validation_rules"].append(validation_data)
                elif isinstance(validation_data, list):
                    for rule in validation_data:
                        if isinstance(rule, dict):
                            rule['section_name'] = section
                            requirements["validation_rules"].append(rule)
            except:
                pass
    
    # Extract confidence scoring requirements
    confidence_match = re.search(r'confidence_calculation:\s+```yaml\n(.*?)\n```', content, re.DOTALL)
    if confidence_match:
        try:
            confidence_data = yaml.safe_load(confidence_match.group(1))
            requirements["confidence_scoring"] = confidence_data
        except:
            pass
    
    # Extract review flag rules
    flagging_match = re.search(r'flagging_rules:\s+```yaml\n(.*?)\n```', content, re.DOTALL)
    if flagging_match:
        try:
            flagging_data = yaml.safe_load(flagging_match.group(1))
            if isinstance(flagging_data, list):
                requirements["review_flags"] = flagging_data
        except:
            pass
    
    # Extract extraction rules
    extraction_rules_match = re.search(r'line_item_patterns:\s+```yaml\n(.*?)\n```', content, re.DOTALL)
    if extraction_rules_match:
        try:
            extraction_data = yaml.safe_load(extraction_rules_match.group(1))
            requirements["extraction_rules"]["line_item_patterns"] = extraction_data
        except:
            pass
    
    # Extract account mapping rules
    account_mapping_match = re.search(r'account_mapping:\s+```yaml\n(.*?)\n```', content, re.DOTALL)
    if account_mapping_match:
        try:
            mapping_data = yaml.safe_load(account_mapping_match.group(1))
            requirements["extraction_rules"]["account_mapping"] = mapping_data
        except:
            pass
    
    # Extract keywords
    keywords_matches = re.findall(r'(required_keywords|supporting_keywords):\s+```yaml\n(.*?)\n```', content, re.DOTALL)
    for keyword_type, keyword_content in keywords_matches:
        try:
            keyword_data = yaml.safe_load(keyword_content)
            if keyword_type in keyword_data:
                requirements["keywords"][keyword_type] = keyword_data[keyword_type]
        except:
            pass
    
    return requirements


def extract_accounts_from_section(section_data: Dict, accounts_list: List):
    """Recursively extract accounts from section data"""
    
    section_name = section_data.get('section_name', '')
    
    # Extract section total
    if 'section_total' in section_data:
        total_data = section_data['section_total']
        accounts_list.append({
            "account_code": total_data.get('account_code'),
            "name": total_data.get('name'),
            "type": total_data.get('type', 'section_total'),
            "section": section_name,
            "required": total_data.get('required', False),
            "critical": total_data.get('critical', False),
            "data_type": total_data.get('data_type'),
            "validation": total_data.get('validation')
        })
    
    # Extract subsections
    if 'subsections' in section_data:
        for subsection in section_data['subsections']:
            subsection_name = subsection.get('name', '')
            
            # Extract subsection total
            if 'total_account' in subsection:
                accounts_list.append({
                    "account_code": subsection['total_account'],
                    "name": subsection.get('total_names', [None])[0] if subsection.get('total_names') else f"Total {subsection_name}",
                    "type": "calculated_total",
                    "section": section_name,
                    "subsection": subsection_name,
                    "required": subsection.get('required', False)
                })
            
            # Extract line items
            if 'line_items' in subsection:
                for line_item in subsection['line_items']:
                    if line_item.get('skip_extraction'):
                        continue
                    
                    account = {
                        "account_code": line_item.get('account_code'),
                        "name": line_item.get('name') or line_item.get('name_pattern'),
                        "type": line_item.get('type', 'detail'),
                        "section": section_name,
                        "subsection": subsection_name,
                        "required": line_item.get('required', False),
                        "data_type": line_item.get('data_type'),
                        "allow_negative": line_item.get('allow_negative', False),
                        "is_contra_account": line_item.get('is_contra_account', False),
                        "validation": line_item.get('validation')
                    }
                    accounts_list.append(account)
    
    # Handle grand_total
    if 'account_code' in section_data and section_data.get('type') == 'grand_total':
        accounts_list.append({
            "account_code": section_data.get('account_code'),
            "name": section_data.get('name'),
            "type": "grand_total",
            "required": section_data.get('required', False),
            "critical": section_data.get('critical', False),
            "must_equal": section_data.get('must_equal')
        })


def main():
    """Main execution"""
    template_path = "/home/gurpyar/Documents/R/Balance Sheet Extraction Template/balance_sheet_extraction_template.md"
    output_path = "/home/gurpyar/Documents/R/REIMS2/backend/balance_sheet_template_requirements.json"
    
    print("Parsing Balance Sheet Extraction Template...")
    requirements = parse_template_file(template_path)
    
    print(f"\nExtracted Requirements Summary:")
    print(f"  - Header fields: {len(requirements['header_fields'])}")
    print(f"  - Accounts: {len(requirements['accounts'])}")
    print(f"  - Validation rules: {len(requirements['validation_rules'])}")
    print(f"  - Review flags: {len(requirements['review_flags'])}")
    print(f"  - Keywords: {sum(len(v) if isinstance(v, list) else 1 for v in requirements['keywords'].values())}")
    
    # Save to JSON
    with open(output_path, 'w') as f:
        json.dump(requirements, f, indent=2)
    
    print(f"\n✅ Saved requirements to: {output_path}")
    
    # Generate summary statistics
    print("\n📊 Account Summary:")
    account_types = {}
    sections = {}
    for acc in requirements['accounts']:
        acc_type = acc.get('type', 'unknown')
        section = acc.get('section', 'unknown')
        account_types[acc_type] = account_types.get(acc_type, 0) + 1
        sections[section] = sections.get(section, 0) + 1
    
    print(f"\n  By Type:")
    for acc_type, count in sorted(account_types.items()):
        print(f"    - {acc_type}: {count}")
    
    print(f"\n  By Section:")
    for section, count in sorted(sections.items()):
        print(f"    - {section}: {count}")
    
    # List critical accounts
    critical_accounts = [acc for acc in requirements['accounts'] if acc.get('critical') or acc.get('required')]
    print(f"\n⚠️  Critical/Required Accounts: {len(critical_accounts)}")
    for acc in critical_accounts[:10]:  # Show first 10
        print(f"    - {acc.get('account_code')}: {acc.get('name')}")
    if len(critical_accounts) > 10:
        print(f"    ... and {len(critical_accounts) - 10} more")


if __name__ == "__main__":
    main()

