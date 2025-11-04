#!/usr/bin/env python3
"""
Build Script for Rubix Token Sync Executable
Automates the creation of cross-platform executables using PyInstaller
"""

import os
import sys
import subprocess
import shutil
import platform
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

class ExecutableBuilder:
    """Handles building cross-platform executables"""

    def __init__(self):
        self.current_dir = Path.cwd()
        self.build_dir = self.current_dir / "build"
        self.dist_dir = self.current_dir / "dist"
        self.spec_file = self.current_dir / "rubix_sync.spec"

        # Platform-specific settings
        self.platform_system = platform.system()
        self.platform_arch = platform.machine()

        # Executable names
        self.app_name = "RubixTokenSync"
        if self.platform_system == "Windows":
            self.executable_name = f"{self.app_name}.exe"
        else:
            self.executable_name = self.app_name

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
        timestamp = time.strftime("%H:%M:%S")
        print(f"{color}[{timestamp} {level}]{reset} {message}")

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are available"""
        self.print_status("Checking build prerequisites...")

        errors = []

        # Check Python version
        if sys.version_info < (3, 8):
            errors.append(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}")

        # Check PyInstaller
        try:
            import PyInstaller
            self.print_status(f"PyInstaller version: {PyInstaller.__version__}", "SUCCESS")
        except ImportError:
            errors.append("PyInstaller not installed. Run: pip install pyinstaller")

        # Check required modules
        required_modules = [
            "pyodbc",
            "requests",
            "psutil"
        ]

        for module in required_modules:
            try:
                __import__(module)
                self.print_status(f"✅ {module} available", "SUCCESS")
            except ImportError:
                errors.append(f"Required module missing: {module}")

        # Check required files
        required_files = [
            "rubix_sync_main.py",
            "rubix_launcher.py",
            "config_manager.py",
            "system_checker.py",
            "sync_distributed_tokens.py",
            "rubix_sync.spec"
        ]

        for file in required_files:
            file_path = self.current_dir / file
            if file_path.exists():
                self.print_status(f"✅ {file} found", "SUCCESS")
            else:
                errors.append(f"Required file missing: {file}")

        if errors:
            self.print_status("Prerequisites check failed:", "ERROR")
            for error in errors:
                print(f"   ❌ {error}")
            return False

        self.print_status("✅ All prerequisites satisfied", "SUCCESS")
        return True

    def clean_build_directories(self):
        """Clean previous build artifacts"""
        self.print_status("Cleaning build directories...")

        directories_to_clean = [self.build_dir, self.dist_dir]

        for directory in directories_to_clean:
            if directory.exists():
                try:
                    shutil.rmtree(directory)
                    self.print_status(f"Cleaned {directory.name}/", "SUCCESS")
                except Exception as e:
                    self.print_status(f"Warning: Could not clean {directory}: {e}", "WARNING")

    def install_dependencies(self):
        """Install build dependencies"""
        self.print_status("Installing build dependencies...")

        dependencies = [
            "pyinstaller>=5.0",
            "pyodbc",
            "requests",
            "psutil"
        ]

        for dep in dependencies:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", dep],
                             check=True, capture_output=True)
                self.print_status(f"✅ Installed {dep}", "SUCCESS")
            except subprocess.CalledProcessError as e:
                self.print_status(f"❌ Failed to install {dep}: {e}", "ERROR")
                return False

        return True

    def build_executable(self, clean: bool = True) -> bool:
        """Build the executable using PyInstaller"""
        self.print_status(f"Building executable for {self.platform_system} {self.platform_arch}...")

        if clean:
            self.clean_build_directories()

        # Build command
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(self.spec_file),
            "--clean",
            "--noconfirm"
        ]

        try:
            self.print_status(f"Running: {' '.join(cmd)}")

            # Run PyInstaller
            process = subprocess.run(cmd, cwd=self.current_dir, capture_output=True, text=True)

            if process.returncode == 0:
                self.print_status("✅ Build completed successfully!", "SUCCESS")

                # Check if executable was created
                executable_path = self.dist_dir / self.executable_name
                if executable_path.exists():
                    file_size = executable_path.stat().st_size / (1024 * 1024)  # MB
                    self.print_status(f"✅ Executable created: {executable_path} ({file_size:.1f} MB)", "SUCCESS")
                    return True
                else:
                    self.print_status(f"❌ Executable not found at {executable_path}", "ERROR")
                    return False
            else:
                self.print_status("❌ Build failed!", "ERROR")
                if process.stderr:
                    print("STDERR:")
                    print(process.stderr)
                if process.stdout:
                    print("STDOUT:")
                    print(process.stdout)
                return False

        except Exception as e:
            self.print_status(f"❌ Build error: {e}", "ERROR")
            return False

    def test_executable(self) -> bool:
        """Test the built executable"""
        executable_path = self.dist_dir / self.executable_name

        if not executable_path.exists():
            self.print_status("❌ Executable not found for testing", "ERROR")
            return False

        self.print_status("Testing executable...")

        # Test help command
        try:
            result = subprocess.run([str(executable_path), "--help"],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and "Rubix Token Sync Tool" in result.stdout:
                self.print_status("✅ Executable help test passed", "SUCCESS")
            else:
                self.print_status("❌ Executable help test failed", "ERROR")
                print(f"Return code: {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.print_status("❌ Executable test timed out", "ERROR")
            return False
        except Exception as e:
            self.print_status(f"❌ Executable test error: {e}", "ERROR")
            return False

        return True

    def create_distribution_package(self) -> bool:
        """Create a distribution package"""
        executable_path = self.dist_dir / self.executable_name

        if not executable_path.exists():
            self.print_status("❌ Executable not found for packaging", "ERROR")
            return False

        self.print_status("Creating distribution package...")

        # Create distribution directory
        package_name = f"{self.app_name}_{self.platform_system}_{self.platform_arch}".lower()
        package_dir = self.dist_dir / package_name
        package_dir.mkdir(exist_ok=True)

        try:
            # Copy executable
            shutil.copy2(executable_path, package_dir)

            # Copy documentation and templates
            docs_to_copy = [
                "requirements.txt",
                "azure_sql_connection_template.txt",
                "telegram_config_template.json"
            ]

            for doc in docs_to_copy:
                doc_path = self.current_dir / doc
                if doc_path.exists():
                    shutil.copy2(doc_path, package_dir)

            # Create README for the package
            readme_content = f"""# {self.app_name}

Cross-Platform Distributed Token Synchronization Tool

## Quick Start

1. Run the executable:
   - Windows: Double-click {self.executable_name} or run from command prompt
   - macOS/Linux: Run ./{self.executable_name} from terminal

2. The tool will start in interactive mode and guide you through:
   - Setting up database credentials
   - Configuring notifications
   - Running token synchronization

## Command Line Usage

Run with --help for all options:
```
./{self.executable_name} --help
```

## Configuration

The tool will create configuration files in the same directory:
- azure_sql_connection.txt - Database credentials
- telegram_config.json - Notification settings

## System Requirements

- Memory: 2GB RAM minimum
- Disk: 1GB free space minimum
- Network: Internet connection required
- OS: Windows 10+, macOS 10.14+, or Linux (64-bit)

## Support

For issues or questions, refer to the project documentation.

Built on: {time.strftime('%Y-%m-%d %H:%M:%S')}
Platform: {self.platform_system} {self.platform_arch}
"""

            readme_path = package_dir / "README.txt"
            with open(readme_path, 'w') as f:
                f.write(readme_content)

            # Create archive
            if self.platform_system == "Windows":
                archive_format = "zip"
                archive_ext = ".zip"
            else:
                archive_format = "gztar"
                archive_ext = ".tar.gz"

            archive_name = f"{package_name}{archive_ext}"
            archive_path = self.dist_dir / archive_name

            shutil.make_archive(
                base_name=str(archive_path.with_suffix('')),
                format=archive_format,
                root_dir=str(self.dist_dir),
                base_dir=package_name
            )

            if archive_path.exists():
                archive_size = archive_path.stat().st_size / (1024 * 1024)  # MB
                self.print_status(f"✅ Distribution package created: {archive_path} ({archive_size:.1f} MB)", "SUCCESS")
                return True
            else:
                self.print_status("❌ Failed to create distribution package", "ERROR")
                return False

        except Exception as e:
            self.print_status(f"❌ Error creating distribution package: {e}", "ERROR")
            return False

    def show_build_summary(self):
        """Show build summary"""
        self.print_status("Build Summary", "SUCCESS")
        print("=" * 60)

        # List generated files
        if self.dist_dir.exists():
            print("Generated files:")
            for item in self.dist_dir.iterdir():
                if item.is_file():
                    size = item.stat().st_size / (1024 * 1024)  # MB
                    print(f"  📄 {item.name} ({size:.1f} MB)")
                elif item.is_dir():
                    print(f"  📁 {item.name}/")

        print()
        print("To distribute the executable:")
        print(f"  1. Share the entire {self.app_name}*.zip/.tar.gz package")
        print("  2. Users extract and run the executable")
        print("  3. No installation required - runs standalone")
        print()

def main():
    """Main build script"""
    builder = ExecutableBuilder()

    print("🏗️  Rubix Token Sync - Executable Builder")
    print("=" * 50)
    print()

    # Check command line arguments
    install_deps = "--install-deps" in sys.argv
    skip_test = "--skip-test" in sys.argv
    clean_only = "--clean-only" in sys.argv

    if clean_only:
        builder.clean_build_directories()
        return

    # Install dependencies if requested
    if install_deps:
        if not builder.install_dependencies():
            sys.exit(1)

    # Check prerequisites
    if not builder.check_prerequisites():
        print()
        print("💡 To install missing dependencies, run:")
        print("   python build_executable.py --install-deps")
        sys.exit(1)

    # Build executable
    if not builder.build_executable():
        sys.exit(1)

    # Test executable
    if not skip_test:
        if not builder.test_executable():
            print()
            print("⚠️  Executable test failed, but build completed.")
            print("   You may still be able to use the executable.")

    # Create distribution package
    if not builder.create_distribution_package():
        print()
        print("⚠️  Failed to create distribution package.")
        print("   Executable is still available in dist/ directory.")

    # Show summary
    print()
    builder.show_build_summary()

    print("🎉 Build process completed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Build cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)