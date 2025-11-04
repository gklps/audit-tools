#!/bin/bash
# Cross-Platform Build Script
# Run this on different platforms to create all builds

set -e

VERSION="v1.0.20251104"
PLATFORMS=("windows" "macos" "linux")
CURRENT_PLATFORM=""

# Detect current platform
case "$(uname -s)" in
    Darwin*)    CURRENT_PLATFORM="macos" ;;
    Linux*)     CURRENT_PLATFORM="linux" ;;
    CYGWIN*|MINGW32*|MSYS*|MINGW*) CURRENT_PLATFORM="windows" ;;
    *)          echo "❌ Unknown platform: $(uname -s)" && exit 1 ;;
esac

echo "🏗️  Cross-Platform Build Script"
echo "Current Platform: $CURRENT_PLATFORM"
echo "Version: $VERSION"
echo "=================================="

# Function to build for current platform
build_current_platform() {
    echo "📦 Building for $CURRENT_PLATFORM..."

    # Clean previous builds
    rm -rf build/ dist/

    # Install dependencies
    echo "📥 Installing dependencies..."
    pip install pyinstaller psutil pyodbc requests

    # Remove conflicting packages
    pip uninstall -y pathlib 2>/dev/null || true

    # Build executable
    echo "🔨 Building executable..."
    python3 build_executable.py

    # Verify build
    if [ "$CURRENT_PLATFORM" = "windows" ]; then
        EXECUTABLE="dist/RubixTokenSync.exe"
    else
        EXECUTABLE="dist/RubixTokenSync"
    fi

    if [ ! -f "$EXECUTABLE" ]; then
        echo "❌ Build failed - executable not found"
        exit 1
    fi

    # Test executable
    echo "🧪 Testing executable..."
    if [ "$CURRENT_PLATFORM" = "windows" ]; then
        "$EXECUTABLE" --help > /dev/null
    else
        "$EXECUTABLE" --help > /dev/null
    fi

    echo "✅ Build completed successfully!"

    # Create release package
    echo "📦 Creating release package..."
    python3 prepare_release.py

    echo "🎉 Release package created for $CURRENT_PLATFORM"
    echo "📁 Location: releases/$VERSION/"
}

# Function to create manual builds on other platforms
create_build_instructions() {
    echo ""
    echo "📋 To build on other platforms:"
    echo ""

    for platform in "${PLATFORMS[@]}"; do
        if [ "$platform" != "$CURRENT_PLATFORM" ]; then
            echo "🖥️  For $platform:"
            echo "   1. Clone repository: git clone https://github.com/gklps/audit-tools.git"
            echo "   2. Checkout tag: git checkout $VERSION"
            echo "   3. Run: ./build_all_platforms.sh"
            echo ""
        fi
    done

    echo "📤 After building on all platforms:"
    echo "   1. Collect all platform packages from releases/$VERSION/"
    echo "   2. Upload to GitHub release manually or use ./manual_release.sh"
    echo ""
}

# Main execution
echo "🚀 Starting build process..."
build_current_platform

echo ""
echo "✅ Current platform build complete!"
create_build_instructions

# Check if we can create GitHub release
if command -v gh &> /dev/null && gh auth status &> /dev/null; then
    echo "🔗 GitHub CLI detected and authenticated"
    echo "💡 Run ./manual_release.sh to create GitHub release"
else
    echo "💡 To create GitHub release:"
    echo "   1. Install GitHub CLI: https://cli.github.com/"
    echo "   2. Authenticate: gh auth login"
    echo "   3. Run: ./manual_release.sh"
    echo "   OR upload manually to: https://github.com/gklps/audit-tools/releases/new"
fi

echo ""
echo "🎯 Build Summary:"
echo "   Platform: $CURRENT_PLATFORM ✅"
echo "   Version: $VERSION"
echo "   Package: releases/$VERSION/RubixTokenSync-$CURRENT_PLATFORM-$VERSION.*"