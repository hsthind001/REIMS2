"""
Registry of all defined reconciliation rule IDs.

Used by ReconciliationRuleEngine to emit a result for every defined rule
each run (PASS / FAIL / SKIP / INFO), so the Financial Integrity Hub
can list "all rules" with a status instead of only rules that emitted a result.

Rule IDs are collected at import time by scanning backend/app/services/rules/*.py
for rule_id="..." literals (this file is excluded). Run
  python scripts/validate_rules_coverage_matrix.py
to keep docs/RULES_COVERAGE_MATRIX.md in sync.
"""
import re
from pathlib import Path
from typing import FrozenSet


def _collect_rule_ids() -> FrozenSet[str]:
    """Collect all rule_id literals from Python files in the rules package."""
    rules_dir = Path(__file__).resolve().parent
    ids: set[str] = set()
    for py in rules_dir.rglob("*.py"):
        if py.name == "rule_registry.py":
            continue
        content = py.read_text(encoding="utf-8")
        for m in re.finditer(r'rule_id\s*=\s*["\']([^"\']+)["\']', content):
            ids.add(m.group(1))
    return frozenset(ids)


ALL_RULE_IDS: FrozenSet[str] = _collect_rule_ids()
