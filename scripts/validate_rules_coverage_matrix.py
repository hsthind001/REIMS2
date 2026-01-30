#!/usr/bin/env python3
"""
Validate docs/RULES_COVERAGE_MATRIX.md against rule IDs in backend code.

Usage (from repo root):
  python scripts/validate_rules_coverage_matrix.py
  python scripts/validate_rules_coverage_matrix.py --matrix path/to/matrix.md
  python scripts/validate_rules_coverage_matrix.py --strict   # fail if any code ID missing from matrix

Exits 0 if OK, 1 if there are gaps (or with --strict).
"""
import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = REPO_ROOT / "docs" / "RULES_COVERAGE_MATRIX.md"
RULES_DIR = REPO_ROOT / "backend" / "app" / "services" / "rules"


def _expand_range(s: str) -> set[str]:
    """Expand 'AUDIT-1..48' to {'AUDIT-1', 'AUDIT-2', ..., 'AUDIT-48'}."""
    out: set[str] = set()
    s = s.strip()
    # e.g. "AUDIT-1..48" or "FA-PAL-1..5"
    m = re.match(r"^([A-Za-z0-9\-]+)-(\d+)\.\.(\d+)$", s)
    if m:
        prefix, start, end = m.group(1), int(m.group(2)), int(m.group(3))
        for i in range(start, end + 1):
            out.add(f"{prefix}-{i}")
        return out
    # e.g. "AUDIT-49" or "FA-MORT-4"
    if re.match(r"^[A-Za-z0-9\-]+-\d+$", s) or re.match(r"^[A-Za-z0-9\-]+-\d+\.\.\d+$", s):
        out.add(s)
        return out
    # "FA-PAL-1..5" with hyphen in prefix
    m2 = re.match(r"^([A-Za-z\-]+)-(\d+)\.\.(\d+)$", s)
    if m2:
        prefix, start, end = m2.group(1), int(m2.group(2)), int(m2.group(3))
        for i in range(start, end + 1):
            out.add(f"{prefix}-{i}")
        return out
    # single ID
    out.add(s)
    return out


def _parse_cell_to_ids(cell: str) -> set[str]:
    """Parse a table cell that may contain 'AUDIT-1..48', 'FA-WC-1, FA-WC-2', 'RRBS-1..4 (FA-RR-1..4)'."""
    ids: set[str] = set()
    cell = re.sub(r"^\*\*|\*\*$", "", cell)
    # Split on comma and on " (" / ")" to get tokens like "RRBS-1..4", "FA-RR-1..4", "FA-WC-1"
    for token in re.split(r"[,()]", cell):
        token = token.strip()
        if not token:
            continue
        if ".." in token:
            ids |= _expand_range(token)
        elif re.match(r"^[A-Za-z0-9\-]+-\d+$", token):
            ids.add(token)
    return ids


def parse_matrix_rule_ids(path: Path) -> set[str]:
    """Parse Rule ID column from the markdown table (first column of rule rows)."""
    ids: set[str] = set()
    if not path.exists():
        return ids
    text = path.read_text()
    in_table = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and "Rule ID" in line and "Rule name" in line:
            in_table = True
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 1 and parts[0] and not parts[0].startswith("---"):
                ids |= _parse_cell_to_ids(parts[0])
        if in_table and line.startswith("---"):
            continue
        if in_table and line.startswith("|") and "---" in line:
            continue
    return ids


def grep_rule_ids_in_code(rules_dir: Path) -> set[str]:
    """Extract rule_id= values from Python files under rules dir."""
    ids: set[str] = set()
    if not rules_dir.exists():
        return ids
    for py in rules_dir.rglob("*.py"):
        content = py.read_text()
        for m in re.finditer(r'rule_id\s*=\s*["\']([^"\']+)["\']', content):
            ids.add(m.group(1))
    return ids


# Top-level rule ID pattern: prefix + single number (e.g. AUDIT-49, FA-MORT-4, DQ-1).
# Sub-rules (BS-1, IS-1, DQ-13-BS, MST-1, etc.) are internal and not required in the matrix.
TOP_LEVEL_PATTERN = re.compile(
    r"^(AUDIT|FA-MORT|FA-WC|FA-RR|FA-CASH|FA-FRAUD|FA-PAL|RRBS|WCR|MCI|ANALYTICS|"
    r"COVENANT|BENCHMARK|TREND|STRESS|DASHBOARD|DQ)-\d+$"
)


def _is_top_level_rule_id(rid: str) -> bool:
    """True if this ID is a top-level rule the matrix is expected to list (or cover by range)."""
    return bool(TOP_LEVEL_PATTERN.match(rid))


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate rules coverage matrix vs code")
    ap.add_argument("--matrix", type=Path, default=MATRIX_PATH, help="Path to RULES_COVERAGE_MATRIX.md")
    ap.add_argument("--rules-dir", type=Path, default=RULES_DIR, help="Path to backend app/services/rules")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any top-level code ID missing from matrix")
    ap.add_argument("--all", action="store_true", help="Report all code IDs missing from matrix (including sub-rules)")
    args = ap.parse_args()

    matrix_ids = parse_matrix_rule_ids(args.matrix)
    code_ids = grep_rule_ids_in_code(args.rules_dir)

    # Code IDs that don't appear in matrix (matrix may use ranges like AUDIT-1..48)
    missing_from_matrix = code_ids - matrix_ids
    if not args.all:
        missing_from_matrix = {rid for rid in missing_from_matrix if _is_top_level_rule_id(rid)}

    ok = True
    if missing_from_matrix:
        print("Rule IDs in code but not listed in matrix (add or expand range in docs/RULES_COVERAGE_MATRIX.md):")
        for rid in sorted(missing_from_matrix):
            print(f"  - {rid}")
        ok = False
    if args.strict and (matrix_ids - code_ids):
        missing_from_code = matrix_ids - code_ids
        print("Rule IDs in matrix but not found in code (may be range or alias):")
        for rid in sorted(missing_from_code)[:30]:
            print(f"  - {rid}")
        if len(missing_from_code) > 30:
            print(f"  ... and {len(missing_from_code) - 30} more")
        ok = False

    if ok:
        print("OK: Matrix and code rule IDs are in sync.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
