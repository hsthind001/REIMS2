#!/usr/bin/env python3
"""
Validate environment configuration for REIMS backend.

Run before deploy or in CI to ensure required env vars are set.
Usage: python scripts/validate_env.py
"""
import os
import sys


def main() -> int:
    env = os.environ.get("ENVIRONMENT", "development").lower()
    errors = []

    if env in ("production", "staging"):
        required = [
            ("SECRET_KEY", "JWT/session signing. Generate: python -c \"import secrets; print(secrets.token_urlsafe(64))\""),
            ("POSTGRES_USER", "Database user"),
            ("POSTGRES_PASSWORD", "Database password"),
            ("POSTGRES_SERVER", "Database host"),
        ]
        for key, desc in required:
            val = os.environ.get(key)
            if not val:
                errors.append(f"  {key}: {desc}")
            elif key == "SECRET_KEY" and len(val) < 32:
                errors.append(f"  {key}: must be at least 32 characters")

    if errors:
        print("ERROR: Missing or invalid required environment variables:\n" + "\n".join(errors))
        return 1

    print("OK: Environment configuration valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
