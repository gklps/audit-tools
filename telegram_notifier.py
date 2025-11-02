#!/usr/bin/env python3
"""
Telegram Notification System for Rubix Token Sync

Provides real-time status updates via Telegram bot with machine identification
using public IP addresses for multi-VM monitoring.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests
from dataclasses import dataclass
import threading
import queue

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    bot_token: str
    chat_id: str
    enabled: bool = True
    machine_name: str = ""
    public_ip: str = ""
    send_startup: bool = True
    send_progress: bool = True
    send_errors: bool = True
    send_completion: bool = True
    progress_interval: int = 300  # Send progress updates every 5 minutes
    max_message_length: int = 4000  # Telegram message limit

class TelegramNotifier:
    """Thread-safe Telegram notification system"""

    def __init__(self, config_file: str = "telegram_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.bot = None
        self.message_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.last_progress_time = 0
        self.machine_id = self._generate_machine_id()

        if TELEGRAM_AVAILABLE and self.config.enabled and self.config.bot_token:
            self._initialize_bot()

    def _load_config(self) -> TelegramConfig:
        """Load Telegram configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return TelegramConfig(**data)
            except Exception as e:
                print(f"Error loading Telegram config: {e}")

        # Return default config
        return TelegramConfig(
            bot_token="",
            chat_id="",
            enabled=False
        )

    def _save_config(self):
        """Save current configuration to file"""
        try:
            config_dict = {
                'bot_token': self.config.bot_token,
                'chat_id': self.config.chat_id,
                'enabled': self.config.enabled,
                'machine_name': self.config.machine_name,
                'public_ip': self.config.public_ip,
                'send_startup': self.config.send_startup,
                'send_progress': self.config.send_progress,
                'send_errors': self.config.send_errors,
                'send_completion': self.config.send_completion,
                'progress_interval': self.config.progress_interval,
                'max_message_length': self.config.max_message_length
            }

            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            print(f"Error saving Telegram config: {e}")

    def _generate_machine_id(self) -> str:
        """Generate a unique machine identifier"""
        if self.config.machine_name:
            return f"{self.config.machine_name} ({self.config.public_ip})"
        elif self.config.public_ip:
            return f"VM-{self.config.public_ip}"
        else:
            # Fallback to hostname
            import socket
            hostname = socket.gethostname()
            return f"{hostname} (IP: Unknown)"

    def _initialize_bot(self):
        """Initialize Telegram bot"""
        try:
            self.bot = Bot(token=self.config.bot_token)
            self.is_running = True

            # Start worker thread for async message sending
            self.worker_thread = threading.Thread(target=self._message_worker, daemon=True)
            self.worker_thread.start()

            print(f"Telegram notifier initialized for machine: {self.machine_id}")
        except Exception as e:
            print(f"Failed to initialize Telegram bot: {e}")
            self.config.enabled = False

    def _message_worker(self):
        """Background worker thread to send messages"""
        while self.is_running:
            try:
                # Wait for message with timeout
                message = self.message_queue.get(timeout=1.0)
                if message is None:  # Shutdown signal
                    break

                self._send_message_sync(message)
                self.message_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in Telegram message worker: {e}")

    def _send_message_sync(self, message: str):
        """Synchronously send message to Telegram"""
        if not self.bot or not self.config.enabled:
            return

        try:
            # Split long messages
            if len(message) > self.config.max_message_length:
                parts = self._split_message(message)
                for part in parts:
                    self.bot.send_message(
                        chat_id=self.config.chat_id,
                        text=part,
                        parse_mode='Markdown'
                    )
                    time.sleep(0.5)  # Avoid rate limiting
            else:
                self.bot.send_message(
                    chat_id=self.config.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
        except TelegramError as e:
            print(f"Telegram send error: {e}")
        except Exception as e:
            print(f"Unexpected error sending Telegram message: {e}")

    def _split_message(self, message: str) -> List[str]:
        """Split long message into smaller parts"""
        parts = []
        current_part = ""

        for line in message.split('\n'):
            if len(current_part) + len(line) + 1 > self.config.max_message_length:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line
            else:
                if current_part:
                    current_part += '\n' + line
                else:
                    current_part = line

        if current_part:
            parts.append(current_part.strip())

        return parts

    def send_message(self, message: str):
        """Queue message for sending"""
        if not self.config.enabled or not self.bot:
            return

        # Add machine identifier to message
        formatted_message = f"🖥️ **{self.machine_id}**\n{message}"

        try:
            self.message_queue.put(formatted_message, block=False)
        except queue.Full:
            print("Telegram message queue is full, dropping message")

    def send_startup_notification(self, sync_type: str = "Distributed Token Sync"):
        """Send sync startup notification"""
        if not self.config.send_startup:
            return

        message = f"""
🚀 **SYNC STARTED**
```
Type: {sync_type}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Status: Initializing...
```
"""
        self.send_message(message)

    def send_progress_notification(self, progress_data: Dict[str, Any]):
        """Send progress update notification with rate limiting"""
        if not self.config.send_progress:
            return

        current_time = time.time()
        if current_time - self.last_progress_time < self.config.progress_interval:
            return  # Skip if too soon

        self.last_progress_time = current_time

        # Format progress data
        progress_pct = progress_data.get('progress_percentage', 0)
        records = progress_data.get('records_processed', 0)
        rate = progress_data.get('processing_rate', 0)
        ipfs_success = progress_data.get('ipfs_success', 0)
        sql_errors = progress_data.get('sql_errors', 0)
        elapsed = progress_data.get('elapsed_time', 0)

        # Create progress bar
        progress_bar = self._create_progress_bar(progress_pct)

        message = f"""
📊 **SYNC PROGRESS**
```
{progress_bar} {progress_pct:.1f}%

Records: {records:,}
Rate: {rate:.1f}/sec
IPFS Success: {ipfs_success:,}
SQL Errors: {sql_errors:,}
Elapsed: {elapsed/60:.1f} min
```
"""
        self.send_message(message)

    def send_error_notification(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Send error notification"""
        if not self.config.send_errors:
            return

        # Truncate long error messages
        if len(error_message) > 500:
            error_message = error_message[:500] + "..."

        message = f"""
❌ **ERROR DETECTED**
```
Type: {error_type}
Time: {datetime.now().strftime('%H:%M:%S')}
Message: {error_message}
```
"""

        if context:
            context_str = ""
            for key, value in context.items():
                if len(context_str) > 300:  # Limit context size
                    context_str += "..."
                    break
                context_str += f"{key}: {value}\n"

            if context_str:
                message += f"```\nContext:\n{context_str}```"

        self.send_message(message)

    def send_completion_notification(self, final_metrics: Dict[str, Any]):
        """Send sync completion notification"""
        if not self.config.send_completion:
            return

        duration = final_metrics.get('duration_seconds', 0)
        records = final_metrics.get('total_records_processed', 0)
        rate = final_metrics.get('records_per_second', 0)
        ipfs_rate = final_metrics.get('ipfs_success_rate', 0)
        sql_rate = final_metrics.get('sql_success_rate', 0)
        databases = final_metrics.get('total_databases_processed', 0)
        errors = final_metrics.get('total_errors', 0)

        status_emoji = "✅" if errors == 0 else "⚠️"

        message = f"""
{status_emoji} **SYNC COMPLETED**
```
Duration: {duration/60:.1f} minutes
Databases: {databases:,}
Records: {records:,}
Avg Rate: {rate:.1f}/sec

Success Rates:
├─ IPFS: {ipfs_rate:.1f}%
└─ SQL: {sql_rate:.1f}%

Errors: {errors:,}
```
"""
        self.send_message(message)

    def send_database_completed(self, db_name: str, db_metrics: Dict[str, Any]):
        """Send notification when a database is completed"""
        records = db_metrics.get('records_processed', 0)
        duration = db_metrics.get('processing_duration', 0)
        ipfs_success_rate = db_metrics.get('ipfs_success_rate', 0)

        # Only send for significant databases (>1000 records) to avoid spam
        if records < 1000:
            return

        message = f"""
📁 **DATABASE COMPLETED**
```
Name: {db_name}
Records: {records:,}
Duration: {duration:.1f}s
IPFS Rate: {ipfs_success_rate:.1f}%
```
"""
        self.send_message(message)

    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a text-based progress bar"""
        filled = int(width * percentage / 100)
        empty = width - filled
        return '█' * filled + '░' * empty

    def update_machine_info(self, public_ip: str, machine_name: str = ""):
        """Update machine identification information"""
        self.config.public_ip = public_ip
        if machine_name:
            self.config.machine_name = machine_name

        self.machine_id = self._generate_machine_id()
        self._save_config()

    def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        if not self.bot or not self.config.enabled:
            return False

        try:
            self.bot.get_me()
            return True
        except Exception as e:
            print(f"Telegram connection test failed: {e}")
            return False

    def shutdown(self):
        """Shutdown the notifier"""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            # Signal shutdown
            self.message_queue.put(None)
            self.worker_thread.join(timeout=5.0)

# Global notifier instance
telegram_notifier = None

def init_telegram_notifier(bot_token: str = "", chat_id: str = "",
                          machine_name: str = "", enabled: bool = True) -> TelegramNotifier:
    """Initialize global Telegram notifier"""
    global telegram_notifier

    if not TELEGRAM_AVAILABLE:
        print("Telegram notifications not available - python-telegram-bot not installed")
        return None

    # Load existing config or create new one
    config_file = "telegram_config.json"

    if bot_token and chat_id:
        # Create/update config
        config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            enabled=enabled,
            machine_name=machine_name
        )

        # Save config
        with open(config_file, 'w') as f:
            json.dump({
                'bot_token': bot_token,
                'chat_id': chat_id,
                'enabled': enabled,
                'machine_name': machine_name,
                'send_startup': True,
                'send_progress': True,
                'send_errors': True,
                'send_completion': True,
                'progress_interval': 300,
                'max_message_length': 4000
            }, f, indent=2)

    telegram_notifier = TelegramNotifier(config_file)
    return telegram_notifier

def get_telegram_notifier() -> Optional[TelegramNotifier]:
    """Get the global Telegram notifier instance"""
    return telegram_notifier

# Convenience functions for easy integration
def notify_startup(sync_type: str = "Distributed Token Sync"):
    """Send startup notification"""
    if telegram_notifier:
        telegram_notifier.send_startup_notification(sync_type)

def notify_progress(progress_data: Dict[str, Any]):
    """Send progress notification"""
    if telegram_notifier:
        telegram_notifier.send_progress_notification(progress_data)

def notify_error(error_type: str, error_message: str, context: Dict[str, Any] = None):
    """Send error notification"""
    if telegram_notifier:
        telegram_notifier.send_error_notification(error_type, error_message, context)

def notify_completion(final_metrics: Dict[str, Any]):
    """Send completion notification"""
    if telegram_notifier:
        telegram_notifier.send_completion_notification(final_metrics)

def notify_database_completed(db_name: str, db_metrics: Dict[str, Any]):
    """Send database completion notification"""
    if telegram_notifier:
        telegram_notifier.send_database_completed(db_name, db_metrics)

def update_machine_info(public_ip: str, machine_name: str = ""):
    """Update machine information"""
    if telegram_notifier:
        telegram_notifier.update_machine_info(public_ip, machine_name)

def shutdown_telegram():
    """Shutdown Telegram notifications"""
    if telegram_notifier:
        telegram_notifier.shutdown()