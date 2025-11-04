#!/usr/bin/env python3
"""
GitHub Release Preparation Script for Rubix Token Sync
Automates the creation of cross-platform releases with proper versioning and documentation
"""

import os
import sys
import subprocess
import shutil
import json
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class ReleaseManager:
    """Manages GitHub releases for Rubix Token Sync"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.version = self.get_version()
        self.release_dir = self.project_root / "releases" / f"v{self.version}"
        self.dist_dir = self.project_root / "dist"

        # Platform configurations
        self.platforms = {
            "windows": {
                "executable": "RubixTokenSync.exe",
                "archive_format": "zip",
                "build_command": ["python", "build_executable.py"],
            },
            "macos": {
                "executable": "RubixTokenSync",
                "archive_format": "tar.gz",
                "build_command": ["python3", "build_executable.py"],
            },
            "linux": {
                "executable": "RubixTokenSync",
                "archive_format": "tar.gz",
                "build_command": ["python3", "build_executable.py"],
            }
        }

    def get_version(self) -> str:
        """Get version from git tags or generate one"""
        try:
            # Try to get version from git tags
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True, text=True, cwd=self.project_root
            )
            if result.returncode == 0:
                return result.stdout.strip().lstrip('v')
        except:
            pass

        # Fallback to date-based version
        return datetime.now().strftime("1.0.%Y%m%d")

    def print_status(self, message: str, level: str = "INFO"):
        """Print colored status message"""
        colors = {
            "INFO": "\033[0;34m",     # Blue
            "SUCCESS": "\033[0;32m",  # Green
            "WARNING": "\033[1;33m",  # Yellow
            "ERROR": "\033[0;31m",    # Red
            "RESET": "\033[0m"        # Reset
        }

        color = colors.get(level, colors["INFO"])
        reset = colors["RESET"]
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp} {level}]{reset} {message}")

    def clean_release_directory(self):
        """Clean and create release directory"""
        if self.release_dir.exists():
            shutil.rmtree(self.release_dir)

        self.release_dir.mkdir(parents=True, exist_ok=True)
        self.print_status(f"Created release directory: {self.release_dir}")

    def create_release_notes(self) -> str:
        """Generate release notes"""
        release_notes = f"""# Rubix Token Sync v{self.version}

## 🚀 Cross-Platform Executable Release

This release provides standalone executables for all major operating systems. No installation required!

### ✨ New Features

- **🖥️ Interactive Menu System**: User-friendly interface with guided setup
- **⚙️ Automatic Configuration**: Pre-configured Telegram, simple MSSQL setup
- **🔍 Per-Node IPFS Detection**: Automatic binary discovery for each node
- **📊 System Compatibility Checking**: Built-in diagnostics and validation
- **📱 Real-time Notifications**: Integrated Telegram bot for live updates
- **🗄️ Azure SQL Database Integration**: Enterprise-grade database sync
- **📈 Advanced Progress Tracking**: Visual progress bars with ETA calculations

### 📦 Platform Support

| Platform | File | Size | Notes |
|----------|------|------|-------|
| **Windows** | `RubixTokenSync-windows-v{self.version}.zip` | ~25MB | Windows 10+ (64-bit) |
| **macOS** | `RubixTokenSync-macos-v{self.version}.tar.gz` | ~25MB | macOS 10.14+ (Universal) |
| **Linux** | `RubixTokenSync-linux-v{self.version}.tar.gz` | ~25MB | Ubuntu 18.04+, CentOS 7+ |

### 🔧 Quick Start

1. **Download** the appropriate file for your OS
2. **Extract** the archive
3. **Run** the executable:
   - Windows: Double-click `RubixTokenSync.exe`
   - macOS/Linux: `./RubixTokenSync`
4. **Follow** the interactive setup prompts

### 📋 What's Included

Each release package contains:
- ✅ Main executable (all dependencies bundled)
- ✅ Configuration templates
- ✅ Documentation and README
- ✅ Quick start guide

### 💻 System Requirements

- **Memory**: 2GB RAM minimum
- **Disk**: 1GB free space minimum
- **Network**: Internet connection required
- **OS**: Windows 10+, macOS 10.14+, or Linux (64-bit)

### 🔒 Pre-configured Settings

- **Telegram Bot**: Pre-configured with audit bot credentials
- **MSSQL Setup**: Interactive guided configuration
- **IPFS Detection**: Automatic binary discovery
- **Logging**: Comprehensive audit trails included

### 🚀 Performance Improvements

- **Parallel Processing**: Multi-core IPFS fetching
- **Batch Operations**: 1000-record batches for efficiency
- **Smart Retry Logic**: Automatic error recovery
- **Memory Optimization**: Efficient large dataset handling

### 🐛 Bug Fixes

- Fixed per-node IPFS binary detection
- Improved error handling for missing dependencies
- Enhanced multiprocessing stability
- Better connection pool management

### 📚 Documentation

- [Complete User Guide](README_EXECUTABLE.md)
- [System Compatibility](system_checker.py)
- [Configuration Guide](config_manager.py)

### 📞 Support

For issues or questions:
1. Check the included documentation
2. Run the system compatibility checker
3. Review log files for detailed information
4. Create an issue on GitHub

---

**Built on**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Commit**: {self.get_git_commit()}
"""
        return release_notes

    def get_git_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, cwd=self.project_root
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "unknown"

    def copy_documentation(self):
        """Copy documentation files to release"""
        docs_to_copy = [
            "README_EXECUTABLE.md",
            "requirements.txt",
            "azure_sql_connection_template.txt",
            "telegram_config_template.json",
        ]

        for doc in docs_to_copy:
            src = self.project_root / doc
            if src.exists():
                dst = self.release_dir / doc
                shutil.copy2(src, dst)
                self.print_status(f"Copied {doc}")

    def create_platform_package(self, platform: str, executable_path: Path) -> Optional[Path]:
        """Create platform-specific release package"""
        if not executable_path.exists():
            self.print_status(f"Executable not found: {executable_path}", "ERROR")
            return None

        config = self.platforms[platform]
        package_name = f"RubixTokenSync-{platform}-v{self.version}"
        package_dir = self.release_dir / package_name
        package_dir.mkdir(exist_ok=True)

        # Copy executable
        executable_name = config["executable"]
        shutil.copy2(executable_path, package_dir / executable_name)

        # Make executable on Unix systems
        if platform in ["macos", "linux"]:
            os.chmod(package_dir / executable_name, 0o755)

        # Copy documentation
        docs_to_include = [
            "README_EXECUTABLE.md",
            "requirements.txt",
            "azure_sql_connection_template.txt",
            "telegram_config_template.json",
        ]

        for doc in docs_to_include:
            src = self.project_root / doc
            if src.exists():
                shutil.copy2(src, package_dir / doc)

        # Create platform-specific README
        readme_content = f"""# Rubix Token Sync v{self.version} - {platform.title()}

## Quick Start

1. Run the executable:
   {"   Double-click RubixTokenSync.exe" if platform == "windows" else "   ./RubixTokenSync"}

2. Follow the interactive setup prompts

3. Configure MSSQL credentials when prompted

4. Start syncing!

## Files Included

- {executable_name} - Main executable
- README_EXECUTABLE.md - Complete user guide
- *.txt - Configuration templates

## System Requirements

{"- Windows 10+ (64-bit)" if platform == "windows" else "- macOS 10.14+ (Universal binary)" if platform == "macos" else "- Linux 64-bit (Ubuntu 18.04+, CentOS 7+)"}
- 2GB RAM minimum
- 1GB free disk space
- Internet connection

## Support

See README_EXECUTABLE.md for detailed documentation and troubleshooting.

Built on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(package_dir / "README.txt", "w") as f:
            f.write(readme_content)

        # Create archive
        archive_format = config["archive_format"]
        if archive_format == "zip":
            archive_path = self.release_dir / f"{package_name}.zip"
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in package_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(package_dir)
                        zf.write(file_path, arcname)
        else:
            archive_path = self.release_dir / f"{package_name}.tar.gz"
            with tarfile.open(archive_path, 'w:gz') as tf:
                tf.add(package_dir, arcname=package_name)

        # Clean up directory (keep only archive)
        shutil.rmtree(package_dir)

        archive_size = archive_path.stat().st_size / (1024 * 1024)  # MB
        self.print_status(f"Created {platform} package: {archive_path.name} ({archive_size:.1f} MB)", "SUCCESS")

        return archive_path

    def create_current_platform_release(self) -> bool:
        """Create release for current platform"""
        self.print_status("Creating release for current platform...")

        # Check if we have a built executable
        current_executable = self.dist_dir / "RubixTokenSync"
        if not current_executable.exists():
            # Try to find .exe for Windows
            current_executable = self.dist_dir / "RubixTokenSync.exe"

        if not current_executable.exists():
            self.print_status("No executable found. Building...", "WARNING")

            # Build executable
            try:
                result = subprocess.run(
                    ["python3", "build_executable.py"],
                    cwd=self.project_root,
                    check=True
                )

                # Check again
                current_executable = self.dist_dir / "RubixTokenSync"
                if not current_executable.exists():
                    current_executable = self.dist_dir / "RubixTokenSync.exe"

                if not current_executable.exists():
                    self.print_status("Failed to build executable", "ERROR")
                    return False

            except subprocess.CalledProcessError as e:
                self.print_status(f"Build failed: {e}", "ERROR")
                return False

        # Determine platform
        import platform
        system = platform.system().lower()
        if system == "darwin":
            platform_name = "macos"
        elif system == "windows":
            platform_name = "windows"
        else:
            platform_name = "linux"

        # Create package
        package_path = self.create_platform_package(platform_name, current_executable)
        return package_path is not None

    def generate_release_manifest(self) -> Dict:
        """Generate release manifest"""
        manifest = {
            "version": self.version,
            "build_date": datetime.now().isoformat(),
            "git_commit": self.get_git_commit(),
            "platforms": {},
            "files": []
        }

        # List all files in release directory
        for file_path in self.release_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.release_dir)
                file_size = file_path.stat().st_size

                manifest["files"].append({
                    "name": str(relative_path),
                    "size": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 1)
                })

        return manifest

    def create_release(self):
        """Create complete release"""
        self.print_status(f"Creating release v{self.version}")

        # Clean and setup
        self.clean_release_directory()

        # Copy documentation
        self.copy_documentation()

        # Create current platform release
        if not self.create_current_platform_release():
            self.print_status("Failed to create platform release", "ERROR")
            return False

        # Create release notes
        release_notes = self.create_release_notes()
        with open(self.release_dir / "RELEASE_NOTES.md", "w") as f:
            f.write(release_notes)

        # Create manifest
        manifest = self.generate_release_manifest()
        with open(self.release_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        self.print_status("Release created successfully!", "SUCCESS")
        self.show_release_summary()

        return True

    def show_release_summary(self):
        """Show release summary"""
        print("\n" + "=" * 60)
        self.print_status(f"Release v{self.version} Summary", "SUCCESS")
        print("=" * 60)

        print(f"📁 Release Directory: {self.release_dir}")
        print(f"🏷️  Version: v{self.version}")
        print(f"📅 Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Git Commit: {self.get_git_commit()}")
        print()

        print("📦 Release Files:")
        total_size = 0
        for file_path in self.release_dir.rglob('*'):
            if file_path.is_file():
                size = file_path.stat().st_size
                size_mb = size / (1024 * 1024)
                total_size += size
                print(f"   📄 {file_path.name} ({size_mb:.1f} MB)")

        print(f"\n💾 Total Size: {total_size / (1024 * 1024):.1f} MB")
        print()

        print("🚀 Next Steps:")
        print("1. Test the executable on target platforms")
        print("2. Commit and push changes to GitHub:")
        print(f"   git add .")
        print(f"   git commit -m 'Release v{self.version}'")
        print(f"   git tag v{self.version}")
        print(f"   git push origin main --tags")
        print("3. Create GitHub release and upload files")
        print("4. Update documentation if needed")

def main():
    """Main release preparation"""
    release_manager = ReleaseManager()

    print("🚀 Rubix Token Sync - Release Manager")
    print("=" * 50)

    try:
        success = release_manager.create_release()
        if success:
            print("\n🎉 Release preparation completed successfully!")
        else:
            print("\n❌ Release preparation failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n👋 Release preparation cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()