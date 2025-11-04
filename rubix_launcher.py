#!/usr/bin/env python3
"""
Rubix Token Sync - Interactive Launcher
Cross-platform executable launcher with interactive setup and menu system
"""

import os
import sys
import json
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any
import getpass

def is_bundled_executable() -> bool:
    """Check if we're running as a PyInstaller bundled executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Handle path correctly for both bundled and unbundled execution
if is_bundled_executable():
    # When bundled, config files should be in current working directory
    current_dir = Path.cwd()
else:
    # When running as script, use file location
    current_dir = Path(__file__).parent.absolute()
    sys.path.insert(0, str(current_dir))

class RubixLauncher:
    """Interactive launcher for Rubix Token Sync"""

    def __init__(self):
        self.config_dir = current_dir
        self.azure_config_file = self.config_dir / "azure_sql_connection.txt"
        self.telegram_config_file = self.config_dir / "telegram_config.json"
        self.logs_dir = self.config_dir / "logs"

        # Pre-configured Telegram credentials (provided by user)
        self.default_telegram_config = {
            "bot_token": "8391226270:AAFv1p1nHf6gcEgXI7diiikczAW-I5Gg1KE",
            "chat_id": "-1003231044644",
            "enabled": True,
            "machine_name": self.get_machine_name(),
            "public_ip": "",
            "send_startup": True,
            "send_progress": True,
            "send_errors": True,
            "send_completion": True,
            "progress_interval": 300,
            "max_message_length": 4000
        }

        # Ensure logs directory exists
        self.logs_dir.mkdir(exist_ok=True)

    def get_machine_name(self) -> str:
        """Generate a default machine name"""
        hostname = platform.node() or "Unknown"
        system = platform.system()
        return f"{hostname}-{system}"

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """Print application header"""
        print("[RUBIX] Rubix Token Sync Tool")
        print("=" * 50)
        print()

    def show_system_info(self):
        """Display system information"""
        self.clear_screen()
        self.print_header()

        print("[SYSTEM] System Information:")
        print(f"   [HOST] Hostname: {platform.node()}")
        print(f"   [INFO] System: {platform.system()} {platform.release()}")
        print(f"   [ARCH] Architecture: {platform.machine()}")
        print(f"   Python Version: {sys.version}")
        print(f"   [DIR] Working Directory: {current_dir}")

        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(current_dir)
            free_gb = free // (1024**3)
            print(f"   [DISK] Available Disk Space: {free_gb} GB")
        except:
            print(f"   [DISK] Available Disk Space: Unable to detect")

        print()

        # Check configuration status
        self.show_configuration_status()

        print()
        input("Press Enter to continue...")

    def show_configuration_status(self) -> bool:
        """Show current configuration status and return True if all configured"""
        print("[CONFIG] Configuration Status:")
        azure_status = "[OK] Configured" if self.check_azure_sql_config() else "[ERROR] Not configured"
        telegram_status = "[OK] Configured" if self.check_telegram_config() else "[ERROR] Not configured"

        print(f"   [DB] Azure SQL Database: {azure_status}")
        print(f"   [TELEGRAM] Telegram Notifications: {telegram_status}")

        return self.check_azure_sql_config() and self.check_telegram_config()

    def setup_azure_sql(self):
        """Setup Azure SQL Database configuration"""
        self.clear_screen()
        self.print_header()

        print("[SETUP] Azure SQL Database Configuration")
        print("-" * 40)
        print()

        if self.azure_config_file.exists():
            print("[WARNING] Existing Azure SQL configuration found.")
            choice = input("Do you want to overwrite it? (y/N): ").strip().lower()
            if choice != 'y':
                return

        print("Please provide your Azure SQL Database details:")
        print()

        # Get database connection details
        server = input("Server (e.g., myserver.database.windows.net): ").strip()
        if not server:
            print("[ERROR] Server is required!")
            input("Press Enter to continue...")
            return

        database = input("Database name: ").strip()
        if not database:
            print("[ERROR] Database name is required!")
            input("Press Enter to continue...")
            return

        username = input("Username: ").strip()
        if not username:
            print("[ERROR] Username is required!")
            input("Press Enter to continue...")
            return

        password = getpass.getpass("Password: ")
        if not password:
            print("[ERROR] Password is required!")
            input("Press Enter to continue...")
            return

        # Choose driver
        print("\nAvailable ODBC drivers:")
        print("1. ODBC Driver 17 for SQL Server (recommended)")
        print("2. ODBC Driver 18 for SQL Server")
        print("3. SQL Server Native Client 11.0")

        driver_choice = input("Choose driver (1-3) [1]: ").strip() or "1"

        drivers = {
            "1": "ODBC Driver 17 for SQL Server",
            "2": "ODBC Driver 18 for SQL Server",
            "3": "SQL Server Native Client 11.0"
        }

        driver = drivers.get(driver_choice, drivers["1"])

        # Create connection string
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

        # Save configuration
        try:
            with open(self.azure_config_file, 'w') as f:
                f.write(connection_string)

            print(f"\n[OK] Azure SQL configuration saved to {self.azure_config_file}")

            # Test connection
            print("\nTesting connection...")
            if self.test_azure_connection():
                print("[OK] Connection test successful!")
            else:
                print("[ERROR] Connection test failed. Please check your credentials.")

        except Exception as e:
            print(f"[ERROR] Failed to save configuration: {e}")

        print()
        input("Press Enter to continue...")

    def setup_telegram(self):
        """Setup Telegram configuration"""
        self.clear_screen()
        self.print_header()

        print("[TELEGRAM] Telegram Configuration")
        print("-" * 40)
        print()

        if self.telegram_config_file.exists():
            print("[WARNING] Existing Telegram configuration found.")
            choice = input("Do you want to overwrite it? (y/N): ").strip().lower()
            if choice != 'y':
                return

        print("Telegram bot is pre-configured with audit bot credentials.")
        print("You can customize the machine name and notification preferences.")
        print()

        # Get machine name
        default_name = self.get_machine_name()
        machine_name = input(f"Machine name [{default_name}]: ").strip() or default_name

        # Get notification preferences
        print("\nNotification preferences:")
        send_startup = input("Send startup notifications? (Y/n): ").strip().lower() != 'n'
        send_progress = input("Send progress updates? (Y/n): ").strip().lower() != 'n'
        send_errors = input("Send error notifications? (Y/n): ").strip().lower() != 'n'
        send_completion = input("Send completion notifications? (Y/n): ").strip().lower() != 'n'

        if send_progress:
            try:
                interval = int(input("Progress update interval in seconds [300]: ").strip() or "300")
            except ValueError:
                interval = 300
        else:
            interval = 300

        # Create configuration
        config = self.default_telegram_config.copy()
        config.update({
            "machine_name": machine_name,
            "send_startup": send_startup,
            "send_progress": send_progress,
            "send_errors": send_errors,
            "send_completion": send_completion,
            "progress_interval": interval
        })

        # Save configuration
        try:
            with open(self.telegram_config_file, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"\n[OK] Telegram configuration saved to {self.telegram_config_file}")

        except Exception as e:
            print(f"[ERROR] Failed to save configuration: {e}")

        print()
        input("Press Enter to continue...")

    def check_azure_sql_config(self) -> bool:
        """Check if Azure SQL is configured"""
        return self.azure_config_file.exists()

    def check_telegram_config(self) -> bool:
        """Check if Telegram is configured"""
        return self.telegram_config_file.exists()

    def test_azure_connection(self) -> bool:
        """Test Azure SQL connection"""
        if not self.azure_config_file.exists():
            return False

        try:
            import pyodbc
            with open(self.azure_config_file, 'r') as f:
                connection_string = f.read().strip()

            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            return True

        except Exception:
            return False

    def run_sync(self, sync_type: str):
        """Run synchronization with specified type"""
        self.clear_screen()
        self.print_header()

        print(f"Starting {sync_type}...")
        print("-" * 40)
        print()

        # Check configuration
        if not self.check_azure_sql_config():
            print("[ERROR] Azure SQL Database not configured!")
            print("Please configure database settings first.")
            input("Press Enter to continue...")
            return

        try:
            # Import and run sync
            from sync_distributed_tokens import main as sync_main

            # Set command line arguments based on sync type
            original_argv = sys.argv[:]

            if sync_type == "Standard Sync":
                sys.argv = ["rubix_sync"]
            elif sync_type == "Full Sync":
                sys.argv = ["rubix_sync", "--clear", "--force-ipfs"]
            elif sync_type == "Test Connections":
                sys.argv = ["rubix_sync", "--test-only"]
            elif sync_type == "Cleanup IPFS Locks":
                sys.argv = ["rubix_sync", "--cleanup-locks"]
            elif sync_type == "Essential Metadata":
                sys.argv = ["rubix_sync", "--essential-only"]

            # Run sync
            sync_main()

            # Restore original argv
            sys.argv = original_argv

            print()
            print("[OK] Sync completed successfully!")

        except Exception as e:
            print(f"[ERROR] Sync failed: {e}")

        print()
        input("Press Enter to continue...")

    def show_main_menu(self):
        """Display main menu and handle user selection"""
        while True:
            self.clear_screen()
            self.print_header()

            all_configured = self.show_configuration_status()

            print()
            print("Choose an option:")
            print("1. Run Standard Sync (incremental)")
            print("2. Run Full Sync (clear all + resync)")
            print("3. Test Connections Only")
            print("4. Setup MSSQL Credentials")
            print("5. Setup Telegram Configuration")
            print("6. Cleanup IPFS Lock Errors")
            print("7. Essential Metadata Only (fast)")
            print("8. View System Information")
            print("9. Exit")
            print()

            choice = input("Enter choice [1-9]: ").strip()

            if choice == "1":
                self.run_sync("Standard Sync")
            elif choice == "2":
                self.run_sync("Full Sync")
            elif choice == "3":
                self.run_sync("Test Connections")
            elif choice == "4":
                self.setup_azure_sql()
            elif choice == "5":
                self.setup_telegram()
            elif choice == "6":
                self.run_sync("Cleanup IPFS Locks")
            elif choice == "7":
                self.run_sync("Essential Metadata")
            elif choice == "8":
                self.show_system_info()
            elif choice == "9":
                print("\n[EXIT] Goodbye!")
                break
            else:
                print("\n[ERROR] Invalid choice. Please try again.")
                time.sleep(1)

if __name__ == "__main__":
    try:
        launcher = RubixLauncher()
        launcher.show_main_menu()
    except KeyboardInterrupt:
        print("\n[EXIT] Goodbye!")
    except Exception as e:
        print(f"\n[ERROR] Launcher failed: {e}")
        sys.exit(1)