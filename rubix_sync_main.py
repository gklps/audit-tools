#!/usr/bin/env python3
"""
Rubix Token Sync - Main Entry Point
Unified entry point for both interactive launcher and direct command-line usage
"""

import os
import sys
import subprocess
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def is_interactive_mode() -> bool:
    """Check if we should run in interactive mode"""
    # Run interactive mode if:
    # 1. No command line arguments provided
    # 2. Explicitly requested with --interactive
    # 3. Running as compiled executable with no args

    if len(sys.argv) == 1:
        return True

    if "--interactive" in sys.argv:
        return True

    # Check if running as compiled executable (PyInstaller)
    if hasattr(sys, 'frozen') and len(sys.argv) == 1:
        return True

    return False

def should_show_help() -> bool:
    """Check if help should be displayed"""
    help_args = ["--help", "-h", "help"]
    return any(arg in sys.argv for arg in help_args)

def show_usage():
    """Show comprehensive usage information"""
    print("[RUBIX] Rubix Token Sync Tool")
    print("Cross-Platform Distributed Token Synchronization")
    print("=" * 60)
    print()
    print("USAGE:")
    print("  rubix_sync_main.py [options]              # Interactive menu (default)")
    print("  rubix_sync_main.py --interactive          # Force interactive mode")
    print("  rubix_sync_main.py [sync_options]         # Direct command-line sync")
    print()
    print("INTERACTIVE MODE (Default):")
    print("  When no arguments are provided, launches an interactive menu with:")
    print("  • Configuration setup for MSSQL and Telegram")
    print("  • System compatibility checking")
    print("  • Multiple sync options (standard, full, cleanup, etc.)")
    print("  • Connection testing")
    print("  • System information display")
    print()
    print("DIRECT SYNC OPTIONS:")
    print("  --clear          Clear all existing records before sync")
    print("  --force-ipfs     Force IPFS fetch for all tokens (re-fetch)")
    print("  --cleanup-locks  Clean up IPFS lock errors from database")
    print("  --essential-only Capture only essential metadata (fast, no IPFS)")
    print("  --test-only      Only test connections, don't run sync")
    print("  --help, -h       Show this help message")
    print()
    print("EXAMPLES:")
    print("  rubix_sync_main.py                        # Interactive menu")
    print("  rubix_sync_main.py --clear --force-ipfs   # Complete fresh sync")
    print("  rubix_sync_main.py --force-ipfs          # Re-fetch IPFS data only")
    print("  rubix_sync_main.py --cleanup-locks       # Clean up IPFS lock errors")
    print("  rubix_sync_main.py --essential-only      # Fast metadata capture")
    print("  rubix_sync_main.py --test-only           # Test connections only")
    print()
    print("FEATURES:")
    print("  [IPFS]  Per-node IPFS detection (automatic binary discovery)")
    print("  [DATA] SQLite schema compatibility (handles missing columns)")
    print("  [SYNC] Universal IPFS binary detection")
    print("  [DB]  Azure SQL Database integration")
    print("  [TELEGRAM] Real-time Telegram notifications")
    print("  [DATA] Comprehensive audit logging")
    print("  [PLATFORM]  Cross-platform compatibility (Windows/macOS/Linux)")
    print()
    print("CONFIGURATION:")
    print("  Configuration files are automatically created in the current directory:")
    print("  • azure_sql_connection.txt  - Database credentials")
    print("  • telegram_config.json      - Notification settings")
    print()
    print("  Use interactive mode to set up credentials with guided prompts.")

def run_interactive_launcher():
    """Run the interactive launcher"""
    try:
        from rubix_launcher import RubixLauncher
        launcher = RubixLauncher()
        launcher.show_main_menu()
    except ImportError as e:
        print(f"[ERROR] Error: Could not import launcher module: {e}")
        print("Please ensure all required files are present.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error running interactive launcher: {e}")
        sys.exit(1)

def run_direct_sync():
    """Run direct sync with command-line arguments"""
    try:
        # Import and run the main sync function
        sys.path.insert(0, str(current_dir))

        # Remove our entry point from argv to pass clean args to sync script
        original_argv = sys.argv[:]

        # Call the main sync script directly
        from sync_distributed_tokens import main as sync_main

        # Run the sync
        sync_main()

    except ImportError as e:
        print(f"[ERROR] Error: Could not import sync module: {e}")
        print("Please ensure sync_distributed_tokens.py is present.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error running sync: {e}")
        sys.exit(1)

def check_basic_requirements():
    """Check basic requirements before running"""
    errors = []

    # Check Python version
    if sys.version_info < (3, 8):
        errors.append(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}")

    # Check for required files
    required_files = [
        "sync_distributed_tokens.py",
        "rubix_launcher.py",
        "config_manager.py",
        "system_checker.py"
    ]

    for file in required_files:
        if not (current_dir / file).exists():
            errors.append(f"Required file missing: {file}")

    if errors:
        print("[ERROR] Requirements Check Failed:")
        for error in errors:
            print(f"   • {error}")
        print()
        print("Please ensure all required files are present and Python 3.8+ is installed.")
        sys.exit(1)

def main():
    """Main entry point for Rubix Token Sync"""

    # Set working directory to script directory
    os.chdir(current_dir)

    # Show help if requested
    if should_show_help():
        show_usage()
        return

    # Check basic requirements
    check_basic_requirements()

    # Determine mode and run appropriate function
    if is_interactive_mode():
        print("[START] Starting Rubix Token Sync - Interactive Mode")
        print("Use --help for command-line options")
        print()
        run_interactive_launcher()
    else:
        print("[START] Starting Rubix Token Sync - Direct Mode")
        run_direct_sync()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[EXIT] Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        print("Please check the logs or run with --help for usage information.")
        sys.exit(1)