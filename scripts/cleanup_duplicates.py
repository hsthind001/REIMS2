#!/usr/bin/env python3
"""
REIMS2 Intelligent Duplicate Cleanup System
============================================

This script implements a self-learning system to:
1. Identify duplicate/redundant documentation files
2. Consolidate related documentation into archives
3. Clean up Docker-related duplicates
4. Prevent future documentation bloat
5. Generate a knowledge base index

Author: REIMS Team
Date: 2025-12-26
"""

import os
import sys
import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# REIMS2 root directory
ROOT_DIR = Path(__file__).parent.parent
ARCHIVE_DIR = ROOT_DIR / "docs" / "archive"
DOCS_DIR = ROOT_DIR / "docs"

# Categories of documentation that should be consolidated
DOC_CATEGORIES = {
    "forensic_reconciliation": {
        "pattern": ["FORENSIC"],
        "keep": "README_FORENSIC_RECONCILIATION.md",
        "archive_prefix": "forensic"
    },
    "market_intelligence": {
        "pattern": ["MARKET_INTELLIGENCE", "MARKET"],
        "keep": "README_MARKET_INTELLIGENCE.md",
        "archive_prefix": "market"
    },
    "optimization": {
        "pattern": ["OPTIMIZATION", "DOCKER_OPTIMIZATION"],
        "keep": "OPTIMIZATION_SESSION_COMPLETE.md",
        "archive_prefix": "optimization"
    },
    "implementation": {
        "pattern": ["IMPLEMENTATION_", "FINAL_IMPLEMENTATION"],
        "keep": "IMPLEMENTATION_COMPLETE.md",
        "archive_prefix": "implementation"
    },
    "docker": {
        "pattern": ["DOCKER_FILES", "DOCKER_FRONTEND", "DOCKER_CLEANUP"],
        "keep": "DOCKER_COMPOSE_README.md",
        "archive_prefix": "docker"
    },
    "mortgage": {
        "pattern": ["MORTGAGE_"],
        "keep": "MORTGAGE_INTEGRATION_SOLUTION.md",
        "archive_prefix": "mortgage"
    },
    "self_learning": {
        "pattern": ["SELF_LEARNING"],
        "keep": "COMPLETE_SELF_LEARNING_IMPLEMENTATION.md",
        "archive_prefix": "self_learning"
    },
    "verification": {
        "pattern": ["VERIFICATION", "TESTING"],
        "keep": "FINAL_VERIFICATION_REPORT.md",
        "archive_prefix": "verification"
    }
}

# Files that should ALWAYS be kept (essential documentation)
ESSENTIAL_DOCS = {
    "README.md",
    "START_HERE.md",
    "GETTING_STARTED.md",
    "USER_GUIDE.md",
    "QUICK_REFERENCE.md",
    "DATABASE_QUICK_REFERENCE.md",
    "MINIO_QUICK_REFERENCE.md",
    "SEED_DATA_QUICK_REFERENCE.md",
    "PRODUCTION_DEPLOYMENT_GUIDE.md",
    "VERSIONING_GUIDE.md",
}

# Docker files to clean up
DOCKER_DUPLICATES = {
    "backend/Dockerfile.base": "Superseded by optimized Dockerfile",
    "backend/Dockerfile.optimized": "Experimental - should be merged or removed",
    "Dockerfile.frontend.production": "Should be consolidated with Dockerfile.frontend",
    "docker-compose.dev.yml": "Should be part of main docker-compose.yml with profiles",
    "docker-compose.elk.yml": "ELK stack - move to optional-services directory",
    "deployment/docker-compose.production.yml": "Duplicate of root docker-compose.production.yml",
}

# Backup files to remove
BACKUP_PATTERNS = [
    "*.backup*",
    "*.old*",
    "*_OLD*",
    "vite.config.backup.ts",
    "vite.config.optimized.ts",
]


class DuplicateCleanupSystem:
    """Intelligent system for cleaning up and preventing duplicates"""

    def __init__(self, root_dir: Path, dry_run: bool = True):
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.archive_dir = ARCHIVE_DIR
        self.stats = {
            "files_archived": 0,
            "files_deleted": 0,
            "space_saved_mb": 0,
            "duplicates_found": 0,
        }
        self.knowledge_base = {}

    def create_archive_structure(self):
        """Create organized archive directory structure"""
        if not self.dry_run:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            for category in DOC_CATEGORIES.keys():
                (self.archive_dir / category).mkdir(exist_ok=True)
        print(f"✅ Archive structure created at: {self.archive_dir}")

    def calculate_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of file for duplicate detection"""
        if not filepath.exists():
            return ""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def find_duplicate_markdown_files(self) -> Dict[str, List[Path]]:
        """Find duplicate markdown files by category"""
        duplicates = defaultdict(list)
        processed_files = set()  # Track files we've already categorized

        # Scan root directory for markdown files
        md_files = list(self.root_dir.glob("*.md"))

        for category, config in DOC_CATEGORIES.items():
            patterns = config["pattern"]
            keep_file = config["keep"]

            for md_file in md_files:
                filename = md_file.name

                # Skip if already processed (prevents duplicate categorization)
                if filename in processed_files:
                    continue

                # Skip essential documentation
                if filename in ESSENTIAL_DOCS:
                    continue

                # Skip the file we want to keep for this category
                if filename == keep_file:
                    continue

                # Check if file matches any pattern for this category
                for pattern in patterns:
                    if pattern in filename:
                        duplicates[category].append(md_file)
                        processed_files.add(filename)
                        break

        return duplicates

    def archive_documentation(self, duplicates: Dict[str, List[Path]]):
        """Archive duplicate documentation files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for category, files in duplicates.items():
            if not files:
                continue

            archive_prefix = DOC_CATEGORIES[category]["archive_prefix"]
            archive_subdir = self.archive_dir / category

            print(f"\n📂 Category: {category.upper()}")
            print(f"   Found {len(files)} duplicate files")

            for file_path in files:
                # Skip if file doesn't exist (may have been moved already)
                if not file_path.exists():
                    print(f"   ⏭️  Skipped (already processed): {file_path.name}")
                    continue

                size_mb = file_path.stat().st_size / (1024 * 1024)
                archive_path = archive_subdir / f"{archive_prefix}_{file_path.name}"

                if not self.dry_run:
                    # Move file to archive
                    shutil.move(str(file_path), str(archive_path))
                    self.stats["files_archived"] += 1
                    self.stats["space_saved_mb"] += size_mb

                print(f"   ✅ Archived: {file_path.name} ({size_mb:.2f} MB)")

                # Update knowledge base
                self.knowledge_base[file_path.name] = {
                    "category": category,
                    "archived_date": timestamp,
                    "original_path": str(file_path),
                    "archive_path": str(archive_path),
                    "size_mb": round(size_mb, 2),
                }

    def cleanup_docker_duplicates(self):
        """Clean up duplicate Docker files"""
        print(f"\n🐳 Cleaning up Docker duplicates...")

        for docker_file, reason in DOCKER_DUPLICATES.items():
            file_path = self.root_dir / docker_file

            if not file_path.exists():
                print(f"   ℹ️  Already removed: {docker_file}")
                continue

            size_mb = file_path.stat().st_size / (1024 * 1024)

            # Archive Docker files instead of deleting
            archive_path = self.archive_dir / "docker" / file_path.name

            if not self.dry_run:
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(archive_path))
                self.stats["files_archived"] += 1
                self.stats["space_saved_mb"] += size_mb

            print(f"   ✅ Archived: {docker_file}")
            print(f"      Reason: {reason}")
            print(f"      Size: {size_mb:.2f} MB")

    def cleanup_backup_files(self):
        """Remove backup and temporary files"""
        print(f"\n🧹 Cleaning up backup files...")

        for pattern in BACKUP_PATTERNS:
            backup_files = list(self.root_dir.glob(pattern))

            for backup_file in backup_files:
                if backup_file.is_file():
                    size_mb = backup_file.stat().st_size / (1024 * 1024)

                    if not self.dry_run:
                        backup_file.unlink()
                        self.stats["files_deleted"] += 1
                        self.stats["space_saved_mb"] += size_mb

                    print(f"   ✅ Deleted: {backup_file.name} ({size_mb:.2f} MB)")

    def create_index_document(self):
        """Create a master index of all documentation"""
        index_path = DOCS_DIR / "DOCUMENTATION_INDEX.md"

        content = f"""# REIMS2 Documentation Index

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This index helps you find documentation quickly and prevents duplicate documentation from being created.

## 📚 Active Documentation

### Essential Documentation
"""

        # List essential docs
        for essential_doc in sorted(ESSENTIAL_DOCS):
            doc_path = self.root_dir / essential_doc
            if doc_path.exists():
                content += f"- [{essential_doc}](../{essential_doc})\n"

        # List category documentation
        content += "\n### Feature Documentation\n\n"
        for category, config in DOC_CATEGORIES.items():
            keep_file = config["keep"]
            doc_path = self.root_dir / keep_file
            if doc_path.exists():
                content += f"- **{category.replace('_', ' ').title()}**: [{keep_file}](../{keep_file})\n"

        # List archived documentation
        content += f"\n## 📦 Archived Documentation\n\n"
        content += "Historical documentation has been archived to prevent clutter. "
        content += "If you need to reference old implementation details:\n\n"

        for category in sorted(DOC_CATEGORIES.keys()):
            archive_subdir = self.archive_dir / category
            if archive_subdir.exists():
                archived_files = list(archive_subdir.glob("*.md"))
                if archived_files:
                    content += f"### {category.replace('_', ' ').title()}\n"
                    for archived_file in sorted(archived_files):
                        rel_path = archived_file.relative_to(self.root_dir)
                        content += f"- [{archived_file.name}]({rel_path})\n"
                    content += "\n"

        # Knowledge base
        content += "\n## 🧠 Documentation Knowledge Base\n\n"
        content += "```json\n"
        content += json.dumps(self.knowledge_base, indent=2)
        content += "\n```\n"

        # Guidelines
        content += """
## 📝 Documentation Guidelines

### Before Creating New Documentation

1. **Check this index first** - Is there already documentation for your topic?
2. **Update existing docs** - Prefer updating over creating new files
3. **Use descriptive names** - Avoid generic names like "IMPLEMENTATION.md"
4. **Follow naming convention**: `FEATURE_NAME_PURPOSE.md`

### Naming Conventions

- **Feature docs**: `FEATURE_NAME_COMPLETE.md` (e.g., `MARKET_INTELLIGENCE_COMPLETE.md`)
- **Guides**: `HOW_TO_*.md` or `*_GUIDE.md`
- **Quick references**: `*_QUICK_REFERENCE.md`
- **README files**: `README_FEATURE.md`

### When Documentation Becomes Outdated

1. Don't delete - archive it to `docs/archive/[category]/`
2. Update this index
3. Add entry to knowledge base
4. Link from current documentation if relevant

### Documentation Lifecycle

```
New Feature
    ↓
Create FEATURE_COMPLETE.md
    ↓
Feature Evolves
    ↓
Update FEATURE_COMPLETE.md
    ↓
Major Refactor
    ↓
Archive old → Create FEATURE_V2_COMPLETE.md
```

## 🚫 What NOT to Do

- ❌ Don't create multiple "IMPLEMENTATION_SUMMARY" files
- ❌ Don't append dates to filenames (use git history instead)
- ❌ Don't create "FINAL_FINAL" or "COMPLETE_COMPLETE" files
- ❌ Don't duplicate information across files
- ❌ Don't commit `.backup` or `.old` files

## 🤖 Automated Cleanup

Run the cleanup script periodically:

```bash
# Dry run (preview only)
python scripts/cleanup_duplicates.py --dry-run

# Actually perform cleanup
python scripts/cleanup_duplicates.py

# Force cleanup without confirmation
python scripts/cleanup_duplicates.py --force
```

## 📊 Cleanup Statistics

Last cleanup: {datetime.now().strftime("%Y-%m-%d")}
- Files archived: {self.stats['files_archived']}
- Files deleted: {self.stats['files_deleted']}
- Space saved: {self.stats['space_saved_mb']:.2f} MB
"""

        if not self.dry_run:
            DOCS_DIR.mkdir(exist_ok=True)
            with open(index_path, 'w') as f:
                f.write(content)

        print(f"\n📋 Created documentation index: {index_path}")
        return content

    def generate_report(self) -> str:
        """Generate cleanup report"""
        report = f"""
{'='*80}
REIMS2 DUPLICATE CLEANUP REPORT
{'='*80}

📅 Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
🔧 Mode: {'DRY RUN (Preview Only)' if self.dry_run else 'LIVE CLEANUP'}

📊 STATISTICS
{'-'*80}
Files Archived:     {self.stats['files_archived']:>4}
Files Deleted:      {self.stats['files_deleted']:>4}
Space Saved:        {self.stats['space_saved_mb']:>8.2f} MB

📂 ARCHIVE LOCATION
{'-'*80}
{self.archive_dir}

🧠 KNOWLEDGE BASE ENTRIES
{'-'*80}
{len(self.knowledge_base)} files indexed

✅ RECOMMENDATIONS
{'-'*80}
1. Review archived files in: {self.archive_dir}
2. Update documentation references to use index
3. Run 'git add' to stage cleanup changes
4. Commit with message: "docs: Clean up duplicate documentation"
5. Set up pre-commit hook to prevent future duplicates

🚀 NEXT STEPS
{'-'*80}
"""

        if self.dry_run:
            report += """
This was a DRY RUN. To actually perform the cleanup:

    python scripts/cleanup_duplicates.py

To skip confirmation:

    python scripts/cleanup_duplicates.py --force
"""
        else:
            report += """
✅ Cleanup complete!

Now run:
    git status
    git add .
    git commit -m "docs: Clean up duplicate documentation and Docker files"
"""

        report += f"\n{'='*80}\n"
        return report

    def run(self):
        """Execute the cleanup process"""
        print("🧹 REIMS2 Intelligent Duplicate Cleanup System")
        print("=" * 80)

        if self.dry_run:
            print("⚠️  DRY RUN MODE - No files will be modified")
        else:
            print("🚀 LIVE MODE - Files will be moved/deleted")

        print("=" * 80)

        # Step 1: Create archive structure
        self.create_archive_structure()

        # Step 2: Find duplicate markdown files
        duplicates = self.find_duplicate_markdown_files()
        self.stats["duplicates_found"] = sum(len(files) for files in duplicates.values())

        # Step 3: Archive documentation
        self.archive_documentation(duplicates)

        # Step 4: Cleanup Docker duplicates
        self.cleanup_docker_duplicates()

        # Step 5: Cleanup backup files
        self.cleanup_backup_files()

        # Step 6: Create documentation index
        self.create_index_document()

        # Step 7: Generate report
        report = self.generate_report()
        print(report)

        # Save report
        if not self.dry_run:
            report_path = self.root_dir / f"CLEANUP_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w') as f:
                f.write(report)
            print(f"📄 Report saved to: {report_path}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="REIMS2 Intelligent Duplicate Cleanup System"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without modifying files (default: True)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Actually perform cleanup (disables dry-run)"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # If --force is specified, disable dry-run
    dry_run = not args.force

    if not dry_run and not args.yes:
        print("\n⚠️  WARNING: This will move and delete files!")
        try:
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != "yes":
                print("Aborted.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

    # Run cleanup
    cleanup_system = DuplicateCleanupSystem(ROOT_DIR, dry_run=dry_run)
    cleanup_system.run()


if __name__ == "__main__":
    main()
