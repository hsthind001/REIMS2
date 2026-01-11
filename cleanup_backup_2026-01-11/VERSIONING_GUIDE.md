# Versioning Guide

This project uses **Semantic Versioning** (SemVer) for releases: `MAJOR.MINOR.PATCH`

- **MAJOR** (v1.0.0 → v2.0.0): Breaking changes, major feature additions
- **MINOR** (v1.0.0 → v1.1.0): New features, backward compatible
- **PATCH** (v1.0.0 → v1.0.1): Bug fixes, backward compatible

## Current Version

**v1.0.0** - Concordance Table System Release

## Creating a New Version

### Option 1: Manual Version Creation

After committing your changes:

```bash
# 1. Commit your changes
git add -A
git commit -m "feat: Your feature description"

# 2. Create and push version tag
git tag -a v1.1.0 -m "Version 1.1.0: Your release description"
git push origin master
git push origin v1.1.0
```

### Option 2: Using the Version Script

```bash
# Make it executable (first time only)
chmod +x scripts/create_version.sh

# Create a new version
./scripts/create_version.sh 1.1.0 "Version 1.1.0: Your release description"
```

### Option 3: Quick Version Bump

For patch/minor versions, you can use:

```bash
# Patch version (bug fix)
./scripts/create_version.sh patch "Bug fix description"

# Minor version (new feature)
./scripts/create_version.sh minor "New feature description"

# Major version (breaking change)
./scripts/create_version.sh major "Major change description"
```

## Version Naming Convention

- Use semantic versioning: `v1.0.0`, `v1.1.0`, `v2.0.0`
- Tag format: `v{MAJOR}.{MINOR}.{PATCH}`
- Tag message should describe what's in the release

## Viewing Versions

```bash
# List all versions
git tag --sort=-v:refname

# View version details
git show v1.0.0

# Compare versions
git diff v1.0.0 v1.1.0
```

## Best Practices

1. **Always commit before creating a version tag**
2. **Use descriptive commit messages** following conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code refactoring
   - `test:` for tests
   - `chore:` for maintenance

3. **Version tags should reference completed features**, not work-in-progress

4. **Push both commits and tags**:
   ```bash
   git push origin master
   git push origin v1.1.0
   ```

5. **Create a release on GitHub** after pushing the tag for better visibility

## Example Workflow

```bash
# 1. Make your changes
# ... edit files ...

# 2. Stage and commit
git add -A
git commit -m "feat: Add new feature X"

# 3. Create version tag
git tag -a v1.1.0 -m "Version 1.1.0: Add feature X"
git push origin master
git push origin v1.1.0

# 4. (Optional) Create GitHub release
# Go to: https://github.com/hsthind001/REIMS2/releases/new
# Select tag: v1.1.0
# Add release notes
```

## Version History

- **v1.0.0** (2025-11-24): Concordance Table System Release
  - Automatic concordance table generation
  - Field-by-field model comparison
  - CSV/Excel export functionality
  - Complete integration with extraction workflow

