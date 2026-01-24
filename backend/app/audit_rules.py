
import os
import re
import glob

RULES_DIR = "/home/hsthind/Downloads/Reconcile - Aduit - Rules"
CODE_DIR = "/home/hsthind/Documents/GitHub/REIMS2/backend/app/services/rules"

# Map MD filename to PY filename
FILE_MAPPING = {
    "balance_sheet_rules.md": "balance_sheet_rules.py",
    "income_statement_rules.md": "income_statement_rules.py",
    "cash_flow_rules.md": "cash_flow_rules.py",
    "mortgage_rules_analysis.md": "mortgage_rules.py",
    # "rent_roll_complete_reconciliation.md": "rent_roll_rules.py", # Format might be different, checking manually later if needed
    # "complete_three_statement_reconciliation.md": "three_statement_rules.py"
}

def extract_rules_from_md(filepath):
    """Extract rule IDs like BS-1, IS-5, etc."""
    rules = set()
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            # Look for headers like "### Rule BS-1:" or "**Rule BS-1:"
            # Match Rule BS-1 or Rule 1
            matches_hyphen = re.findall(r"Rule\s+([A-Z0-9]+-[0-9]+)", content, re.IGNORECASE)
            matches_num = re.findall(r"Rule\s+([0-9]+)", content, re.IGNORECASE)
            
            for m in matches_hyphen:
                rules.add(m.upper())
            for m in matches_num:
                # Assuming mortgage file context, or prefixing?
                # Actually, check what prefix is expected.
                # If content source is 'mortgage', we might prefix MST-
                # But let's look at the mapping logic in audit_rules.py
                pass # Logic needs to handle context specific prefixing
                
            # Quick fix: if file is mortgage, add MST- prefix
            if "mortgage" in filepath.lower():
               for m in matches_num:
                   rules.add(f"MST-{m}")
            else:
               # Just add raw if not mortgage, though standard is Hyphen
               pass
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return rules

def extract_rules_from_py(filepath):
    """Extract rule IDs from code like rule_id="BS-1" """
    rules = set()
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            # Pattern: rule_id=["']([A-Z0-9-]+)["']
            matches = re.findall(r'rule_id=["\']([A-Z0-9-]+)["\']', content)
            for m in matches:
                rules.add(m.upper())
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return rules

def main():
    print("Beginning Rule Audit...\n")
    
    # Check specific mappings first
    for md_file, py_file in FILE_MAPPING.items():
        md_path = os.path.join(RULES_DIR, md_file)
        py_path = os.path.join(CODE_DIR, py_file)
        
        if os.path.exists(md_path) and os.path.exists(py_path):
            req_rules = extract_rules_from_md(md_path)
            impl_rules = extract_rules_from_py(py_path)
            
            missing = req_rules - impl_rules
            print(f"--- {md_file} vs {py_file} ---")
            print(f"Required: {len(req_rules)}")
            print(f"Implemented: {len(impl_rules)}")
            print(f"Missing ({len(missing)}): {sorted(list(missing))}")
            print("\n")
            
    # Check Rent Roll manually if regex is tricky, but let's try generic
    rr_md = os.path.join(RULES_DIR, "rent_roll_complete_reconciliation.md")
    rr_py = os.path.join(CODE_DIR, "rent_roll_rules.py")
    if os.path.exists(rr_md):
        req = extract_rules_from_md(rr_md)
        impl = extract_rules_from_py(rr_py)
        print(f"--- Rent Roll ---")
        print(f"Missing: {sorted(list(req - impl))}\n")
        
    # Check Three Statement
    ts_md = os.path.join(RULES_DIR, "complete_three_statement_reconciliation.md")
    ts_py = os.path.join(CODE_DIR, "three_statement_rules.py")
    if os.path.exists(ts_md):
        req = extract_rules_from_md(ts_md)
        impl = extract_rules_from_py(ts_py)
        # Note: 3S rules might use CF- or BS- prefixes in requirement, but map to logic.
        print(f"--- Three Statement ---")
        print(f"Missing: {sorted(list(req - impl))}\n")

if __name__ == "__main__":
    main()
