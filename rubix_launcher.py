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

# Handle path correctly for both bundled and unbundled execution
def is_bundled_executable() -> bool:
    """Check if we're running as a PyInstaller bundled executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

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
        print("=" * 60)
        print("[RUBIX] Rubix Token Sync Tool")
        print("Cross-Platform Distributed Token Synchronization")
        print("=" * 60)
        print()

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
        print(f"{color}[{level}]{reset} {message}")

    def check_azure_sql_config(self) -> bool:
        """Check if Azure SQL configuration exists and is valid"""
        if not self.azure_config_file.exists():
            return False

        try:
            with open(self.azure_config_file, 'r') as f:
                config_content = f.read().strip()

            # Check if it's still using template placeholder
            if "{your_password}" in config_content:
                return False

            # Basic validation - should contain required components
            required_parts = ["Server=", "Database=", "UID=", "PWD="]
            return all(part in config_content for part in required_parts)

        except Exception:
            return False

    def check_telegram_config(self) -> bool:
        """Check if Telegram configuration exists and is valid"""
        if not self.telegram_config_file.exists():
            return False

        try:
            with open(self.telegram_config_file, 'r') as f:
                config = json.load(f)

            # Check if required fields exist
            required_fields = ["bot_token", "chat_id", "enabled"]
            return all(field in config for field in required_fields)

        except Exception:
            return False

    def test_azure_sql_connection(self) -> bool:
        """Test Azure SQL Database connection"""
        if not self.check_azure_sql_config():
            return False

        try:
            # Import and test connection
            from sync_distributed_tokens import get_azure_sql_connection_string, init_connection_pool

            conn_string = get_azure_sql_connection_string()
            if "{your_password}" in conn_string:
                return False

            pool = init_connection_pool()
            conn = pool.get_connection()
            conn.close()
            return True

        except Exception as e:
            self.print_status(f"Azure SQL connection failed: {e}", "ERROR")
            return False

    def test_telegram_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.check_telegram_config():
            return False

        try:
            # Import and test Telegram
            from telegram_notifier import init_telegram_notifier

            notifier = init_telegram_notifier()
            if notifier and notifier.config.enabled:
                return notifier.test_connection()
            return False

        except Exception as e:
            self.print_status(f"Telegram connection failed: {e}", "ERROR")
            return False

    def show_system_info(self):
        """Display system information"""
        self.clear_screen()
        self.print_header()

        print("[SYSTEM] System Information:")
        print(f"   [HOST]  Hostname: {platform.node()}")
        print(f"   [INFO]  System: {platform.system()} {platform.release()}")
        print(f"   [ARCH]  Architecture: {platform.machine()}")
        print(f"   🐍 Python Version: {sys.version.split()[0]}")
        print(f"   [DIR] Working Directory: {current_dir}")

        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(current_dir)
            free_gb = free // (1024**3)
            print(f"   [DISK] Available Disk Space: {free_gb} GB")
        except:
            print(f"   [DISK] Available Disk Space: Unable to detect")

        # Check memory
        try:
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if 'MemAvailable:' in line:
                            mem_kb = int(line.split()[1])
                            mem_gb = mem_kb // (1024**2)
                            print(f"   🧠 Available Memory: {mem_gb} GB")
                            break
            else:
                print(f"   🧠 Available Memory: System dependent")
        except:
            print(f"   🧠 Available Memory: Unable to detect")

        print(f"   🕐 Current Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Show configuration status
        print("[CONFIG]  Configuration Status:")
        azure_status = "[OK] Configured" if self.check_azure_sql_config() else "[ERROR] Not configured"
        telegram_status = "[OK] Configured" if self.check_telegram_config() else "[ERROR] Not configured"
        print(f"   [DB]  Azure SQL Database: {azure_status}")
        print(f"   [TELEGRAM] Telegram Notifications: {telegram_status}")
        print()

        input("Press Enter to continue...")

    def setup_azure_sql_credentials(self):
        """Interactive setup for Azure SQL credentials"""
        self.clear_screen()
        self.print_header()

        print("[SETUP] Azure SQL Database Configuration")
        print("-" * 40)
        print()

        # Check if config already exists
        if self.check_azure_sql_config():
            print("[WARNING]  Existing Azure SQL configuration found.")

            # Show current configuration (masked)
            try:
                with open(self.azure_config_file, 'r') as f:
                    config_content = f.read().strip()

                # Extract server and database for display
                server = "Unknown"
                database = "Unknown"
                user = "Unknown"

                for part in config_content.split(';'):
                    if part.startswith('SERVER='):
                        server = part.split('=', 1)[1]
                    elif part.startswith('DATABASE='):
                        database = part.split('=', 1)[1]
                    elif part.startswith('UID='):
                        user = part.split('=', 1)[1]

                print(f"Current settings:")
                print(f"   Server: {server}")
                print(f"   Database: {database}")
                print(f"   Username: {user}")
                print(f"   Password: ********")
                print()

                choice = input("Keep existing configuration? (y/n) [y]: ").strip().lower()
                if choice in ['', 'y', 'yes']:
                    self.print_status("Keeping existing configuration", "SUCCESS")
                    time.sleep(1)
                    return

            except Exception:
                pass

        # Get new configuration
        print("Enter Azure SQL Database details:")
        print()

        # Default values
        default_server = "rauditser.database.windows.net,1433"
        default_database = "rauditd"
        default_user = "rubix"

        server = input(f"Server [{default_server}]: ").strip() or default_server
        database = input(f"Database [{default_database}]: ").strip() or default_database
        user = input(f"Username [{default_user}]: ").strip() or default_user

        # Get password securely
        while True:
            password = getpass.getpass("Password: ").strip()
            if password:
                confirm_password = getpass.getpass("Confirm password: ").strip()
                if password == confirm_password:
                    break
                else:
                    self.print_status("Passwords don't match. Please try again.", "ERROR")
            else:
                self.print_status("Password cannot be empty.", "ERROR")

        # Build connection string
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

        # Test connection
        print()
        self.print_status("Testing database connection...", "INFO")

        # Save temporarily to test
        try:
            with open(self.azure_config_file, 'w') as f:
                f.write(connection_string)

            if self.test_azure_sql_connection():
                self.print_status("[OK] Database connection successful!", "SUCCESS")
                print()
                input("Press Enter to continue...")
            else:
                self.print_status("[ERROR] Database connection failed!", "ERROR")
                print("Please check your credentials and try again.")
                input("Press Enter to continue...")

        except Exception as e:
            self.print_status(f"Error saving configuration: {e}", "ERROR")
            input("Press Enter to continue...")

    def setup_telegram_config(self):
        """Setup Telegram configuration (pre-configured)"""
        self.clear_screen()
        self.print_header()

        print("[TELEGRAM] Telegram Configuration")
        print("-" * 40)
        print()

        if self.check_telegram_config():
            print("[OK] Telegram is already configured.")

            try:
                with open(self.telegram_config_file, 'r') as f:
                    config = json.load(f)

                print(f"Current settings:")
                print(f"   Machine Name: {config.get('machine_name', 'Unknown')}")
                print(f"   Notifications: {'Enabled' if config.get('enabled', False) else 'Disabled'}")
                print(f"   Bot Token: {config.get('bot_token', 'Unknown')[:20]}...")
                print(f"   Chat ID: {config.get('chat_id', 'Unknown')}")
                print()

                choice = input("Keep existing configuration? (y/n) [y]: ").strip().lower()
                if choice in ['', 'y', 'yes']:
                    self.print_status("Keeping existing configuration", "SUCCESS")
                    time.sleep(1)
                    return

            except Exception:
                pass

        # Setup new configuration
        print("Setting up Telegram notifications...")
        print("[TELEGRAM] Bot Token and Chat ID are pre-configured.")
        print()

        # Get machine name
        default_machine_name = self.get_machine_name()
        machine_name = input(f"Machine Name [{default_machine_name}]: ").strip() or default_machine_name

        # Create configuration
        config = self.default_telegram_config.copy()
        config["machine_name"] = machine_name

        # Save configuration
        try:
            with open(self.telegram_config_file, 'w') as f:
                json.dump(config, f, indent=2)

            self.print_status("[OK] Telegram configuration saved!", "SUCCESS")

            # Test connection
            print()
            self.print_status("Testing Telegram connection...", "INFO")

            if self.test_telegram_connection():
                self.print_status("[OK] Telegram connection successful!", "SUCCESS")
            else:
                self.print_status("[WARNING]  Telegram connection test failed", "WARNING")
                print("Configuration saved but connection could not be verified.")

            print()
            input("Press Enter to continue...")

        except Exception as e:
            self.print_status(f"Error saving Telegram configuration: {e}", "ERROR")
            input("Press Enter to continue...")

    def test_connections(self):
        """Test all connections"""
        self.clear_screen()
        self.print_header()

        print("🧪 Connection Tests")
        print("-" * 40)
        print()

        # Test Azure SQL
        self.print_status("Testing Azure SQL Database connection...", "INFO")
        if self.test_azure_sql_connection():
            self.print_status("[OK] Azure SQL Database: Connected", "SUCCESS")
        else:
            self.print_status("[ERROR] Azure SQL Database: Failed", "ERROR")

        print()

        # Test Telegram
        self.print_status("Testing Telegram connection...", "INFO")
        if self.test_telegram_connection():
            self.print_status("[OK] Telegram: Connected", "SUCCESS")
        else:
            self.print_status("[ERROR] Telegram: Failed", "ERROR")

        print()
        input("Press Enter to continue...")

    def show_configuration_status(self):
        """Show current configuration status"""
        azure_configured = self.check_azure_sql_config()
        telegram_configured = self.check_telegram_config()

        print("Current Configuration:")
        if azure_configured:
            print("[OK] MSSQL: Configured")
            if self.test_azure_sql_connection():
                print("   🔗 Connection: Working")
            else:
                print("   [WARNING]  Connection: Failed")
        else:
            print("[ERROR] MSSQL: Not configured")

        if telegram_configured:
            print("[OK] Telegram: Configured")
            if self.test_telegram_connection():
                print("   🔗 Connection: Working")
            else:
                print("   [WARNING]  Connection: Failed")
        else:
            print("[ERROR] Telegram: Not configured")

        print()
        return azure_configured and telegram_configured

    def run_sync(self, sync_type: str = "standard"):
        """Run the sync process"""
        self.clear_screen()
        self.print_header()

        print(f"[RUBIX] Running {sync_type.title()} Sync")
        print("-" * 40)
        print()

        # Check prerequisites
        if not self.check_azure_sql_config():
            self.print_status("[ERROR] Azure SQL Database not configured!", "ERROR")
            print("Please configure database credentials first.")
            input("Press Enter to continue...")
            return

        # Ensure Telegram is configured
        if not self.check_telegram_config():
            self.print_status("Setting up Telegram configuration...", "INFO")
            try:
                with open(self.telegram_config_file, 'w') as f:
                    json.dump(self.default_telegram_config, f, indent=2)
                self.print_status("[OK] Telegram configured with default settings", "SUCCESS")
            except Exception as e:
                self.print_status(f"Warning: Could not setup Telegram: {e}", "WARNING")

        # Build sync command
        sync_cmd = [sys.executable, "sync_distributed_tokens.py"]

        if sync_type == "full":
            sync_cmd.extend(["--clear", "--force-ipfs"])
        elif sync_type == "cleanup":
            sync_cmd.append("--cleanup-locks")
        elif sync_type == "essential":
            sync_cmd.append("--essential-only")

        self.print_status(f"Executing: {' '.join(sync_cmd)}", "INFO")
        print()

        # Run the sync
        try:
            result = subprocess.run(sync_cmd, cwd=current_dir)

            if result.returncode == 0:
                self.print_status("[OK] Sync completed successfully!", "SUCCESS")
            else:
                self.print_status(f"[ERROR] Sync failed with exit code {result.returncode}", "ERROR")

        except Exception as e:
            self.print_status(f"[ERROR] Error running sync: {e}", "ERROR")

        print()
        input("Press Enter to continue...")

    def show_main_menu(self):
        """Display main menu and handle user selection"""
        while True:
            self.clear_screen()
            self.print_header()

            # Show configuration status
            all_configured = self.show_configuration_status()

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

            if not all_configured:
                self.print_status("[WARNING]  Some configurations are missing. Please setup credentials first.", "WARNING")
                print()

            try:
                choice = input("Enter choice [1-9]: ").strip()

                if choice == "1":
                    self.run_sync("standard")
                elif choice == "2":
                    print()
                    confirm = input("[WARNING]  This will delete ALL existing records. Type 'YES' to confirm: ").strip()
                    if confirm == "YES":
                        self.run_sync("full")
                    else:
                        self.print_status("Full sync cancelled.", "INFO")
                        time.sleep(1)
                elif choice == "3":
                    self.test_connections()
                elif choice == "4":
                    self.setup_azure_sql_credentials()
                elif choice == "5":
                    self.setup_telegram_config()
                elif choice == "6":
                    self.run_sync("cleanup")
                elif choice == "7":
                    self.run_sync("essential")
                elif choice == "8":
                    self.show_system_info()
                elif choice == "9":
                    self.print_status("Goodbye! 👋", "SUCCESS")
                    break
                else:
                    self.print_status("Invalid choice. Please try again.", "ERROR")
                    time.sleep(1)

            except KeyboardInterrupt:
                print("\n")
                self.print_status("Goodbye! 👋", "SUCCESS")
                break
            except Exception as e:
                self.print_status(f"Error: {e}", "ERROR")
                time.sleep(2)

def main():
    """Main entry point"""
    launcher = RubixLauncher()

    # Handle command line arguments for backward compatibility
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--clear":
            launcher.run_sync("full")
        elif arg == "--cleanup-locks":
            launcher.run_sync("cleanup")
        elif arg == "--essential-only":
            launcher.run_sync("essential")
        elif arg == "--test-only":
            launcher.test_connections()
        elif arg == "--help":
            print("Rubix Token Sync Tool")
            print("Usage: rubix_launcher.py [option]")
            print("Options:")
            print("  --clear          Full sync (clear all + resync)")
            print("  --cleanup-locks  Cleanup IPFS lock errors")
            print("  --essential-only Essential metadata only")
            print("  --test-only      Test connections only")
            print("  --help           Show this help")
            print("  (no args)        Interactive menu")
        else:
            launcher.run_sync("standard")
    else:
        # Interactive mode
        launcher.show_main_menu()

if __name__ == "__main__":
    main()