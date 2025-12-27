#!/usr/bin/env python3
"""
REIMS2 Pre-Commit Hook: Duplicate Prevention
=============================================

This hook prevents committing:
1. Duplicate/redundant documentation files
2. Backup files (*.backup, *.old, *_OLD)
3. Temporary files
4. Large generated files that should be gitignored

Install this hook:
    ln -s ../../scripts/pre_commit_duplicate_prevention.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Author: REIMS Team
Date: 2025-12-26
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate problematic files
FORBIDDEN_PATTERNS = [
    # Backup files
    r".*\.backup(\.\w+)?$",
    r".*\.old(\.\w+)?$",
    r".*_OLD(\.\w+)?$",
    r".*_BACKUP(\.\w+)?$",

    # Temporary files
    r".*\.tmp(\.\w+)?$",
    r".*~$",
    r".*\.swp$",

    # Duplicate indicators in filenames
    r".*_FINAL_FINAL.*",
    r".*_COMPLETE_COMPLETE.*",
    r".*_V\d+_V\d+.*",  # Double versioning like _V1_V2
]

# Documentation patterns that suggest duplication
DOC_DUPLICATION_PATTERNS = [
    (r"IMPLEMENTATION_SUMMARY.*\.md", "Use IMPLEMENTATION_COMPLETE.md instead"),
    (r"FINAL_.*_FINAL.*\.md", "Avoid 'FINAL_FINAL' naming"),
    (r".*_COMPLETE_\d{8}\.md", "Don't append dates - use git history"),
    (r".*_\d{4}-\d{2}-\d{2}\.md", "Don't append dates to filenames"),
]

# Files that should be in .gitignore
SHOULD_BE_IGNORED = [
    r".*_TEST_RESULTS\.json$",
    r".*\.cache/.*",
    r".*__pycache__/.*",
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.pyd$",
]

# Maximum file size (in MB) for documentation
MAX_DOC_SIZE_MB = 5.0


class PreCommitChecker:
    """Pre-commit hook to prevent duplicate and problematic files"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def check_file(self, filepath: str) -> Tuple[bool, List[str]]:
        """Check a single file for issues"""
        issues = []

        filename = os.path.basename(filepath)

        # Check forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if re.match(pattern, filename, re.IGNORECASE):
                issues.append(f"❌ Forbidden pattern: {filename} matches {pattern}")

        # Check documentation duplication patterns
        if filename.endswith('.md'):
            for pattern, message in DOC_DUPLICATION_PATTERNS:
                if re.match(pattern, filename, re.IGNORECASE):
                    issues.append(f"⚠️  Possible duplicate: {filename} - {message}")

        # Check if file should be gitignored
        for pattern in SHOULD_BE_IGNORED:
            if re.match(pattern, filepath, re.IGNORECASE):
                issues.append(f"❌ Should be in .gitignore: {filepath}")

        # Check file size for documentation
        if filename.endswith('.md') and os.path.exists(filepath):
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if size_mb > MAX_DOC_SIZE_MB:
                issues.append(
                    f"⚠️  Large documentation file: {filename} ({size_mb:.2f} MB) "
                    f"- Consider splitting or archiving"
                )

        return len(issues) == 0, issues

    def get_staged_files(self) -> List[str]:
        """Get list of files staged for commit"""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                capture_output=True,
                text=True,
                check=True
            )
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []

    def run(self) -> int:
        """Run pre-commit checks"""
        print("🔍 REIMS2 Pre-Commit: Checking for duplicates and problematic files...")

        staged_files = self.get_staged_files()

        if not staged_files:
            print("✅ No files staged for commit")
            return 0

        has_errors = False
        has_warnings = False

        for filepath in staged_files:
            passed, issues = self.check_file(filepath)

            for issue in issues:
                if issue.startswith("❌"):
                    self.errors.append(f"{filepath}: {issue}")
                    has_errors = True
                else:
                    self.warnings.append(f"{filepath}: {issue}")
                    has_warnings = True

        # Print results
        if has_errors:
            print("\n❌ COMMIT BLOCKED - Fix these errors:\n")
            for error in self.errors:
                print(f"  {error}")
            print("\n💡 Tips:")
            print("  - Remove backup/temporary files")
            print("  - Add ignored files to .gitignore")
            print("  - Use descriptive, non-duplicate filenames")
            print("  - Run: python scripts/cleanup_duplicates.py")
            return 1

        if has_warnings:
            print("\n⚠️  WARNINGS (commit will proceed):\n")
            for warning in self.warnings:
                print(f"  {warning}")
            print()

        print(f"✅ Pre-commit checks passed ({len(staged_files)} files)")
        return 0


def main():
    """Main entry point"""
    checker = PreCommitChecker()
    sys.exit(checker.run())


if __name__ == "__main__":
    main()
