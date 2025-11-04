#!/bin/bash
# Manual Release Creation Script
# Use this if GitHub Actions doesn't work

echo "🚀 Creating Manual GitHub Release"
echo "=================================="

VERSION="v1.0.20251104"
RELEASE_DIR="releases/$VERSION"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "Install it from: https://cli.github.com/"
    echo ""
    echo "Alternative: Create release manually on GitHub:"
    echo "1. Go to: https://github.com/gklps/audit-tools/releases/new"
    echo "2. Tag: $VERSION"
    echo "3. Title: Release $VERSION"
    echo "4. Upload files from: $RELEASE_DIR/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

# Create release
echo "📦 Creating GitHub release..."
gh release create $VERSION \
    --title "Release $VERSION" \
    --notes-file "$RELEASE_DIR/RELEASE_NOTES.md" \
    "$RELEASE_DIR"/*.tar.gz \
    "$RELEASE_DIR"/*.zip \
    "$RELEASE_DIR/README_EXECUTABLE.md" \
    "$RELEASE_DIR/manifest.json"

echo "✅ Release created successfully!"
echo "🔗 View at: https://github.com/gklps/audit-tools/releases/tag/$VERSION"