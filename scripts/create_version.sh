#!/bin/bash

# Version Creation Script
# Usage:
#   ./scripts/create_version.sh 1.1.0 "Version description"
#   ./scripts/create_version.sh patch "Bug fix description"
#   ./scripts/create_version.sh minor "New feature description"
#   ./scripts/create_version.sh major "Breaking change description"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current version
get_current_version() {
    local latest_tag=$(git tag --sort=-v:refname | head -1)
    if [ -z "$latest_tag" ]; then
        echo "0.0.0"
    else
        echo "${latest_tag#v}"  # Remove 'v' prefix
    fi
}

# Bump version
bump_version() {
    local version=$1
    local bump_type=$2
    
    IFS='.' read -ra VERSION_PARTS <<< "$version"
    local major=${VERSION_PARTS[0]}
    local minor=${VERSION_PARTS[1]}
    local patch=${VERSION_PARTS[2]}
    
    case $bump_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            echo -e "${RED}Error: Invalid bump type '$bump_type'. Use: major, minor, or patch${NC}"
            exit 1
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

# Main script
if [ $# -lt 1 ]; then
    echo -e "${RED}Usage:${NC}"
    echo "  $0 <version> <description>"
    echo "  $0 <patch|minor|major> <description>"
    echo ""
    echo "Examples:"
    echo "  $0 1.1.0 \"Version 1.1.0: New feature\""
    echo "  $0 patch \"Bug fix for issue #123\""
    echo "  $0 minor \"Add new API endpoint\""
    exit 1
fi

VERSION_INPUT=$1
DESCRIPTION=${2:-"Version release"}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Warning: You have uncommitted changes.${NC}"
    echo "Please commit your changes before creating a version tag."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Determine version
if [[ "$VERSION_INPUT" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Explicit version provided
    VERSION=$VERSION_INPUT
elif [[ "$VERSION_INPUT" =~ ^(major|minor|patch)$ ]]; then
    # Bump type provided
    CURRENT_VERSION=$(get_current_version)
    VERSION=$(bump_version "$CURRENT_VERSION" "$VERSION_INPUT")
    echo -e "${GREEN}Bumping version from v$CURRENT_VERSION to v$VERSION${NC}"
else
    echo -e "${RED}Error: Invalid version format '$VERSION_INPUT'${NC}"
    echo "Use semantic versioning (e.g., 1.1.0) or bump type (patch/minor/major)"
    exit 1
fi

# Check if version already exists
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo -e "${RED}Error: Version v$VERSION already exists${NC}"
    exit 1
fi

# Create tag
TAG_NAME="v$VERSION"
echo -e "${GREEN}Creating version tag: $TAG_NAME${NC}"
echo -e "Description: $DESCRIPTION"

git tag -a "$TAG_NAME" -m "Version $VERSION: $DESCRIPTION"

# Show tag info
echo ""
echo -e "${GREEN}✅ Version tag created successfully!${NC}"
echo ""
echo "Tag: $TAG_NAME"
echo "Message: Version $VERSION: $DESCRIPTION"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Push commits: git push origin master"
echo "  2. Push tag: git push origin $TAG_NAME"
echo ""
echo "Or push both at once:"
echo "  git push origin master && git push origin $TAG_NAME"

