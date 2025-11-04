#!/usr/bin/env python3
"""
Configuration Manager for Rubix Token Sync
Handles secure credential storage, validation, and configuration management
"""

import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import tempfile
import stat

class ConfigManager:
    """Manages configuration files and credentials for Rubix Token Sync"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize ConfigManager

        Args:
            config_dir: Directory for configuration files (defaults to current directory)
        """
        self.config_dir = config_dir or Path(__file__).parent.absolute()
        self.azure_config_file = self.config_dir / "azure_sql_connection.txt"
        self.telegram_config_file = self.config_dir / "telegram_config.json"

        # Default Telegram configuration
        self.default_telegram_config = {
            "bot_token": "8391226270:AAFv1p1nHf6gcEgXI7diiikczAW-I5Gg1KE",
            "chat_id": "-1003231044644",
            "enabled": True,
            "machine_name": self._get_default_machine_name(),
            "public_ip": "",
            "send_startup": True,
            "send_progress": True,
            "send_errors": True,
            "send_completion": True,
            "progress_interval": 300,
            "max_message_length": 4000
        }

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)

    def _get_default_machine_name(self) -> str:
        """Generate a default machine name based on system info"""
        hostname = platform.node() or "Unknown"
        system = platform.system()
        return f"{hostname}-{system}"

    def _secure_file_permissions(self, file_path: Path):
        """Set secure file permissions (readable only by owner)"""
        try:
            if platform.system() != "Windows":
                # Unix-like systems: Set 600 permissions (rw-------)
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            # If we can't set permissions, continue anyway
            pass

    def validate_azure_config(self, config_content: str) -> Tuple[bool, str]:
        """
        Validate Azure SQL configuration

        Args:
            config_content: Configuration string content

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not config_content or not config_content.strip():
            return False, "Configuration is empty"

        # Check for template placeholder
        if "{your_password}" in config_content:
            return False, "Password placeholder not replaced"

        # Required components for Azure SQL connection
        required_parts = [
            ("SERVER=", "Server information"),
            ("DATABASE=", "Database name"),
            ("UID=", "Username"),
            ("PWD=", "Password")
        ]

        missing_parts = []
        for part, description in required_parts:
            if part not in config_content.upper():
                missing_parts.append(description)

        if missing_parts:
            return False, f"Missing required fields: {', '.join(missing_parts)}"

        return True, "Configuration is valid"

    def validate_telegram_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate Telegram configuration

        Args:
            config: Telegram configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["bot_token", "chat_id", "enabled"]
        missing_fields = []

        for field in required_fields:
            if field not in config:
                missing_fields.append(field)

        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        # Validate bot token format (basic check)
        bot_token = config.get("bot_token", "")
        if not bot_token or ":" not in bot_token:
            return False, "Invalid bot token format"

        # Validate chat ID
        chat_id = config.get("chat_id", "")
        if not chat_id:
            return False, "Chat ID is required"

        return True, "Configuration is valid"

    def save_azure_config(self, server: str, database: str, username: str,
                         password: str, driver: str = "ODBC Driver 17 for SQL Server") -> bool:
        """
        Save Azure SQL configuration

        Args:
            server: SQL Server address
            database: Database name
            username: Username
            password: Password
            driver: ODBC driver name

        Returns:
            True if saved successfully
        """
        try:
            # Build connection string
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

            # Validate before saving
            is_valid, error_msg = self.validate_azure_config(connection_string)
            if not is_valid:
                raise ValueError(f"Invalid configuration: {error_msg}")

            # Write to temporary file first, then move (atomic operation)
            with tempfile.NamedTemporaryFile(mode='w', delete=False,
                                           dir=self.config_dir, suffix='.tmp') as temp_file:
                temp_file.write(connection_string)
                temp_path = Path(temp_file.name)

            # Set secure permissions
            self._secure_file_permissions(temp_path)

            # Atomic move
            temp_path.rename(self.azure_config_file)

            return True

        except Exception as e:
            # Clean up temporary file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            raise e

    def load_azure_config(self) -> Optional[str]:
        """
        Load Azure SQL configuration

        Returns:
            Configuration string or None if not found/invalid
        """
        try:
            if not self.azure_config_file.exists():
                return None

            with open(self.azure_config_file, 'r') as f:
                config_content = f.read().strip()

            is_valid, _ = self.validate_azure_config(config_content)
            if not is_valid:
                return None

            return config_content

        except Exception:
            return None

    def parse_azure_config(self) -> Optional[Dict[str, str]]:
        """
        Parse Azure configuration into components

        Returns:
            Dictionary with parsed components or None
        """
        config_content = self.load_azure_config()
        if not config_content:
            return None

        try:
            parsed = {}
            for part in config_content.split(';'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    key = key.strip().upper()
                    value = value.strip()

                    # Map to friendly names
                    if key == 'SERVER':
                        parsed['server'] = value
                    elif key == 'DATABASE':
                        parsed['database'] = value
                    elif key == 'UID':
                        parsed['username'] = value
                    elif key == 'PWD':
                        parsed['password'] = '********'  # Mask password
                    elif key == 'DRIVER':
                        parsed['driver'] = value.strip('{}')

            return parsed

        except Exception:
            return None

    def save_telegram_config(self, machine_name: Optional[str] = None,
                           enabled: bool = True, custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save Telegram configuration

        Args:
            machine_name: Custom machine name
            enabled: Whether Telegram notifications are enabled
            custom_config: Custom configuration dictionary

        Returns:
            True if saved successfully
        """
        try:
            if custom_config:
                config = custom_config.copy()
            else:
                config = self.default_telegram_config.copy()

            # Override with provided values
            if machine_name:
                config["machine_name"] = machine_name
            config["enabled"] = enabled

            # Validate before saving
            is_valid, error_msg = self.validate_telegram_config(config)
            if not is_valid:
                raise ValueError(f"Invalid configuration: {error_msg}")

            # Write to temporary file first, then move (atomic operation)
            with tempfile.NamedTemporaryFile(mode='w', delete=False,
                                           dir=self.config_dir, suffix='.tmp') as temp_file:
                json.dump(config, temp_file, indent=2)
                temp_path = Path(temp_file.name)

            # Set secure permissions
            self._secure_file_permissions(temp_path)

            # Atomic move
            temp_path.rename(self.telegram_config_file)

            return True

        except Exception as e:
            # Clean up temporary file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            raise e

    def load_telegram_config(self) -> Optional[Dict[str, Any]]:
        """
        Load Telegram configuration

        Returns:
            Configuration dictionary or None if not found/invalid
        """
        try:
            if not self.telegram_config_file.exists():
                return None

            with open(self.telegram_config_file, 'r') as f:
                config = json.load(f)

            is_valid, _ = self.validate_telegram_config(config)
            if not is_valid:
                return None

            return config

        except Exception:
            return None

    def is_azure_configured(self) -> bool:
        """Check if Azure SQL is properly configured"""
        return self.load_azure_config() is not None

    def is_telegram_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return self.load_telegram_config() is not None

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get summary of current configuration status

        Returns:
            Dictionary with configuration status
        """
        summary = {
            "azure_sql": {
                "configured": False,
                "details": None,
                "error": None
            },
            "telegram": {
                "configured": False,
                "details": None,
                "error": None
            }
        }

        # Check Azure SQL
        try:
            azure_config = self.parse_azure_config()
            if azure_config:
                summary["azure_sql"]["configured"] = True
                summary["azure_sql"]["details"] = azure_config
            else:
                summary["azure_sql"]["error"] = "Configuration missing or invalid"
        except Exception as e:
            summary["azure_sql"]["error"] = str(e)

        # Check Telegram
        try:
            telegram_config = self.load_telegram_config()
            if telegram_config:
                summary["telegram"]["configured"] = True
                # Remove sensitive information for summary
                safe_config = telegram_config.copy()
                if "bot_token" in safe_config:
                    safe_config["bot_token"] = safe_config["bot_token"][:20] + "..."
                summary["telegram"]["details"] = safe_config
            else:
                summary["telegram"]["error"] = "Configuration missing or invalid"
        except Exception as e:
            summary["telegram"]["error"] = str(e)

        return summary

    def create_default_configs(self, force: bool = False) -> Dict[str, bool]:
        """
        Create default configuration files

        Args:
            force: Whether to overwrite existing configurations

        Returns:
            Dictionary indicating which configs were created
        """
        results = {
            "telegram": False
        }

        # Create default Telegram config if it doesn't exist or force is True
        if force or not self.is_telegram_configured():
            try:
                self.save_telegram_config()
                results["telegram"] = True
            except Exception:
                pass

        return results

    def backup_configs(self, backup_dir: Optional[Path] = None) -> Dict[str, bool]:
        """
        Create backup of configuration files

        Args:
            backup_dir: Directory for backups (defaults to config_dir/backups)

        Returns:
            Dictionary indicating which configs were backed up
        """
        if backup_dir is None:
            backup_dir = self.config_dir / "backups"

        backup_dir.mkdir(exist_ok=True)

        results = {
            "azure_sql": False,
            "telegram": False
        }

        import shutil
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Backup Azure SQL config
        if self.azure_config_file.exists():
            try:
                backup_file = backup_dir / f"azure_sql_connection_{timestamp}.txt"
                shutil.copy2(self.azure_config_file, backup_file)
                results["azure_sql"] = True
            except Exception:
                pass

        # Backup Telegram config
        if self.telegram_config_file.exists():
            try:
                backup_file = backup_dir / f"telegram_config_{timestamp}.json"
                shutil.copy2(self.telegram_config_file, backup_file)
                results["telegram"] = True
            except Exception:
                pass

        return results

    def export_config_template(self, export_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Export configuration templates for manual setup

        Args:
            export_dir: Directory for templates (defaults to config_dir)

        Returns:
            Dictionary mapping config type to template file path
        """
        if export_dir is None:
            export_dir = self.config_dir

        templates = {}

        # Azure SQL template
        azure_template_content = """# Azure SQL Database Connection String Template
# Replace the placeholders with your actual credentials
#
# IMPORTANT: Replace {your_password} with the actual password
# SECURITY: This file contains sensitive credentials - do not commit to version control

DRIVER={ODBC Driver 17 for SQL Server};SERVER=tcp:rauditser.database.windows.net,1433;DATABASE=rauditd;UID=rubix;PWD={your_password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;

# Connection string breakdown:
# - DRIVER: ODBC driver for SQL Server
# - SERVER: Azure SQL Database server endpoint
# - DATABASE: Database name (rauditd)
# - UID: Database username (rubix)
# - PWD: Database password (REPLACE {your_password})
# - Encrypt=yes: Forces SSL encryption
# - Connection Timeout: 30 seconds timeout for initial connection
"""

        try:
            azure_template_path = export_dir / "azure_sql_connection_template.txt"
            with open(azure_template_path, 'w') as f:
                f.write(azure_template_content)
            templates["azure_sql"] = azure_template_path
        except Exception:
            pass

        # Telegram template
        try:
            telegram_template_path = export_dir / "telegram_config_template.json"
            template_config = self.default_telegram_config.copy()
            template_config["machine_name"] = "{your_machine_name}"

            with open(telegram_template_path, 'w') as f:
                json.dump(template_config, f, indent=2)
            templates["telegram"] = telegram_template_path
        except Exception:
            pass

        return templates

def main():
    """Test the ConfigManager functionality"""
    config_manager = ConfigManager()

    print("🔧 Configuration Manager Test")
    print("=" * 40)

    # Get configuration summary
    summary = config_manager.get_configuration_summary()

    print("Current Configuration Status:")
    for service, info in summary.items():
        status = "✅ Configured" if info["configured"] else "❌ Not configured"
        print(f"  {service.title()}: {status}")

        if info["error"]:
            print(f"    Error: {info['error']}")
        elif info["details"]:
            print(f"    Details: {info['details']}")

    print()

    # Create default configs
    print("Creating default configurations...")
    created = config_manager.create_default_configs()
    for service, was_created in created.items():
        if was_created:
            print(f"  ✅ Created {service} configuration")
        else:
            print(f"  ℹ️  {service} configuration already exists")

    print()
    print("Configuration manager test completed!")

if __name__ == "__main__":
    main()