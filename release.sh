#!/bin/bash
# Release script for StorySpark Agent

# Exit on error
set -e

# Check if version is provided
if [ -z "$1" ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 0.9.0"
    exit 1
fi

VERSION=$1
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Ensure we're on main branch
if [ "$BRANCH" != "main" ]; then
    echo "Error: You must be on the main branch to create a release"
    exit 1
fi

# Update version in files
echo "Updating version to $VERSION..."
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/__version__.py
sed -i "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
sed -i "s/version=\".*\"/version=\"$VERSION\"/" setup.py
sed -i "s/version-.*-blue/version-$VERSION-blue/" README.md

# Update CHANGELOG
echo "Don't forget to update CHANGELOG.md with the new version notes!"

# Stage changes
git add src/__version__.py pyproject.toml setup.py README.md

# Commit
git commit -m "Bump version to $VERSION"

# Create tag
git tag -a "v$VERSION" -m "Release version $VERSION"

# Push changes
echo "Pushing changes and tag..."
git push origin main
git push origin "v$VERSION"

echo "Release v$VERSION completed!"
echo "Next steps:"
echo "1. Create release on GitHub with release notes"
echo "2. Build and upload to PyPI: python -m build && twine upload dist/*"
