"""
Seed runner for forensic calculated rules.

Usage:
    python3 backend/scripts/seed_forensic_rules.py
"""
import os
import sys

if __name__ == "__main__":
    # Ensure app is on path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from app.db.seeds.forensic_calculated_rules_seed import seed_calculated_rules
        seed_calculated_rules()
    except Exception as exc:  # pragma: no cover - helper script
        print(f"Failed to seed forensic calculated rules: {exc}")
        sys.exit(1)
