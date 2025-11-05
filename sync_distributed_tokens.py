#!/usr/bin/env python3
"""
Distributed Token Sync Service with IPFS Integration

Scans directories for Rubix/rubix.db files, reads TokensTable data,
fetches IPFS metadata via ipfs cat, and syncs everything to Azure SQL Database.
"""

import os
import sqlite3
import subprocess
import logging
import sys
import time
import requests
import json
import pyodbc
import argparse
# import pandas as pd  # Removed - not used in the script
from typing import List, Optional, Tuple, Dict, Any
from multiprocessing import Pool, cpu_count
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Import Telegram notifications
try:
    from telegram_notifier import (
        init_telegram_notifier, notify_startup, notify_progress,
        notify_error, notify_completion, notify_database_completed,
        update_machine_info, shutdown_telegram
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Telegram notifications not available - telegram_notifier module not found")

# Configuration
AZURE_SQL_CONNECTION_STRING = "Server=tcp:rauditser.database.windows.net,1433;Initial Catalog=rauditd;Persist Security Info=False;User ID=rubix;Password={your_password};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
CONNECTION_CONFIG_FILE = 'azure_sql_connection.txt'
# Smart IPFS binary detection
def find_ipfs_binary() -> str:
    """Universal IPFS binary detection for any VM setup"""

    search_paths = []

    # Dynamic directory detection based on executable location
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Bundled executable - search from executable's directory
        current_dir = Path(sys.executable).parent
    else:
        # Python script - use current working directory
        current_dir = Path.cwd()

    # 1. Search current directory tree (up to 5 levels up)
    for i in range(6):
        check_dir = current_dir if i == 0 else current_dir.parents[i-1]
        if check_dir == check_dir.parent:  # Reached root
            break

        # Check for ipfs binary in this directory
        ipfs_path = check_dir / 'ipfs'
        if ipfs_path.exists() and ipfs_path.is_file():
            search_paths.append(str(ipfs_path))

    # 2. Search common sibling directories from current path
    # If we're in /some/path/audit-tools, check /some/path/ipfs
    for i in range(3):  # Check up to 3 levels
        check_dir = current_dir.parents[i] if i < len(current_dir.parents) else None
        if check_dir:
            ipfs_path = check_dir / 'ipfs'
            if ipfs_path.exists() and ipfs_path.is_file():
                search_paths.append(str(ipfs_path))

    # 3. Search home directory and common locations
    home_dir = Path.home()
    common_locations = [
        home_dir / 'ipfs',
        home_dir / 'bin' / 'ipfs',
        home_dir / '.local' / 'bin' / 'ipfs',
        Path('/usr/local/bin/ipfs'),
        Path('/usr/bin/ipfs'),
        Path('/bin/ipfs'),
        Path('/opt/ipfs/ipfs'),
    ]

    for location in common_locations:
        if location.exists() and location.is_file():
            search_paths.append(str(location))

    # 4. Search in PATH directories
    path_env = os.environ.get('PATH', '')
    for path_dir in path_env.split(':'):
        if path_dir:
            ipfs_path = Path(path_dir) / 'ipfs'
            if ipfs_path.exists() and ipfs_path.is_file():
                search_paths.append(str(ipfs_path))

    # 5. Add fallback system command (relative to current directory)
    search_paths.extend([str(current_dir / 'ipfs'), 'ipfs'])

    # Test each path
    for ipfs_path in search_paths:
        try:
            result = subprocess.run([ipfs_path, 'version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Found IPFS binary: {ipfs_path}")
                return ipfs_path
        except:
            continue

    print("⚠️  Using fallback 'ipfs' command - ensure it's in PATH")
    return 'ipfs'

def find_node_ipfs_binary(db_path: str) -> Optional[str]:
    """
    Find IPFS binary for a specific node by walking up from rubix.db location.

    Args:
        db_path: Path to rubix.db file (e.g., /this/is/my/path/SafePass/Rubix/Qnode1/Rubix/rubix.db)

    Returns:
        Path to ipfs binary for this node, or None if not found
    """
    db_path_obj = Path(db_path)

    # Start from rubix.db location and walk up
    current_path = db_path_obj.parent  # Start from Rubix directory
    max_levels = 10  # Reasonable limit to prevent infinite loops

    for level in range(max_levels):
        logger.debug(f"  Searching for ipfs binary at level {level}: {current_path}")

        # Check for ipfs binary in current directory
        ipfs_binary = current_path / 'ipfs'
        if ipfs_binary.exists() and ipfs_binary.is_file():
            try:
                # Test if it's a working IPFS binary
                result = subprocess.run([str(ipfs_binary), 'version'],
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    logger.debug(f"Found working IPFS binary: {ipfs_binary}")
                    return str(ipfs_binary)
            except:
                pass

        # Check for rubixgoplatform as indicator (90% chance ipfs is here)
        rubixgo_binary = current_path / 'rubixgoplatform'
        if rubixgo_binary.exists() and rubixgo_binary.is_file():
            logger.debug(f"Found rubixgoplatform at {current_path}, checking for ipfs")
            # Check if ipfs is also in this directory
            ipfs_binary = current_path / 'ipfs'
            if ipfs_binary.exists() and ipfs_binary.is_file():
                try:
                    result = subprocess.run([str(ipfs_binary), 'version'],
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        logger.debug(f"Found IPFS binary with rubixgoplatform: {ipfs_binary}")
                        return str(ipfs_binary)
                except:
                    pass

        # Move up one level
        if current_path == current_path.parent:  # Reached root
            break
        current_path = current_path.parent

    # Fallback to common system locations
    common_locations = [
        Path('/usr/local/bin/ipfs'),
        Path('/usr/bin/ipfs'),
        Path('/bin/ipfs'),
    ]

    for ipfs_path in common_locations:
        if ipfs_path.exists() and ipfs_path.is_file():
            try:
                result = subprocess.run([str(ipfs_path), 'version'],
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    logger.debug(f"Found IPFS binary (system fallback): {ipfs_path}")
                    return str(ipfs_path)
            except:
                pass

    logger.warning(f"No IPFS binary found for node: {db_path}")
    return None


IPFS_COMMAND = find_ipfs_binary()  # Global fallback - will be replaced with per-node detection
TELEGRAM_CONFIG_FILE = 'telegram_config.json'

# Performance tuning - Optimized for Azure SQL Database
NUM_DB_WORKERS = max(1, cpu_count() // 2)  # Parallel database processing
NUM_IPFS_WORKERS = cpu_count() * 2  # Increased for better IPFS throughput
BATCH_SIZE = 2000  # Larger batches for Azure SQL Database efficiency
BULK_INSERT_SIZE = 1000   # Reduced for Azure SQL stability - prevents network timeouts
IPFS_TIMEOUT = 12  # Reduced timeout for faster failover
CONNECTION_POOL_SIZE = 10  # Connection pool for Azure SQL
RETRY_ATTEMPTS = 3  # Retry failed operations
PROGRESS_REPORT_INTERVAL = 100  # Report progress every N records

# Data validation and quality settings
VALIDATE_TOKEN_FORMAT = True
VALIDATE_IPFS_DATA = True
MAX_ERROR_LOG_SIZE = 1000  # Maximum errors to keep in memory

# Enhanced logging configuration with detailed audit trails
import logging.handlers
from logging.handlers import RotatingFileHandler
import uuid
import traceback

# Create custom formatter for structured logging
class AuditFormatter(logging.Formatter):
    """Custom formatter that adds structured data for audit trails"""

    def format(self, record):
        # Add correlation ID if not present
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = getattr(logging.getLoggerClass(), '_correlation_id', 'N/A')

        # Add component if not present
        if not hasattr(record, 'component'):
            record.component = 'MAIN'

        # Add operation if not present
        if not hasattr(record, 'operation'):
            record.operation = 'GENERAL'

        # Create base log entry
        base_msg = super().format(record)

        # Add structured data for audit
        audit_data = {
            'timestamp': record.created,
            'level': record.levelname,
            'component': record.component,
            'operation': record.operation,
            'correlation_id': record.correlation_id,
            'thread_id': record.thread,
            'process_id': record.process
        }

        # Add extra context if available
        if hasattr(record, 'extra_data'):
            audit_data.update(record.extra_data)

        # Format as: TIMESTAMP - LEVEL - COMPONENT:OPERATION [CORRELATION_ID] - MESSAGE
        formatted = f"{record.asctime} - {record.levelname} - {record.component}:{record.operation} [{record.correlation_id}] - {record.getMessage()}"

        # Add stack trace for errors
        if record.levelname in ['ERROR', 'CRITICAL'] and record.exc_info:
            formatted += f"\nStack Trace: {self.formatException(record.exc_info)}"

        return formatted

# Detect if running in multiprocessing worker
def is_multiprocessing_worker():
    """Detect if we're running in a multiprocessing worker process"""
    try:
        # Check if we have a multiprocessing current_process
        from multiprocessing import current_process
        process = current_process()
        # Main process is usually named 'MainProcess', workers have different names
        return process.name != 'MainProcess'
    except:
        return False

# Setup comprehensive logging with multiple handlers
def setup_detailed_logging():
    """Setup detailed logging with multiple log files and audit trails"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Get current timestamp for log file naming
    timestamp = datetime.now().strftime("%Y%m%d")

    # Main application logger
    main_logger = logging.getLogger(__name__)
    main_logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    for handler in main_logger.handlers[:]:
        main_logger.removeHandler(handler)

    # Custom formatter
    formatter = AuditFormatter(
        fmt='%(asctime)s - %(levelname)s - %(component)s:%(operation)s [%(correlation_id)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Check if we're in a multiprocessing worker
    if is_multiprocessing_worker():
        # For workers: Only use console logging to avoid file rotation conflicts
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)  # Only show errors from workers
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        main_logger.addHandler(console_handler)
        return main_logger

    # For main process: Use full logging with file rotation
    # 1. Main application log (rotating)
    main_handler = RotatingFileHandler(
        log_dir / f"sync_main_{timestamp}.log",
        maxBytes=100*1024*1024,  # 100MB
        backupCount=10
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(formatter)

    # 2. Debug log with everything (rotating)
    debug_handler = RotatingFileHandler(
        log_dir / f"sync_debug_{timestamp}.log",
        maxBytes=200*1024*1024,  # 200MB
        backupCount=5
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)

    # 3. Error-only log (permanent retention)
    error_handler = RotatingFileHandler(
        log_dir / f"sync_errors_{timestamp}.log",
        maxBytes=50*1024*1024,  # 50MB
        backupCount=50  # Keep more error logs
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # 4. Console output (clean format - reduced verbosity)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors on console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # Add all handlers
    main_logger.addHandler(main_handler)
    main_logger.addHandler(debug_handler)
    main_logger.addHandler(error_handler)
    main_logger.addHandler(console_handler)

    return main_logger

# Component-specific loggers
def get_component_logger(component_name: str):
    """Get a logger for a specific component with proper context"""
    logger = logging.getLogger(f"{__name__}.{component_name}")

    # Skip file handlers for multiprocessing workers to avoid conflicts
    if is_multiprocessing_worker():
        return logger

    # Create component-specific log file (only for main process)
    log_dir = Path("logs")
    timestamp = datetime.now().strftime("%Y%m%d")

    if not any(isinstance(h, RotatingFileHandler) and component_name in str(h.baseFilename)
               for h in logger.handlers):
        component_handler = RotatingFileHandler(
            log_dir / f"sync_{component_name.lower()}_{timestamp}.log",
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10
        )
        component_handler.setLevel(logging.DEBUG)
        component_handler.setFormatter(AuditFormatter(
            fmt='%(asctime)s - %(levelname)s - %(operation)s [%(correlation_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(component_handler)

    return logger

# Setup logging system
logger = setup_detailed_logging()
ipfs_logger = get_component_logger('IPFS')
sql_logger = get_component_logger('SQL')
validation_logger = get_component_logger('VALIDATION')
sync_logger = get_component_logger('SYNC')

# Thread-safe logging for parallel operations
log_lock = threading.Lock()

# Audit logging utilities
class AuditLogger:
    """Centralized audit logging with correlation tracking"""

    def __init__(self):
        self.correlation_stack = []
        self.operation_stack = []

    def start_operation(self, operation_name: str, correlation_id: str = None) -> str:
        """Start a new operation with correlation tracking"""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:8]

        self.correlation_stack.append(correlation_id)
        self.operation_stack.append(operation_name)

        # Set correlation ID on logger class for thread safety
        logging.getLoggerClass()._correlation_id = correlation_id

        return correlation_id

    def end_operation(self):
        """End the current operation"""
        if self.correlation_stack:
            self.correlation_stack.pop()
        if self.operation_stack:
            self.operation_stack.pop()

        # Update correlation ID
        correlation_id = self.correlation_stack[-1] if self.correlation_stack else 'N/A'
        logging.getLoggerClass()._correlation_id = correlation_id

    def log_with_context(self, logger, level, message, component='MAIN', operation=None,
                        extra_data=None, exc_info=None):
        """Log with full context and audit trail"""
        if operation is None:
            operation = self.operation_stack[-1] if self.operation_stack else 'GENERAL'

        correlation_id = self.correlation_stack[-1] if self.correlation_stack else 'N/A'

        # Create log record with full context
        record_extra = {
            'component': component,
            'operation': operation,
            'correlation_id': correlation_id,
            'extra_data': extra_data or {}
        }

        if exc_info:
            logger.log(level, message, extra=record_extra, exc_info=exc_info)
        else:
            logger.log(level, message, extra=record_extra)

# Global audit logger instance
audit_logger = AuditLogger()

# Context manager for operations
class OperationContext:
    """Context manager for tracking operations with automatic logging"""

    def __init__(self, operation_name: str, component: str = 'MAIN',
                 logger_instance=None, log_start=True, log_end=True):
        self.operation_name = operation_name
        self.component = component
        self.logger_instance = logger_instance or logger
        self.log_start = log_start
        self.log_end = log_end
        self.correlation_id = None
        self.start_time = None
        self.success = False

    def __enter__(self):
        self.correlation_id = audit_logger.start_operation(self.operation_name)
        self.start_time = datetime.now(timezone.utc)

        if self.log_start:
            audit_logger.log_with_context(
                self.logger_instance, logging.INFO,
                f"Starting {self.operation_name}",
                component=self.component,
                operation=self.operation_name,
                extra_data={'start_time': self.start_time.isoformat()}
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds()

        if exc_type is None:
            self.success = True
            if self.log_end:
                audit_logger.log_with_context(
                    self.logger_instance, logging.INFO,
                    f"Completed {self.operation_name} successfully",
                    component=self.component,
                    operation=self.operation_name,
                    extra_data={
                        'duration_seconds': duration,
                        'end_time': end_time.isoformat(),
                        'success': True
                    }
                )
        else:
            self.success = False
            error_details = {
                'duration_seconds': duration,
                'end_time': end_time.isoformat(),
                'success': False,
                'error_type': exc_type.__name__,
                'error_message': str(exc_val),
                'stack_trace': traceback.format_exc()
            }

            audit_logger.log_with_context(
                self.logger_instance, logging.ERROR,
                f"Failed {self.operation_name}: {exc_val}",
                component=self.component,
                operation=self.operation_name,
                extra_data=error_details,
                exc_info=(exc_type, exc_val, exc_tb)
            )

        audit_logger.end_operation()

    def add_context(self, key: str, value: Any):
        """Add additional context to the operation"""
        audit_logger.log_with_context(
            self.logger_instance, logging.DEBUG,
            f"Context update: {key} = {value}",
            component=self.component,
            operation=self.operation_name,
            extra_data={key: value}
        )

# Enhanced logging functions
def log_database_operation(operation: str, query: str, params=None, affected_rows=None,
                          duration=None, success=True, error=None):
    """Log database operations with full context"""
    extra_data = {
        'query': query[:200] + '...' if len(query) > 200 else query,  # Truncate long queries
        'param_count': len(params) if params else 0,
        'affected_rows': affected_rows,
        'duration_ms': duration * 1000 if duration else None,
        'success': success
    }

    if error:
        extra_data['error'] = str(error)

    level = logging.INFO if success else logging.ERROR
    message = f"Database {operation}: {'SUCCESS' if success else 'FAILED'}"

    audit_logger.log_with_context(
        sql_logger, level, message,
        component='SQL', operation=operation,
        extra_data=extra_data,
        exc_info=error if not success else None
    )

def log_ipfs_operation(token_id: str, operation: str, ipfs_path: str = None,
                      data_size=None, duration=None, success=True, error=None):
    """Log IPFS operations with full context"""
    extra_data = {
        'token_id': token_id,
        'ipfs_path': ipfs_path,
        'data_size_bytes': data_size,
        'duration_ms': duration * 1000 if duration else None,
        'success': success
    }

    if error:
        extra_data['error'] = str(error)

    level = logging.INFO if success else logging.WARNING
    message = f"IPFS {operation} for token {token_id}: {'SUCCESS' if success else 'FAILED'}"

    audit_logger.log_with_context(
        ipfs_logger, level, message,
        component='IPFS', operation=operation,
        extra_data=extra_data
    )

def log_validation_result(token_id: str, validation_type: str, is_valid: bool,
                         errors: List[str] = None, warnings: List[str] = None):
    """Log validation results with detailed context"""
    extra_data = {
        'token_id': token_id,
        'validation_type': validation_type,
        'is_valid': is_valid,
        'error_count': len(errors) if errors else 0,
        'warning_count': len(warnings) if warnings else 0,
        'errors': errors,
        'warnings': warnings
    }

    level = logging.INFO if is_valid else logging.WARNING
    message = f"Validation {validation_type} for token {token_id}: {'PASSED' if is_valid else 'FAILED'}"

    audit_logger.log_with_context(
        validation_logger, level, message,
        component='VALIDATION', operation=validation_type,
        extra_data=extra_data
    )

def log_sync_progress(database_name: str, progress_data: Dict[str, Any]):
    """Log sync progress with comprehensive metrics"""
    audit_logger.log_with_context(
        sync_logger, logging.INFO,
        f"Sync progress for {database_name}",
        component='SYNC', operation='PROGRESS_UPDATE',
        extra_data=progress_data
    )

def log_performance_metrics(operation: str, metrics: Dict[str, Any]):
    """Log performance metrics for analysis"""
    audit_logger.log_with_context(
        logger, logging.INFO,
        f"Performance metrics for {operation}",
        component='PERFORMANCE', operation=operation,
        extra_data=metrics
    )

@dataclass
class SyncMetrics:
    """Thread-safe metrics tracking for sync operations"""
    total_databases_found: int = 0
    total_databases_processed: int = 0
    total_records_processed: int = 0
    total_ipfs_success: int = 0
    total_ipfs_failures: int = 0
    total_sql_inserts: int = 0
    total_sql_errors: int = 0
    total_validation_errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.start_time is None:
            self.start_time = datetime.now(timezone.utc)

    def add_error(self, error_type: str, message: str, context: Dict[str, Any] = None):
        """Thread-safe error logging with Telegram notification"""
        with log_lock:
            if len(self.errors) < MAX_ERROR_LOG_SIZE:
                self.errors.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'type': error_type,
                    'message': message,
                    'context': context or {}
                })

            # Send Telegram notification for critical errors
            if TELEGRAM_AVAILABLE and error_type in ['database', 'system', 'connection']:
                try:
                    notify_error(error_type, message, context)
                except Exception as e:
                    # Don't let Telegram errors break the sync
                    print(f"Failed to send Telegram error notification: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization"""
        duration = None
        if self.end_time and self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            **asdict(self),
            'duration_seconds': duration,
            'records_per_second': self.total_records_processed / max(duration or 1, 1),
            'ipfs_success_rate': self.total_ipfs_success / max(self.total_records_processed, 1) * 100,
            'sql_success_rate': (self.total_records_processed - self.total_sql_errors) / max(self.total_records_processed, 1) * 100,
            'total_errors': len(self.errors)
        }

@dataclass
class TokenRecord:
    """Structured token record for validation and processing"""
    source_ip: str
    node_name: str
    did: Optional[str]
    token_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    token_status: Optional[str]
    parent_token_id: Optional[str]
    token_value: Optional[str]
    ipfs_data: Optional[str]
    ipfs_fetched: bool
    ipfs_error: Optional[str]
    db_path: str
    ipfs_path: Optional[str]
    db_last_modified: datetime
    validation_errors: List[str] = None

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []

    def validate(self) -> bool:
        """Validate token record and log issues with detailed audit trail"""
        is_valid = True
        validation_warnings = []

        # Token ID validation
        if VALIDATE_TOKEN_FORMAT:
            if not self.token_id or len(self.token_id.strip()) == 0:
                self.validation_errors.append("Missing or empty token_id")
                is_valid = False
            elif len(self.token_id) > 500:  # Token ID length limit
                self.validation_errors.append("Token ID exceeds maximum length (500)")
                is_valid = False

            # DID validation
            if self.did:
                if len(self.did) > 1000:  # Reasonable DID length limit
                    self.validation_errors.append("DID exceeds maximum length (1000)")
                    is_valid = False
                elif len(self.did) < 10:  # Minimum DID length warning
                    validation_warnings.append("DID is unusually short")

            # Token status validation
            if self.token_status and self.token_status not in ['ACTIVE', 'INACTIVE', 'PENDING', 'REVOKED']:
                validation_warnings.append(f"Unknown token status: {self.token_status}")

        # IPFS data validation
        if VALIDATE_IPFS_DATA and self.ipfs_fetched and self.ipfs_data:
            if len(self.ipfs_data) > 50000:  # 50KB limit for IPFS data
                self.validation_errors.append("IPFS data exceeds size limit (50KB)")
                is_valid = False
            elif len(self.ipfs_data) < 10:  # Minimum data size warning
                validation_warnings.append("IPFS data is unusually small")

        # Database path validation
        if not self.db_path or not os.path.exists(self.db_path):
            self.validation_errors.append("Invalid or missing database path")
            is_valid = False

        # Log validation results
        log_validation_result(
            self.token_id or 'UNKNOWN',
            'RECORD_VALIDATION',
            is_valid,
            errors=self.validation_errors,
            warnings=validation_warnings
        )

        return is_valid

# Global metrics instance
sync_metrics = SyncMetrics()

# Cache for public IP
_cached_public_ip = None

# Connection pool management
class AzureSQLConnectionPool:
    """Thread-safe connection pool for Azure SQL Database"""

    def __init__(self, connection_string: str, pool_size: int = CONNECTION_POOL_SIZE):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.pool = []
        self.pool_lock = threading.Lock()
        self.active_connections = 0

    def get_connection(self):
        """Get a connection from the pool or create a new one"""
        with self.pool_lock:
            if self.pool:
                return self.pool.pop()
            elif self.active_connections < self.pool_size:
                self.active_connections += 1
                # Debug: Log the connection string being used
                logger.debug(f"Creating connection with string: {self.connection_string[:50]}...")
                return pyodbc.connect(self.connection_string)
            else:
                # Pool exhausted, wait and retry
                time.sleep(0.1)
                return self.get_connection()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        with self.pool_lock:
            if len(self.pool) < self.pool_size:
                self.pool.append(conn)
            else:
                conn.close()
                self.active_connections -= 1

    def close_all(self):
        """Close all connections in the pool"""
        with self.pool_lock:
            for conn in self.pool:
                try:
                    conn.close()
                except:
                    pass
            self.pool.clear()
            self.active_connections = 0

# Global connection pool
connection_pool = None


def get_azure_sql_connection_string() -> str:
    """Get Azure SQL Database connection string from config file if available."""
    global AZURE_SQL_CONNECTION_STRING

    connection_string = AZURE_SQL_CONNECTION_STRING  # Default fallback

    if os.path.exists(CONNECTION_CONFIG_FILE):
        try:
            with open(CONNECTION_CONFIG_FILE, 'r') as f:
                content = f.read().strip()

                # Handle corrupted/duplicated connection strings
                if content and 'DRIVER=' in content:
                    # Remove any duplicate/corrupted parts
                    lines = content.split('\n')
                    # Take the first line that starts with DRIVER and looks valid
                    for line in lines:
                        line = line.strip()
                        if line.startswith('DRIVER=') and 'SERVER=' in line and 'DATABASE=' in line:
                            # Check if it's not corrupted (no duplicate DRIVER= in same line)
                            if line.count('DRIVER=') == 1 and line.count('SERVER=') == 1:
                                logger.info("Loaded Azure SQL connection string from config file")
                                connection_string = line
                                break
                    else:
                        logger.warning("Connection string appears corrupted in config file")
                        logger.info(f"Corrupted content: {content[:100]}...")
        except Exception as e:
            logger.warning(f"Could not read Azure SQL connection file: {e}")
            sync_metrics.add_error("connection", f"Failed to read config file: {e}")

    # Validate that password is set (check the actual connection string being used, not the fallback)
    if "{your_password}" in connection_string:
        logger.error("Password placeholder found in connection string. Please update the password.")
        raise ValueError("Azure SQL Database password not configured")

    return connection_string

def init_connection_pool() -> AzureSQLConnectionPool:
    """Initialize the global connection pool"""
    global connection_pool
    if connection_pool is None:
        conn_string = get_azure_sql_connection_string()

        # Test the connection before creating pool
        logger.info("Testing Azure SQL connection before creating pool...")
        try:
            test_conn = pyodbc.connect(conn_string)
            test_conn.close()
            logger.info("Azure SQL connection test successful")
        except Exception as e:
            logger.error(f"Azure SQL connection test failed: {e}")
            raise ValueError(f"Azure SQL Database connection failed: {e}")

        connection_pool = AzureSQLConnectionPool(conn_string)
        logger.info(f"Initialized Azure SQL connection pool with {CONNECTION_POOL_SIZE} connections")
    return connection_pool


def get_public_ip() -> str:
    """Get the public IP address of the current VM."""
    global _cached_public_ip

    if _cached_public_ip:
        return _cached_public_ip

    services = [
        'https://api.ipify.org?format=text',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
        'http://wtfismyip.com/text'
    ]

    for service in services:
        try:
            response = requests.get(service, timeout=5)
            if response.status_code == 200:
                ip = response.text.strip()
                _cached_public_ip = ip
                logger.info(f"Detected public IP: {ip}")

                # Update Telegram notifier with machine info
                if TELEGRAM_AVAILABLE:
                    import socket
                    hostname = socket.gethostname()
                    update_machine_info(ip, hostname)

                return ip
        except Exception as e:
            logger.warning(f"Failed to get IP from {service}: {e}")
            continue

    logger.warning("Could not detect public IP, using 'unknown'")
    _cached_public_ip = 'unknown'
    return _cached_public_ip

def initialize_telegram_notifications():
    """Initialize Telegram notifications if configured"""
    if not TELEGRAM_AVAILABLE:
        return False

    try:
        # Try to initialize with existing config
        notifier = init_telegram_notifier()

        if notifier and notifier.config.enabled and notifier.config.bot_token:
            # Test connection
            if notifier.test_connection():
                audit_logger.log_with_context(
                    logger, logging.INFO, "Telegram notifications initialized successfully",
                    component='TELEGRAM', operation='INITIALIZATION',
                    extra_data={
                        'machine_id': notifier.machine_id,
                        'chat_id': notifier.config.chat_id[:10] + "..." if notifier.config.chat_id else "N/A"
                    }
                )
                return True
            else:
                logger.warning("Telegram connection test failed")
                return False
        else:
            logger.info("Telegram notifications not configured or disabled")
            return False

    except Exception as e:
        logger.warning(f"Failed to initialize Telegram notifications: {e}")
        return False


def safe_str(value) -> Optional[str]:
    """Safely convert value to string, handling None and empty strings."""
    if value is None or value == '':
        return None
    if value == 'c not found':
        return 'c not found'  # Preserve placeholder for missing columns
    return str(value).strip() if str(value).strip() else None


def safe_timestamp(value) -> Optional[datetime]:
    """Safely convert value to datetime, handling various formats and None."""
    if value is None or value == '' or value == 'c not found':
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except:
            return None

    if isinstance(value, str):
        # Try various datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%f',
        ]

        # Remove timezone indicators
        value = value.replace('Z', '').replace('+00:00', '')

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except:
                continue

    return None


def build_ipfs_path_mapping(databases: List[Tuple[str, float]]) -> Dict[str, str]:
    """
    Build a mapping of database paths to their corresponding .ipfs directories.
    This pre-maps all IPFS paths to avoid repeated discovery during processing.

    Returns:
        Dict[db_path, ipfs_path] - Mapping of database paths to .ipfs directories
    """
    ipfs_mapping = {}

    logger.info("🗂️  Building IPFS path mapping for all databases...")

    for db_path, _ in databases:
        node_name = extract_node_name(db_path)
        ipfs_path = find_ipfs_directory(db_path)

        if ipfs_path:
            ipfs_mapping[db_path] = ipfs_path
            logger.debug(f"  ✅ {node_name}: {ipfs_path}")
        else:
            logger.warning(f"  ❌ {node_name}: No .ipfs directory found")
            ipfs_mapping[db_path] = None

    # Summary statistics
    valid_ipfs = sum(1 for path in ipfs_mapping.values() if path is not None)
    total_dbs = len(databases)

    logger.info(f"📊 IPFS Mapping Summary:")
    logger.info(f"  Total databases: {total_dbs}")
    logger.info(f"  Valid .ipfs paths: {valid_ipfs}")
    logger.info(f"  Missing .ipfs: {total_dbs - valid_ipfs}")

    # Show unique .ipfs directories found
    unique_ipfs_dirs = set(path for path in ipfs_mapping.values() if path is not None)
    logger.info(f"  Unique .ipfs directories: {len(unique_ipfs_dirs)}")
    for ipfs_dir in sorted(unique_ipfs_dirs):
        node_count = sum(1 for path in ipfs_mapping.values() if path == ipfs_dir)
        logger.info(f"    {ipfs_dir} (used by {node_count} nodes)")

    return ipfs_mapping


def find_rubix_databases(start_path: str = '.') -> List[Tuple[str, float]]:
    """
    Recursively search for Rubix/rubix.db files.
    Returns list of tuples: (db_path, last_modified_timestamp)
    """
    logger.info(f"Scanning for rubix.db files from: {os.path.abspath(start_path)}")

    databases = []
    start_path = Path(start_path).resolve()

    for rubix_db in start_path.rglob('Rubix/rubix.db'):
        if rubix_db.is_file():
            db_path = str(rubix_db)
            last_modified = rubix_db.stat().st_mtime
            databases.append((db_path, last_modified))
            logger.info(f"Found database: {db_path}")

    logger.info(f"Total databases found: {len(databases)}")
    return databases


def find_ipfs_directory(db_path: str) -> Optional[str]:
    """
    Find .ipfs directory by walking UP from rubix.db location.

    Examples:
    - DB at /this/is/my/path/node1/Rubix/rubix.db -> .ipfs at /this/is/my/path/node1/.ipfs
    - DB at /this/is/my/path/SafePass/Rubix/Qnode1/Rubix/rubix.db -> .ipfs at /this/is/my/path/SafePass/Rubix/Qnode1/.ipfs

    Pattern: Walk up from rubix.db location checking each level for .ipfs
    """
    db_path_obj = Path(db_path)

    # Start from rubix.db location and walk up
    current_path = db_path_obj.parent  # Start from Rubix directory
    max_levels = 10  # Reasonable limit to prevent infinite loops

    for level in range(max_levels):
        # Check for .ipfs at current level
        ipfs_path = current_path / '.ipfs'

        logger.debug(f"  Checking level {level}: {ipfs_path}")

        if ipfs_path.exists() and ipfs_path.is_dir():
            # Verify it's a valid IPFS directory
            ipfs_indicators = [
                ipfs_path / 'config',
                ipfs_path / 'datastore',
                ipfs_path / 'keystore',
                ipfs_path / 'blocks',
                ipfs_path / 'version'
            ]

            if any(indicator.exists() for indicator in ipfs_indicators):
                logger.debug(f"Found valid IPFS dir: {ipfs_path}")
                return str(ipfs_path)

        # Move up one level
        if current_path == current_path.parent:  # Reached root
            break
        current_path = current_path.parent

    # If pattern-based search fails, check a few common fallback locations
    # Get node directory for fallback (parent of Rubix)
    node_dir = db_path_obj.parent.parent

    fallback_locations = [
        node_dir / '.ipfs',  # Node-specific .ipfs
        Path.cwd() / '.ipfs',  # Current working directory
        Path.home() / '.ipfs',  # User home directory
    ]

    for ipfs_path in fallback_locations:
        if ipfs_path.exists() and ipfs_path.is_dir():
            ipfs_indicators = [
                ipfs_path / 'config',
                ipfs_path / 'datastore',
                ipfs_path / 'keystore',
                ipfs_path / 'blocks',
                ipfs_path / 'version'
            ]

            if any(indicator.exists() for indicator in ipfs_indicators):
                logger.debug(f"Found IPFS dir (fallback): {ipfs_path}")
                return str(ipfs_path)

    logger.warning(f"No valid .ipfs directory found for {db_path}")
    logger.debug(f"  Searched from: {db_path_obj.parent}")
    return None


def extract_node_name(db_path: str) -> str:
    """
    Extract node name from database path.
    E.g., /mnt/drived/node032/Rubix/rubix.db -> node032
    """
    db_path_obj = Path(db_path)
    node_dir = db_path_obj.parent.parent
    return node_dir.name


def clear_ipfs_lock(ipfs_path: str) -> bool:
    """
    Clear stale IPFS repository lock files.

    Args:
        ipfs_path: Path to the .ipfs directory

    Returns:
        bool: True if lock was cleared or didn't exist, False if unable to clear
    """
    try:
        lock_file = Path(ipfs_path) / 'repo.lock'
        if lock_file.exists():
            logger.debug(f"Removing stale IPFS lock: {lock_file}")
            lock_file.unlink()
            return True
        return True  # No lock file, so it's clear
    except Exception as e:
        logger.warning(f"Failed to clear IPFS lock {lock_file}: {e}")
        return False


def is_ipfs_daemon_running(ipfs_path: str) -> bool:
    """
    Check if IPFS daemon is already running for this repository.

    Args:
        ipfs_path: Path to the .ipfs directory

    Returns:
        bool: True if daemon is running, False otherwise
    """
    try:
        api_file = Path(ipfs_path) / 'api'
        return api_file.exists()
    except:
        return False


def fetch_ipfs_data(token_id: str, ipfs_path: str, script_dir: str, ipfs_binary: str = None) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Fetch IPFS data for a token_id using ipfs cat with detailed logging.

    Args:
        token_id: Token ID to fetch from IPFS
        ipfs_path: Path to .ipfs directory for IPFS_PATH environment variable
        script_dir: Script directory for command execution
        ipfs_binary: Path to IPFS binary (if None, uses global IPFS_COMMAND)

    Returns:
        (ipfs_data, success, error_message)
    """
    if not token_id or token_id.strip() == '':
        log_ipfs_operation(token_id, 'FETCH', ipfs_path, success=False, error="Empty token_id")
        return (None, False, "Empty token_id")

    operation_start = time.time()

    with OperationContext(f"IPFS_FETCH_{token_id[:8]}", 'IPFS', ipfs_logger, log_start=False, log_end=False):
        try:
            # Set IPFS_PATH environment variable
            env = os.environ.copy()
            env['IPFS_PATH'] = ipfs_path

            # Log the attempt (only in main process to avoid multiprocessing conflicts)
            if not is_multiprocessing_worker():
                audit_logger.log_with_context(
                    ipfs_logger, logging.DEBUG,
                    f"Attempting IPFS fetch for token {token_id}",
                    component='IPFS', operation='FETCH',
                    extra_data={
                        'token_id': token_id,
                        'ipfs_path': ipfs_path,
                        'script_dir': script_dir,
                        'timeout': IPFS_TIMEOUT
                    }
                )

            # Handle IPFS repository lock conflicts
            max_lock_retries = 3
            lock_retry_delay = 0.5  # seconds

            for lock_attempt in range(max_lock_retries):
                try:
                    # Use per-node IPFS binary if provided, otherwise fall back to global
                    ipfs_cmd = ipfs_binary if ipfs_binary else IPFS_COMMAND

                    # Run ipfs cat command using node-specific or global IPFS binary
                    result = subprocess.run(
                        [ipfs_cmd, 'cat', token_id],
                        capture_output=True,
                        text=True,
                        timeout=IPFS_TIMEOUT,
                        env=env,
                        cwd=script_dir
                    )

                    # Check for lock errors
                    if result.returncode != 0 and 'repo.lock' in result.stderr:
                        if lock_attempt < max_lock_retries - 1:  # Not the last attempt
                            logger.debug(f"IPFS lock conflict for {token_id}, attempt {lock_attempt + 1}, clearing lock and retrying...")

                            # Try to clear the lock and retry
                            if clear_ipfs_lock(ipfs_path):
                                time.sleep(lock_retry_delay * (lock_attempt + 1))  # Exponential backoff
                                continue
                            else:
                                # If we can't clear the lock, fail this attempt
                                break
                        else:
                            # Last attempt failed, return the lock error
                            logger.warning(f"IPFS lock conflict persists for {token_id} after {max_lock_retries} attempts")
                            break
                    else:
                        # No lock error, break out of retry loop
                        break

                except subprocess.TimeoutExpired:
                    # Handle timeout separately - don't retry for timeouts
                    duration = time.time() - operation_start
                    limited_error = "IPFS timeout"

                    log_ipfs_operation(
                        token_id, 'FETCH', ipfs_path,
                        duration=duration, success=False, error=limited_error
                    )

                    return (None, False, limited_error)

            duration = time.time() - operation_start

            if result.returncode == 0:
                ipfs_data = result.stdout.strip()
                data_size = len(ipfs_data) if ipfs_data else 0

                log_ipfs_operation(
                    token_id, 'FETCH', ipfs_path,
                    data_size=data_size, duration=duration, success=True
                )

                return (ipfs_data if ipfs_data else None, True, None)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                limited_error = error_msg[:500]  # Limit error message length

                log_ipfs_operation(
                    token_id, 'FETCH', ipfs_path,
                    duration=duration, success=False, error=limited_error
                )

                return (None, False, limited_error)

        except subprocess.TimeoutExpired:
            duration = time.time() - operation_start
            error_msg = f"IPFS timeout after {IPFS_TIMEOUT}s"

            log_ipfs_operation(
                token_id, 'FETCH', ipfs_path,
                duration=duration, success=False, error=error_msg
            )

            return (None, False, "IPFS timeout")

        except Exception as e:
            duration = time.time() - operation_start
            error_msg = str(e)[:500]

            log_ipfs_operation(
                token_id, 'FETCH', ipfs_path,
                duration=duration, success=False, error=error_msg
            )

            # Log full exception details (allow ERROR logging but reduce verbosity in workers)
            if not is_multiprocessing_worker():
                audit_logger.log_with_context(
                    ipfs_logger, logging.ERROR,
                    f"Unexpected error fetching IPFS data for token {token_id}",
                    component='IPFS', operation='FETCH',
                    extra_data={
                        'token_id': token_id,
                        'error': error_msg,
                        'exception_type': type(e).__name__
                    },
                    exc_info=True
                )
            else:
                # In workers, just print to stdout without file logging
                print(f"ERROR: IPFS fetch failed for {token_id}: {error_msg}", flush=True)

            return (None, False, error_msg)


def process_token_ipfs(args: Tuple) -> TokenRecord:
    """
    Process a single token: fetch IPFS data and prepare record.
    This function is designed for parallel execution.
    """
    (token_row, source_ip, node_name, db_path, ipfs_path, ipfs_binary, db_last_modified, script_dir) = args

    # Extract SQLite fields with safe handling
    did = safe_str(token_row[0])
    token_id = safe_str(token_row[1])
    created_at = safe_timestamp(token_row[2])
    updated_at = safe_timestamp(token_row[3])
    token_status = safe_str(token_row[4])
    parent_token_id = safe_str(token_row[5])
    token_value = safe_str(token_row[6])

    # Fetch IPFS data if token_id exists
    ipfs_data = None
    ipfs_fetched = False
    ipfs_error = None

    if token_id and ipfs_path:
        for attempt in range(RETRY_ATTEMPTS):
            ipfs_data, ipfs_fetched, ipfs_error = fetch_ipfs_data(token_id, ipfs_path, script_dir, ipfs_binary)
            if ipfs_fetched or ipfs_error != "IPFS timeout":
                break
            time.sleep(0.1 * (attempt + 1))  # Brief exponential backoff
    elif not ipfs_path:
        ipfs_error = "No IPFS path found"

    # Create and validate record
    db_modified_dt = datetime.fromtimestamp(db_last_modified)

    record = TokenRecord(
        source_ip=source_ip,
        node_name=node_name,
        did=did,
        token_id=token_id,
        created_at=created_at,
        updated_at=updated_at,
        token_status=token_status,
        parent_token_id=parent_token_id,
        token_value=token_value,
        ipfs_data=ipfs_data,
        ipfs_fetched=ipfs_fetched,
        ipfs_error=ipfs_error,
        db_path=db_path,
        ipfs_path=ipfs_path,
        db_last_modified=db_modified_dt
    )

    # Validate the record
    if not record.validate():
        sync_metrics.total_validation_errors += 1

    return record


def ensure_essential_metadata(db_path: str, source_ip: str, force_update: bool = False) -> bool:
    """
    Ensure essential metadata (token_id, did, source_ip, node_name) is captured
    in the database even if IPFS or other processing fails.

    This function guarantees we have core node data coverage by inserting minimal
    records with just the essential fields.

    Args:
        db_path: Path to the SQLite database
        source_ip: Source IP address
        force_update: If True, update existing records with minimal data

    Returns:
        bool: True if essential metadata was successfully captured
    """
    try:
        node_name = extract_node_name(db_path)
        logger.info(f"Ensuring essential metadata for {node_name}: {db_path}")

        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if TokensTable exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='TokensTable'
        """)

        if not cursor.fetchone():
            logger.warning(f"TokensTable not found in {db_path}")
            conn.close()
            return False

        # Check which essential columns exist
        cursor.execute("PRAGMA table_info(TokensTable)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Build query for essential fields only
        essential_selects = []
        if 'did' in existing_columns:
            essential_selects.append('did')
        else:
            essential_selects.append("'c not found' as did")

        if 'token_id' in existing_columns:
            essential_selects.append('token_id')
        else:
            essential_selects.append("'c not found' as token_id")

        # Filter by specific token_status values (0,1,2,3,5,9,12,13,14,15,16,17)
        valid_statuses = "(0,1,2,3,5,9,12,13,14,15,16,17)"
        where_clause = f"WHERE token_status IN {valid_statuses}" if 'token_status' in existing_columns else ""

        query = f"SELECT {', '.join(essential_selects)} FROM TokensTable {where_clause}"
        logger.info(f"Essential metadata query: {query}")

        # Read filtered essential data
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            logger.warning(f"No tokens found in {node_name}")
            return True  # Empty database is still "successful"

        logger.info(f"Found {len(rows)} tokens for essential metadata capture")

        # Prepare minimal records for insertion
        essential_records = []
        for row in rows:
            did = safe_str(row[0]) if row[0] else 'c not found'
            token_id = safe_str(row[1]) if row[1] else 'c not found'

            # Create minimal record with essential fields only
            essential_records.append((
                source_ip,           # source_ip
                node_name,          # node_name
                did,                # did
                token_id,           # token_id
                None,               # created_at (NULL)
                None,               # updated_at (NULL)
                'essential_only',   # token_status (marker)
                None,               # parent_token_id (NULL)
                None,               # token_value (NULL)
                None,               # ipfs_data (NULL)
                False,              # ipfs_fetched (False)
                'essential_capture_only',  # ipfs_error (marker)
                db_path,            # db_path
                None,               # ipfs_path (NULL)
                datetime.now(),     # synced_at
                datetime.fromtimestamp(os.path.getmtime(db_path))  # db_last_modified
            ))

        # Insert essential records using existing bulk insert
        if essential_records:
            # Convert to TokenRecord objects for compatibility
            token_records = []
            for record_tuple in essential_records:
                token_record = TokenRecord(
                    source_ip=record_tuple[0],
                    node_name=record_tuple[1],
                    did=record_tuple[2],
                    token_id=record_tuple[3],
                    created_at=record_tuple[4],
                    updated_at=record_tuple[5],
                    token_status=record_tuple[6],
                    parent_token_id=record_tuple[7],
                    token_value=record_tuple[8],
                    ipfs_data=record_tuple[9],
                    ipfs_fetched=record_tuple[10],
                    ipfs_error=record_tuple[11],
                    db_path=record_tuple[12],
                    ipfs_path=record_tuple[13],
                    db_last_modified=record_tuple[15]
                )
                token_records.append(token_record)

            # Use intelligent MERGE to preserve IPFS data and avoid duplicates
            success_count, error_count = bulk_insert_essential_records(token_records)

            logger.info(f"Essential metadata MERGE: {success_count} processed, {error_count} errors (IPFS data preserved)")

            audit_logger.log_with_context(
                logger, logging.INFO,
                f"Essential metadata MERGE for {node_name}: {success_count} records (IPFS preserved)",
                component='ESSENTIAL', operation='METADATA_MERGE',
                extra_data={
                    'node_name': node_name,
                    'db_path': db_path,
                    'tokens_processed': len(rows),
                    'successful_merges': success_count,
                    'failed_merges': error_count,
                    'ipfs_preservation': True,
                    'operation_type': 'MERGE with deduplication'
                }
            )

            return error_count == 0

        return True

    except Exception as e:
        logger.error(f"Failed to ensure essential metadata for {db_path}: {e}")
        audit_logger.log_with_context(
            logger, logging.ERROR,
            f"Essential metadata capture failed: {e}",
            component='ESSENTIAL', operation='METADATA_CAPTURE',
            extra_data={'db_path': db_path, 'error': str(e)},
            exc_info=True
        )
        return False


def run_essential_metadata_capture() -> bool:
    """
    Run essential metadata capture for all databases.
    This is a lightweight alternative to full sync that captures only
    core fields (token_id, did, source_ip, node_name) without IPFS processing.

    Returns:
        bool: True if all essential metadata was captured successfully
    """
    try:
        print("🔍 Initializing essential metadata capture...")

        # Get public IP
        source_ip = get_public_ip()
        print(f"📡 Source IP: {source_ip}")

        # Initialize connection pool
        init_connection_pool()
        print("🔗 Database connection established")

        # Create tables if needed
        create_azure_sql_tables()
        print("📊 Database tables ready")

        # Find all databases
        # Dynamic search path based on executable location
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Bundled executable - search from executable's parent directory
            search_path = str(Path(sys.executable).parent)
        else:
            # Python script - use original logic for development
            search_path = os.path.join('..', 'Node') if os.path.exists('../Node') else '..'

        databases = find_rubix_databases(search_path)

        if not databases:
            print("❌ No rubix.db files found")
            return False

        print(f"📁 Found {len(databases)} database files")

        # Process each database for essential metadata
        successful_count = 0
        failed_count = 0

        print("🔄 Processing databases for essential metadata with IPFS preservation...")
        print(f"{'Node':<20} {'Status':<15} {'Records':<10} {'Result'}")
        print("-" * 60)

        for idx, (db_path, _) in enumerate(databases, 1):
            node_name = extract_node_name(db_path)

            try:
                # Show progress
                progress = (idx / len(databases)) * 100
                print(f"[{progress:5.1f}%] Processing {node_name}...", end=" ", flush=True)

                # Capture essential metadata
                success = ensure_essential_metadata(db_path, source_ip, force_update=False)

                if success:
                    print(f"✅ Success")
                    successful_count += 1
                else:
                    print(f"❌ Failed")
                    failed_count += 1

            except Exception as e:
                print(f"❌ Error: {e}")
                failed_count += 1

        # Summary
        print("\n" + "=" * 60)
        print("📊 Essential Metadata Capture Summary:")
        print(f"   ✅ Successful: {successful_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   📊 Total: {len(databases)}")
        print(f"   🎯 Success Rate: {(successful_count/len(databases)*100):.1f}%")

        if failed_count == 0:
            print("\n🎉 All databases processed successfully!")
            print("💾 Essential metadata (token_id, did, source_ip, node_name) captured with IPFS preservation")
            print("🔄 MERGE logic ensures no duplicates and preserves existing IPFS data")
            return True
        else:
            print(f"\n⚠️  {failed_count} databases had issues - check logs for details")
            print("✅ MERGE logic preserved existing IPFS data for successful records")
            return successful_count > 0  # Return True if at least some succeeded

    except Exception as e:
        print(f"❌ Essential metadata capture failed: {e}")
        logger.error(f"Essential metadata capture failed: {e}", exc_info=True)
        return False
    finally:
        # Close connection pool
        if 'connection_pool' in globals() and connection_pool:
            try:
                connection_pool.close()
                print("🔒 Database connections closed")
            except:
                pass


def create_azure_sql_tables():
    """Create TokenRecords and ProcessedDatabases tables in Azure SQL Database with optimized schema."""
    pool = init_connection_pool()

    # Debug: Log the connection string being used by the pool
    logger.info(f"Pool connection string: {pool.connection_string}")

    conn = pool.get_connection()

    try:
        cursor = conn.cursor()

        # Create TokenRecords table with Azure SQL optimized schema
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TokenRecords]') AND type in (N'U'))
            BEGIN
                CREATE TABLE [dbo].[TokenRecords] (
                    [id] BIGINT IDENTITY(1,1) PRIMARY KEY,
                    [source_ip] NVARCHAR(45) NOT NULL,
                    [node_name] NVARCHAR(255) NOT NULL,
                    [did] NVARCHAR(1000) NULL,
                    [token_id] NVARCHAR(500) NULL,
                    [created_at] DATETIME2(7) NULL,
                    [updated_at] DATETIME2(7) NULL,
                    [token_status] NVARCHAR(50) NULL,
                    [parent_token_id] NVARCHAR(500) NULL,
                    [token_value] NVARCHAR(MAX) NULL,
                    [ipfs_data] NVARCHAR(MAX) NULL,
                    [ipfs_fetched] BIT DEFAULT 0,
                    [ipfs_error] NVARCHAR(1000) NULL,
                    [db_path] NVARCHAR(500) NOT NULL,
                    [ipfs_path] NVARCHAR(500) NULL,
                    [db_last_modified] DATETIME2(7) NOT NULL,
                    [synced_at] DATETIME2(7) DEFAULT GETUTCDATE(),
                    [validation_errors] NVARCHAR(MAX) NULL
                )
            END
        """)

        # Create optimized indexes for Azure SQL Database
        indexes = [
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_TokenRecords_token_id') CREATE INDEX IX_TokenRecords_token_id ON [dbo].[TokenRecords] ([token_id]) INCLUDE ([did], [ipfs_fetched])",
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_TokenRecords_did') CREATE INDEX IX_TokenRecords_did ON [dbo].[TokenRecords] ([did]) INCLUDE ([token_id], [node_name])",
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_TokenRecords_node_name') CREATE INDEX IX_TokenRecords_node_name ON [dbo].[TokenRecords] ([node_name]) INCLUDE ([source_ip], [synced_at])",
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_TokenRecords_source_ip') CREATE INDEX IX_TokenRecords_source_ip ON [dbo].[TokenRecords] ([source_ip])",
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_TokenRecords_db_path') CREATE INDEX IX_TokenRecords_db_path ON [dbo].[TokenRecords] ([db_path])",
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_TokenRecords_ipfs_fetched') CREATE INDEX IX_TokenRecords_ipfs_fetched ON [dbo].[TokenRecords] ([ipfs_fetched]) INCLUDE ([ipfs_error])",
            "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_TokenRecords_synced_at') CREATE INDEX IX_TokenRecords_synced_at ON [dbo].[TokenRecords] ([synced_at]) INCLUDE ([node_name], [source_ip])"
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        # Create ProcessedDatabases metadata table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ProcessedDatabases]') AND type in (N'U'))
            BEGIN
                CREATE TABLE [dbo].[ProcessedDatabases] (
                    [db_path] NVARCHAR(500) PRIMARY KEY,
                    [last_modified] DATETIME2(7) NOT NULL,
                    [last_processed] DATETIME2(7) NOT NULL,
                    [record_count] INT DEFAULT 0,
                    [ipfs_success_count] INT DEFAULT 0,
                    [ipfs_fail_count] INT DEFAULT 0,
                    [validation_error_count] INT DEFAULT 0,
                    [processing_duration_seconds] FLOAT DEFAULT 0
                )
            END
        """)

        # Create SyncSessions table for tracking sync runs
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[SyncSessions]') AND type in (N'U'))
            BEGIN
                CREATE TABLE [dbo].[SyncSessions] (
                    [session_id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    [start_time] DATETIME2(7) DEFAULT GETUTCDATE(),
                    [end_time] DATETIME2(7) NULL,
                    [source_ip] NVARCHAR(45) NOT NULL,
                    [total_databases_found] INT DEFAULT 0,
                    [total_databases_processed] INT DEFAULT 0,
                    [total_records_processed] INT DEFAULT 0,
                    [total_ipfs_success] INT DEFAULT 0,
                    [total_ipfs_failures] INT DEFAULT 0,
                    [total_sql_inserts] INT DEFAULT 0,
                    [total_sql_errors] INT DEFAULT 0,
                    [total_validation_errors] INT DEFAULT 0,
                    [status] NVARCHAR(20) DEFAULT 'RUNNING',
                    [error_summary] NVARCHAR(MAX) NULL
                )
            END
        """)

        conn.commit()
        cursor.close()
        logger.info("Azure SQL Database tables and indexes created successfully")

    except Exception as e:
        logger.error(f"Error creating Azure SQL tables: {e}")
        sync_metrics.add_error("database", f"Failed to create tables: {e}")
        raise
    finally:
        pool.return_connection(conn)


def get_processed_databases() -> Dict[str, float]:
    """Get dictionary of already processed databases and their last_modified timestamps."""
    pool = init_connection_pool()
    conn = pool.get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT [db_path], DATEDIFF(SECOND, '1970-01-01', [last_modified])
            FROM [dbo].[ProcessedDatabases]
        """)

        processed = {row[0]: float(row[1]) for row in cursor.fetchall()}
        cursor.close()
        return processed

    except Exception as e:
        logger.error(f"Error getting processed databases: {e}")
        sync_metrics.add_error("database", f"Failed to get processed databases: {e}")
        return {}
    finally:
        pool.return_connection(conn)


def needs_processing(db_path: str, db_last_modified: float, processed_dbs: Dict[str, float]) -> bool:
    """Check if a database needs to be processed based on last_modified timestamp."""
    if db_path not in processed_dbs:
        return True
    return db_last_modified > processed_dbs[db_path]


def process_database_incremental(db_path: str, db_last_modified: float, source_ip: str, script_dir: str, ipfs_mapping: Dict[str, str]) -> bool:
    """
    Process a single database with incremental 1000-record batches for resilience.
    Processes IPFS and inserts to database in small batches to avoid timeouts and ensure progress is saved.

    Args:
        db_path: Path to the SQLite database
        db_last_modified: Last modified timestamp of the database
        source_ip: Source IP address for audit tracking
        script_dir: Script directory path
        ipfs_mapping: Pre-built mapping of database paths to .ipfs directories

    Returns:
        bool: True if processing completed successfully
    """
    try:
        # Extract node name and get pre-mapped IPFS directory and binary
        node_name = extract_node_name(db_path)
        ipfs_path = ipfs_mapping.get(db_path)

        # Find IPFS binary for this specific node
        ipfs_binary = find_node_ipfs_binary(db_path)

        logger.info(f"🔄 Starting incremental processing for {node_name}: {db_path}")
        if ipfs_path:
            logger.info(f"  📁 IPFS path: {ipfs_path}")
        else:
            logger.warning(f"  ⚠️  No IPFS path found for {node_name}")

        if ipfs_binary:
            logger.info(f"  🔧 IPFS binary: {ipfs_binary}")
        else:
            logger.warning(f"  ⚠️  No IPFS binary found for {node_name}, using global fallback")

        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if TokensTable exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='TokensTable'
        """)

        if not cursor.fetchone():
            logger.warning(f"TokensTable not found in {db_path}")
            conn.close()
            return False

        # Check which columns exist in TokensTable
        cursor.execute("PRAGMA table_info(TokensTable)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Build dynamic query with missing column handling
        column_selects = []
        expected_columns = ['did', 'token_id', 'created_at', 'updated_at', 'token_status', 'parent_token_id', 'token_value']

        for col in expected_columns:
            if col in existing_columns:
                column_selects.append(col)
            else:
                column_selects.append(f"'c not found' as {col}")

        # Filter by specific token_status values (0,1,2,3,5,9,12,13,14,15,16,17)
        valid_statuses = "(0,1,2,3,5,9,12,13,14,15,16,17)"
        where_clause = f"WHERE token_status IN {valid_statuses}" if 'token_status' in existing_columns else ""

        query = f"SELECT {', '.join(column_selects)} FROM TokensTable {where_clause}"
        logger.info(f"  📊 SQLite query for {node_name}: {query}")

        # Read filtered tokens with dynamic column handling
        cursor.execute(query)
        token_rows = cursor.fetchall()
        conn.close()

        total_tokens = len(token_rows)
        logger.info(f"  📦 Found {total_tokens:,} tokens in {node_name}")

        if not token_rows:
            logger.info(f"  ✅ No tokens to process in {node_name}")
            return True

        # Process in incremental batches of 1000
        batch_size = 1000
        total_batches = (total_tokens + batch_size - 1) // batch_size
        successful_batches = 0
        total_processed = 0
        total_ipfs_success = 0
        total_ipfs_fail = 0

        logger.info(f"  🔢 Processing {total_tokens:,} tokens in {total_batches} batches of {batch_size}")

        # Track overall processing start time for accurate ETA calculation
        processing_start_time = time.time()

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_tokens)
            batch_tokens = token_rows[start_idx:end_idx]

            batch_start_time = time.time()
            logger.info(f"  📋 Batch {batch_idx + 1}/{total_batches}: Processing tokens {start_idx + 1}-{end_idx}")

            try:
                # Prepare arguments for parallel processing of this batch
                args_list = [
                    (row, source_ip, node_name, db_path, ipfs_path, ipfs_binary, db_last_modified, script_dir)
                    for row in batch_tokens
                ]

                # Process IPFS for this batch in parallel
                logger.info(f"    🔄 Fetching IPFS data for {len(batch_tokens)} tokens...")
                with Pool(processes=NUM_IPFS_WORKERS) as pool:
                    batch_records = pool.map(process_token_ipfs, args_list)

                # Count batch IPFS successes and failures
                batch_ipfs_success = sum(1 for r in batch_records if r.ipfs_fetched)
                batch_ipfs_fail = len(batch_records) - batch_ipfs_success

                logger.info(f"    📈 IPFS results: {batch_ipfs_success} succeeded, {batch_ipfs_fail} failed")

                # Immediately insert this batch to database
                if batch_records:
                    logger.info(f"    💾 Inserting batch {batch_idx + 1} to database...")
                    success_count, error_count = bulk_insert_records(batch_records)

                    if error_count == 0:
                        logger.info(f"    ✅ Batch {batch_idx + 1} inserted successfully: {success_count} records")
                        successful_batches += 1
                        total_processed += len(batch_tokens)
                        total_ipfs_success += batch_ipfs_success
                        total_ipfs_fail += batch_ipfs_fail
                    else:
                        logger.error(f"    ❌ Batch {batch_idx + 1} insertion failed: {error_count} errors out of {len(batch_records)} records")
                        print(f"    ❌ Batch {batch_idx + 1} insertion failed: {error_count} errors", flush=True)
                        # Continue processing remaining batches even if one fails

                batch_time = time.time() - batch_start_time
                remaining_batches = total_batches - (batch_idx + 1)
                eta_minutes = (remaining_batches * batch_time) / 60 if batch_time > 0 else 0

                # Visual progress bar
                progress_pct = ((batch_idx + 1) / total_batches) * 100
                bar_width = 30
                filled_width = int(bar_width * progress_pct / 100)
                bar = "█" * filled_width + "░" * (bar_width - filled_width)

                # Calculate processing rate
                total_time_elapsed = time.time() - processing_start_time
                if total_time_elapsed > 0 and total_processed > 0:
                    avg_rate = total_processed / total_time_elapsed
                else:
                    avg_rate = len(batch_tokens) / batch_time if batch_time > 0 else 0

                print(f"    [{bar}] {progress_pct:5.1f}% | "
                      f"Batch {batch_idx + 1}/{total_batches} | "
                      f"Processed: {total_processed:,}/{total_tokens:,} | "
                      f"Rate: {avg_rate:,.0f}/s | "
                      f"ETA: {eta_minutes:.1f}m | "
                      f"IPFS: {batch_ipfs_success}/{len(batch_tokens)}", flush=True)

                logger.info(f"    ⏱️  Batch {batch_idx + 1} completed in {batch_time:.1f}s | Progress: {progress_pct:.1f}% | ETA: {eta_minutes:.1f}m")

            except Exception as batch_error:
                logger.error(f"    ❌ Batch {batch_idx + 1} failed: {batch_error}")
                logger.info(f"    🔄 Continuing with next batch...")
                continue

        # Summary for this database
        success_rate = (successful_batches / total_batches) * 100 if total_batches > 0 else 0
        logger.info(f"  📊 {node_name} Summary:")
        logger.info(f"    ✅ Successful batches: {successful_batches}/{total_batches} ({success_rate:.1f}%)")
        logger.info(f"    📦 Total tokens processed: {total_processed:,}/{total_tokens:,}")
        logger.info(f"    🔗 IPFS success: {total_ipfs_success:,}, failed: {total_ipfs_fail:,}")

        # Also print summary to console for user visibility
        print(f"\n✅ {node_name} Complete: {total_processed:,}/{total_tokens:,} tokens | "
              f"IPFS: {total_ipfs_success:,} success, {total_ipfs_fail:,} failed | "
              f"Success Rate: {success_rate:.1f}%\n", flush=True)

        # Update processed database metadata
        update_processed_database(
            db_path, db_last_modified, total_processed,
            total_ipfs_success, total_ipfs_fail, 0,
            time.time() - batch_start_time
        )

        # Consider success if we processed at least 80% of batches
        return success_rate >= 80.0

    except sqlite3.Error as e:
        logger.error(f"SQLite error reading {db_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing {db_path}: {e}")

        # Fallback: Ensure essential metadata is captured even if processing failed
        logger.info(f"Attempting essential metadata capture as fallback for {db_path}")
        if ensure_essential_metadata(db_path, source_ip):
            logger.info(f"Essential metadata captured successfully as fallback for {extract_node_name(db_path)}")
        else:
            logger.error(f"Failed to capture essential metadata for {extract_node_name(db_path)}")

        return False


def process_database(db_path: str, db_last_modified: float, source_ip: str, script_dir: str, ipfs_mapping: Dict[str, str]) -> List[Tuple]:
    """
    Legacy process_database function - kept for compatibility.
    NEW: Use process_database_incremental() for better resilience.

    Process a single database: read tokens from SQLite and fetch IPFS data.
    Uses pre-mapped IPFS paths for efficiency.

    Args:
        db_path: Path to the SQLite database
        db_last_modified: Last modified timestamp of the database
        source_ip: Source IP address for audit tracking
        script_dir: Script directory path
        ipfs_mapping: Pre-built mapping of database paths to .ipfs directories

    Returns:
        List of records ready for Azure SQL insertion
    """
    try:
        # Extract node name and get pre-mapped IPFS directory and binary
        node_name = extract_node_name(db_path)
        ipfs_path = ipfs_mapping.get(db_path)

        # Find IPFS binary for this specific node
        ipfs_binary = find_node_ipfs_binary(db_path)

        logger.info(f"Processing {node_name}: {db_path}")
        if ipfs_path:
            logger.info(f"  IPFS path: {ipfs_path}")
        else:
            logger.warning(f"  No IPFS path found for {node_name}")

        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if TokensTable exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='TokensTable'
        """)

        if not cursor.fetchone():
            logger.warning(f"TokensTable not found in {db_path}")
            conn.close()
            return []

        # Check which columns exist in TokensTable
        cursor.execute("PRAGMA table_info(TokensTable)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Build dynamic query with missing column handling
        column_selects = []
        expected_columns = ['did', 'token_id', 'created_at', 'updated_at', 'token_status', 'parent_token_id', 'token_value']

        for col in expected_columns:
            if col in existing_columns:
                column_selects.append(col)
            else:
                column_selects.append(f"'c not found' as {col}")

        # Filter by specific token_status values (0,1,2,3,5,9,12,13,14,15,16,17)
        valid_statuses = "(0,1,2,3,5,9,12,13,14,15,16,17)"
        where_clause = f"WHERE token_status IN {valid_statuses}" if 'token_status' in existing_columns else ""

        query = f"SELECT {', '.join(column_selects)} FROM TokensTable {where_clause}"
        logger.info(f"  SQLite query for {node_name}: {query}")

        # Read filtered tokens with dynamic column handling
        cursor.execute(query)

        token_rows = cursor.fetchall()
        conn.close()

        logger.info(f"  Found {len(token_rows)} tokens in {node_name}")

        if not token_rows:
            return []

        # Prepare arguments for parallel processing
        args_list = [
            (row, source_ip, node_name, db_path, ipfs_path, ipfs_binary, db_last_modified, script_dir)
            for row in token_rows
        ]

        # Process tokens in parallel (IPFS calls)
        logger.info(f"  Fetching IPFS data for {len(token_rows)} tokens using {NUM_IPFS_WORKERS} workers...")

        with Pool(processes=NUM_IPFS_WORKERS) as pool:
            records = pool.map(process_token_ipfs, args_list)

        # Count IPFS successes and failures
        ipfs_success = sum(1 for r in records if r.ipfs_fetched)
        ipfs_fail = len(records) - ipfs_success
        validation_errors = sum(1 for r in records if r.validation_errors)

        logger.info(f"  IPFS fetch: {ipfs_success} succeeded, {ipfs_fail} failed")
        if validation_errors > 0:
            logger.warning(f"  Validation errors: {validation_errors}")

        return records

    except sqlite3.Error as e:
        logger.error(f"SQLite error reading {db_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error processing {db_path}: {e}")

        # Fallback: Ensure essential metadata is captured even if processing failed
        logger.info(f"Attempting essential metadata capture as fallback for {db_path}")
        if ensure_essential_metadata(db_path, source_ip):
            logger.info(f"Essential metadata captured successfully as fallback for {extract_node_name(db_path)}")
        else:
            logger.error(f"Failed to capture essential metadata for {extract_node_name(db_path)}")

        return []


def bulk_insert_records(records: List[TokenRecord]) -> Tuple[int, int]:
    """
    Optimized bulk insert for Azure SQL Database with comprehensive transaction logging.
    Returns tuple of (success_count, error_count)
    """
    if not records:
        return 0, 0

    operation_start = time.time()

    with OperationContext(f"BULK_INSERT_{len(records)}_RECORDS", 'SQL', sql_logger):
        pool = init_connection_pool()
        conn = pool.get_connection()
        success_count = 0
        error_count = 0

        try:
            # Log operation start
            audit_logger.log_with_context(
                sql_logger, logging.INFO,
                f"Starting bulk insert for {len(records)} records",
                component='SQL', operation='BULK_INSERT',
                extra_data={
                    'record_count': len(records),
                    'batch_threshold': BULK_INSERT_SIZE,
                    'connection_pool_size': CONNECTION_POOL_SIZE
                }
            )

            # Convert records to DataFrame for bulk operations
            data = []
            validation_error_count = 0
            ipfs_success_count = 0

            for record in records:
                validation_errors_json = json.dumps(record.validation_errors) if record.validation_errors else None
                if record.validation_errors:
                    validation_error_count += 1
                if record.ipfs_fetched:
                    ipfs_success_count += 1

                data.append([
                    record.source_ip,
                    record.node_name,
                    record.did,
                    record.token_id,
                    record.created_at,
                    record.updated_at,
                    record.token_status,
                    record.parent_token_id,
                    record.token_value,
                    record.ipfs_data,
                    record.ipfs_fetched,
                    record.ipfs_error,
                    record.db_path,
                    record.ipfs_path,
                    record.db_last_modified,
                    validation_errors_json
                ])

            # Log data preparation metrics
            prep_time = time.time() - operation_start
            audit_logger.log_with_context(
                sql_logger, logging.DEBUG,
                "Data preparation completed",
                component='SQL', operation='BULK_INSERT',
                extra_data={
                    'preparation_time_ms': prep_time * 1000,
                    'validation_errors': validation_error_count,
                    'ipfs_success': ipfs_success_count,
                    'data_rows': len(data)
                }
            )

            # Use parameterized query with fast_executemany for optimal performance
            cursor = conn.cursor()
            cursor.fast_executemany = True

            # Set shorter timeout for large operations to prevent network hangs
            conn.timeout = 300  # 5 minutes timeout

            insert_query = """
                INSERT INTO [dbo].[TokenRecords]
                ([source_ip], [node_name], [did], [token_id], [created_at], [updated_at],
                 [token_status], [parent_token_id], [token_value], [ipfs_data], [ipfs_fetched],
                 [ipfs_error], [db_path], [ipfs_path], [db_last_modified], [validation_errors])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Process in smaller chunks to prevent Azure SQL timeout
            chunk_size = min(1000, len(data))  # Maximum 1000 records per chunk
            total_inserted = 0

            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                chunk_start = time.time()

                # Retry logic for network failures
                for attempt in range(RETRY_ATTEMPTS):
                    try:
                        cursor.executemany(insert_query, chunk)
                        conn.commit()  # Commit each chunk
                        total_inserted += len(chunk)

                        audit_logger.log_with_context(
                            sql_logger, logging.DEBUG,
                            f"Chunk {i//chunk_size + 1} inserted: {len(chunk)} records",
                            component='SQL', operation='BULK_INSERT',
                            extra_data={
                                'chunk_size': len(chunk),
                                'total_progress': total_inserted,
                                'chunk_time_ms': (time.time() - chunk_start) * 1000
                            }
                        )
                        break  # Success, exit retry loop

                    except pyodbc.OperationalError as e:
                        if "Communication link failure" in str(e) and attempt < RETRY_ATTEMPTS - 1:
                            audit_logger.log_with_context(
                                sql_logger, logging.WARNING,
                                f"Network failure on chunk {i//chunk_size + 1}, attempt {attempt + 1}/{RETRY_ATTEMPTS}: {e}",
                                component='SQL', operation='BULK_INSERT'
                            )

                            # Wait before retry with exponential backoff
                            time.sleep(2 ** attempt)

                            # Reconnect to database
                            try:
                                pool.return_connection(conn)
                                conn = pool.get_connection()
                                cursor = conn.cursor()
                                cursor.fast_executemany = True
                                conn.timeout = 300
                            except Exception as reconnect_error:
                                audit_logger.log_with_context(
                                    sql_logger, logging.ERROR,
                                    f"Failed to reconnect: {reconnect_error}",
                                    component='SQL', operation='RECONNECT'
                                )
                                raise
                        else:
                            raise  # Re-raise if max attempts reached or different error

            execute_time = time.time() - operation_start

            # No final commit needed - each chunk was committed individually
            commit_time = 0

            success_count = total_inserted

            # Update metrics
            sync_metrics.total_sql_inserts += success_count

            # Log successful operation
            total_duration = time.time() - operation_start
            log_database_operation(
                'BULK_INSERT',
                insert_query,
                params=data,
                affected_rows=success_count,
                duration=total_duration,
                success=True
            )

            # Log performance metrics
            audit_logger.log_with_context(
                sql_logger, logging.INFO,
                f"Bulk insert completed successfully: {success_count} records",
                component='SQL', operation='BULK_INSERT',
                extra_data={
                    'total_duration_ms': total_duration * 1000,
                    'execute_time_ms': execute_time * 1000,
                    'commit_time_ms': commit_time * 1000,
                    'records_per_second': success_count / total_duration,
                    'validation_errors': validation_error_count,
                    'ipfs_success_rate': (ipfs_success_count / len(records)) * 100
                }
            )

        except Exception as e:
            error_duration = time.time() - operation_start
            error_msg = str(e)

            # Log the error with full context
            log_database_operation(
                'BULK_INSERT',
                insert_query if 'insert_query' in locals() else 'N/A',
                params=[],
                affected_rows=0,
                duration=error_duration,
                success=False,
                error=e
            )

            sync_metrics.add_error("database", f"Bulk insert failed: {error_msg}", {
                "record_count": len(records),
                "error_type": type(e).__name__,
                "duration_ms": error_duration * 1000
            })
            sync_metrics.total_sql_errors += len(records)
            error_count = len(records)

            try:
                conn.rollback()
                audit_logger.log_with_context(
                    sql_logger, logging.INFO,
                    "Transaction rolled back successfully",
                    component='SQL', operation='ROLLBACK'
                )
            except Exception as rollback_error:
                audit_logger.log_with_context(
                    sql_logger, logging.ERROR,
                    f"Rollback failed: {rollback_error}",
                    component='SQL', operation='ROLLBACK',
                    exc_info=True
                )

            # Try individual inserts as fallback
            audit_logger.log_with_context(
                sql_logger, logging.WARNING,
                "Attempting fallback to individual inserts",
                component='SQL', operation='FALLBACK_INSERT'
            )
            success_count, error_count = fallback_individual_inserts(records)

        finally:
            pool.return_connection(conn)

    return success_count, error_count

def fallback_individual_inserts(records: List[TokenRecord]) -> Tuple[int, int]:
    """Fallback to individual inserts when bulk insert fails"""
    pool = init_connection_pool()
    success_count = 0
    error_count = 0

    insert_query = """
        INSERT INTO [dbo].[TokenRecords]
        ([source_ip], [node_name], [did], [token_id], [created_at], [updated_at],
         [token_status], [parent_token_id], [token_value], [ipfs_data], [ipfs_fetched],
         [ipfs_error], [db_path], [ipfs_path], [db_last_modified], [validation_errors])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for record in records:
        conn = pool.get_connection()
        try:
            cursor = conn.cursor()
            validation_errors_json = json.dumps(record.validation_errors) if record.validation_errors else None

            cursor.execute(insert_query, [
                record.source_ip, record.node_name, record.did, record.token_id,
                record.created_at, record.updated_at, record.token_status,
                record.parent_token_id, record.token_value, record.ipfs_data,
                record.ipfs_fetched, record.ipfs_error, record.db_path,
                record.ipfs_path, record.db_last_modified, validation_errors_json
            ])

            conn.commit()
            success_count += 1

        except Exception as e:
            error_count += 1
            sync_metrics.add_error("database", f"Individual insert failed: {e}",
                                 {"token_id": record.token_id, "node_name": record.node_name})
            try:
                conn.rollback()
            except:
                pass

        finally:
            pool.return_connection(conn)

    logger.info(f"  Fallback inserts: {success_count} succeeded, {error_count} failed")
    return success_count, error_count


def bulk_insert_essential_records(records: List[TokenRecord]) -> Tuple[int, int]:
    """
    Intelligent bulk insert/update for essential metadata with IPFS data preservation.
    Uses MERGE logic to handle deduplication while preserving existing IPFS data.

    Args:
        records: List of TokenRecord objects with essential metadata

    Returns:
        tuple: (success_count, error_count)
    """
    if not records:
        return 0, 0

    operation_start = time.time()

    with OperationContext(f"ESSENTIAL_MERGE_{len(records)}_RECORDS", 'SQL', sql_logger):
        pool = init_connection_pool()
        conn = pool.get_connection()
        success_count = 0
        error_count = 0

        try:
            # Log operation start
            audit_logger.log_with_context(
                sql_logger, logging.INFO,
                f"Starting essential metadata MERGE for {len(records)} records",
                component='SQL', operation='ESSENTIAL_MERGE',
                extra_data={
                    'record_count': len(records),
                    'operation_type': 'MERGE with IPFS preservation'
                }
            )

            cursor = conn.cursor()

            # Process records in batches for better performance
            batch_size = 1000
            total_processed = 0

            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                batch_start = time.time()

                # Prepare batch data for MERGE operation
                batch_data = []
                for record in batch:
                    batch_data.append([
                        record.source_ip,
                        record.node_name,
                        record.did or 'c not found',
                        record.token_id or 'c not found',
                        record.db_path,
                        record.ipfs_data,
                        record.ipfs_fetched,
                        record.ipfs_error or 'essential_capture_only',
                        record.token_status or 'essential_only',
                        record.db_last_modified
                    ])

                # Execute MERGE with IPFS data preservation
                merge_query = """
                    MERGE [dbo].[TokenRecords] AS target
                    USING (SELECT
                        ? AS source_ip, ? AS node_name, ? AS did, ? AS token_id, ? AS db_path,
                        ? AS ipfs_data, ? AS ipfs_fetched, ? AS ipfs_error,
                        ? AS token_status, ? AS db_last_modified
                    ) AS source
                    ON target.source_ip = source.source_ip
                       AND target.node_name = source.node_name
                       AND target.token_id = source.token_id

                    WHEN NOT MATCHED THEN
                        -- Insert new record (may have IPFS data from source)
                        INSERT (source_ip, node_name, did, token_id, db_path, ipfs_data,
                               ipfs_fetched, ipfs_error, token_status, db_last_modified, synced_at)
                        VALUES (source.source_ip, source.node_name, source.did, source.token_id,
                               source.db_path, source.ipfs_data, source.ipfs_fetched,
                               source.ipfs_error, source.token_status, source.db_last_modified, GETUTCDATE())

                    WHEN MATCHED THEN
                        UPDATE SET
                            -- Preserve any existing IPFS data, use new data only if existing is empty
                            ipfs_data = CASE
                                WHEN target.ipfs_data IS NOT NULL AND target.ipfs_data != '' THEN target.ipfs_data
                                WHEN source.ipfs_data IS NOT NULL AND source.ipfs_data != '' THEN source.ipfs_data
                                ELSE target.ipfs_data
                            END,

                            -- Update ipfs_fetched if we have new successful IPFS data
                            ipfs_fetched = CASE
                                WHEN target.ipfs_fetched = 1 THEN 1  -- Keep existing success
                                WHEN source.ipfs_fetched = 1 THEN 1  -- Use new success
                                ELSE target.ipfs_fetched
                            END,

                            -- Update ipfs_error intelligently
                            ipfs_error = CASE
                                WHEN target.ipfs_fetched = 1 THEN target.ipfs_error  -- Keep error from successful fetch
                                WHEN source.ipfs_fetched = 1 THEN source.ipfs_error  -- Use error from new successful fetch
                                WHEN target.ipfs_error IS NOT NULL AND target.ipfs_error != 'essential_capture_only' THEN target.ipfs_error
                                ELSE source.ipfs_error
                            END,

                            -- Always update essential metadata to latest
                            did = COALESCE(source.did, target.did),
                            db_path = COALESCE(source.db_path, target.db_path),
                            token_status = CASE
                                WHEN target.ipfs_fetched = 1 THEN target.token_status  -- Keep status if IPFS successful
                                ELSE COALESCE(source.token_status, target.token_status)
                            END,
                            db_last_modified = COALESCE(source.db_last_modified, target.db_last_modified),
                            synced_at = GETUTCDATE();
                """

                # Execute MERGE for each record in batch
                for record_data in batch_data:
                    try:
                        cursor.execute(merge_query, record_data)
                        success_count += 1
                    except Exception as record_error:
                        error_count += 1
                        audit_logger.log_with_context(
                            sql_logger, logging.WARNING,
                            f"Failed to merge essential record: {record_error}",
                            component='SQL', operation='ESSENTIAL_MERGE',
                            extra_data={
                                'error': str(record_error),
                                'record_data': record_data[:4]  # source_ip, node_name, did, token_id
                            }
                        )

                # Commit batch
                conn.commit()
                total_processed += len(batch)
                batch_time = time.time() - batch_start

                # Log batch progress
                audit_logger.log_with_context(
                    sql_logger, logging.DEBUG,
                    f"Essential MERGE batch completed: {len(batch)} records",
                    component='SQL', operation='ESSENTIAL_MERGE',
                    extra_data={
                        'batch_size': len(batch),
                        'batch_time_ms': batch_time * 1000,
                        'total_processed': total_processed,
                        'records_per_second': len(batch) / batch_time
                    }
                )

            # Log successful operation
            total_duration = time.time() - operation_start

            audit_logger.log_with_context(
                sql_logger, logging.INFO,
                f"Essential metadata MERGE completed: {success_count} success, {error_count} errors",
                component='SQL', operation='ESSENTIAL_MERGE',
                extra_data={
                    'total_duration_ms': total_duration * 1000,
                    'success_count': success_count,
                    'error_count': error_count,
                    'records_per_second': success_count / total_duration if total_duration > 0 else 0,
                    'total_records': len(records)
                }
            )

        except Exception as e:
            error_duration = time.time() - operation_start
            error_msg = str(e)

            audit_logger.log_with_context(
                sql_logger, logging.ERROR,
                f"Essential metadata MERGE failed: {error_msg}",
                component='SQL', operation='ESSENTIAL_MERGE',
                extra_data={
                    'error': error_msg,
                    'error_type': type(e).__name__,
                    'duration_ms': error_duration * 1000,
                    'record_count': len(records)
                },
                exc_info=True
            )

            try:
                conn.rollback()
                audit_logger.log_with_context(
                    sql_logger, logging.INFO,
                    "Transaction rolled back successfully",
                    component='SQL', operation='ROLLBACK'
                )
            except Exception as rollback_error:
                audit_logger.log_with_context(
                    sql_logger, logging.ERROR,
                    f"Rollback failed: {rollback_error}",
                    component='SQL', operation='ROLLBACK',
                    exc_info=True
                )

            error_count = len(records)

        finally:
            pool.return_connection(conn)

    return success_count, error_count


def update_processed_database(db_path: str, db_last_modified: float, record_count: int,
                               ipfs_success: int, ipfs_fail: int, validation_errors: int = 0,
                               processing_duration: float = 0):
    """Update the ProcessedDatabases table with processing metadata."""
    pool = init_connection_pool()
    conn = pool.get_connection()

    try:
        cursor = conn.cursor()
        db_modified_dt = datetime.fromtimestamp(db_last_modified)

        # Use MERGE for upsert operation in Azure SQL Database
        cursor.execute("""
            MERGE [dbo].[ProcessedDatabases] AS target
            USING (VALUES (?, ?, GETUTCDATE(), ?, ?, ?, ?, ?)) AS source
                ([db_path], [last_modified], [last_processed], [record_count],
                 [ipfs_success_count], [ipfs_fail_count], [validation_error_count], [processing_duration_seconds])
            ON target.[db_path] = source.[db_path]
            WHEN MATCHED THEN
                UPDATE SET
                    [last_modified] = source.[last_modified],
                    [last_processed] = source.[last_processed],
                    [record_count] = source.[record_count],
                    [ipfs_success_count] = source.[ipfs_success_count],
                    [ipfs_fail_count] = source.[ipfs_fail_count],
                    [validation_error_count] = source.[validation_error_count],
                    [processing_duration_seconds] = source.[processing_duration_seconds]
            WHEN NOT MATCHED THEN
                INSERT ([db_path], [last_modified], [last_processed], [record_count],
                       [ipfs_success_count], [ipfs_fail_count], [validation_error_count], [processing_duration_seconds])
                VALUES (source.[db_path], source.[last_modified], source.[last_processed], source.[record_count],
                       source.[ipfs_success_count], source.[ipfs_fail_count], source.[validation_error_count], source.[processing_duration_seconds]);
        """, (db_path, db_modified_dt, record_count, ipfs_success, ipfs_fail, validation_errors, processing_duration))

        conn.commit()
        cursor.close()

    except Exception as e:
        logger.error(f"Error updating processed database metadata: {e}")
        sync_metrics.add_error("database", f"Failed to update metadata: {e}", {"db_path": db_path})
        try:
            conn.rollback()
        except:
            pass
    finally:
        pool.return_connection(conn)

def create_sync_session(source_ip: str) -> str:
    """Create a new sync session and return session ID"""
    pool = init_connection_pool()
    conn = pool.get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO [dbo].[SyncSessions] ([source_ip])
            OUTPUT INSERTED.session_id
            VALUES (?)
        """, (source_ip,))

        session_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return str(session_id)

    except Exception as e:
        logger.error(f"Error creating sync session: {e}")
        sync_metrics.add_error("database", f"Failed to create sync session: {e}")
        return str(datetime.now(timezone.utc).isoformat())
    finally:
        pool.return_connection(conn)

def update_sync_session(session_id: str, metrics: SyncMetrics, status: str = "COMPLETED"):
    """Update sync session with final metrics"""
    pool = init_connection_pool()
    conn = pool.get_connection()

    try:
        cursor = conn.cursor()
        error_summary = json.dumps(metrics.errors[-10:]) if metrics.errors else None  # Last 10 errors

        cursor.execute("""
            UPDATE [dbo].[SyncSessions]
            SET [end_time] = GETUTCDATE(),
                [total_databases_found] = ?,
                [total_databases_processed] = ?,
                [total_records_processed] = ?,
                [total_ipfs_success] = ?,
                [total_ipfs_failures] = ?,
                [total_sql_inserts] = ?,
                [total_sql_errors] = ?,
                [total_validation_errors] = ?,
                [status] = ?,
                [error_summary] = ?
            WHERE [session_id] = ?
        """, (metrics.total_databases_found, metrics.total_databases_processed,
              metrics.total_records_processed, metrics.total_ipfs_success,
              metrics.total_ipfs_failures, metrics.total_sql_inserts,
              metrics.total_sql_errors, metrics.total_validation_errors,
              status, error_summary, session_id))

        conn.commit()
        cursor.close()

    except Exception as e:
        logger.error(f"Error updating sync session: {e}")
        sync_metrics.add_error("database", f"Failed to update sync session: {e}")
    finally:
        pool.return_connection(conn)


def generate_final_report():
    """Generate comprehensive final report with all metrics and recommendations"""
    sync_metrics.end_time = datetime.now(timezone.utc)
    metrics_dict = sync_metrics.to_dict()

    # Write JSON report
    report_file = f"sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w') as f:
            json.dump(metrics_dict, f, indent=2, default=str)
        logger.info(f"Detailed report saved to: {report_file}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")

    # Print executive summary
    logger.info("=" * 80)
    logger.info("EXECUTIVE SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Sync Duration: {metrics_dict.get('duration_seconds', 0):.2f} seconds ({metrics_dict.get('duration_seconds', 0)/60:.1f} minutes)")
    logger.info(f"Processing Rate: {metrics_dict.get('records_per_second', 0):.2f} records/second")
    logger.info(f"Databases Found: {sync_metrics.total_databases_found:,}")
    logger.info(f"Databases Processed: {sync_metrics.total_databases_processed:,}")
    logger.info(f"Total Records: {sync_metrics.total_records_processed:,}")
    logger.info(f"IPFS Success Rate: {metrics_dict.get('ipfs_success_rate', 0):.1f}%")
    logger.info(f"SQL Success Rate: {metrics_dict.get('sql_success_rate', 0):.1f}%")
    logger.info(f"Validation Errors: {sync_metrics.total_validation_errors:,}")

    if sync_metrics.errors:
        logger.warning(f"Total Errors: {len(sync_metrics.errors)}")
        error_types = {}
        for error in sync_metrics.errors[-10:]:  # Show last 10 errors
            error_type = error.get('type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1

        logger.warning("Error breakdown (last 10):")
        for error_type, count in error_types.items():
            logger.warning(f"  {error_type}: {count}")

    logger.info("=" * 80)

def cleanup_ipfs_lock_errors():
    """
    Clean up existing records that have IPFS lock errors to allow retry.
    This will delete records with 'repo.lock' errors so they can be re-processed.
    """
    try:
        conn_str = get_azure_sql_connection_string()
        if not conn_str:
            print("❌ Cannot load Azure SQL connection string")
            return False

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Find records with lock errors
        cursor.execute("""
            SELECT COUNT(*) FROM [dbo].[TokenRecords]
            WHERE [ipfs_error] LIKE '%repo.lock%'
        """)
        lock_error_count = cursor.fetchone()[0]

        if lock_error_count == 0:
            print("✅ No IPFS lock error records found")
            conn.close()
            return True

        print(f"🔍 Found {lock_error_count:,} records with IPFS lock errors", flush=True)
        print("⚠️  These records will be deleted to allow retry", flush=True)
        response = input(f"Delete these records to allow retry? Type 'YES' to confirm: ")

        if response != 'YES':
            print("❌ Cleanup cancelled")
            conn.close()
            return False

        # Delete records with lock errors in batches to avoid timeout
        batch_size = 10000
        total_deleted = 0
        start_time = time.time()

        print(f"🔄 Deleting {lock_error_count:,} records in batches of {batch_size:,}...", flush=True)
        print("📊 Progress monitoring:", flush=True)

        while True:
            batch_start = time.time()

            cursor.execute(f"""
                DELETE TOP ({batch_size}) FROM [dbo].[TokenRecords]
                WHERE [ipfs_error] LIKE '%repo.lock%'
            """)

            deleted_count = cursor.rowcount
            if deleted_count == 0:
                break

            total_deleted += deleted_count
            conn.commit()

            # Calculate progress and timing
            progress_pct = (total_deleted / lock_error_count) * 100
            elapsed_time = time.time() - start_time
            batch_time = time.time() - batch_start

            if total_deleted > 0:
                avg_rate = total_deleted / elapsed_time
                estimated_remaining = (lock_error_count - total_deleted) / avg_rate if avg_rate > 0 else 0
                eta_mins = estimated_remaining / 60
            else:
                eta_mins = 0

            # Progress bar
            bar_width = 30
            filled_width = int(bar_width * progress_pct / 100)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)

            print(f"   [{bar}] {progress_pct:5.1f}% | "
                  f"{total_deleted:,}/{lock_error_count:,} | "
                  f"Rate: {avg_rate:,.0f}/s | "
                  f"ETA: {eta_mins:.1f}m | "
                  f"Batch: {batch_time:.2f}s", flush=True)

            # Small delay to prevent overwhelming the database
            time.sleep(0.1)

        print(f"✅ Successfully deleted {total_deleted:,} records with lock errors", flush=True)
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error cleaning up lock errors: {e}")
        return False


def clear_all_records():
    """Clear all existing TokenRecords to start fresh"""
    try:
        conn_str = get_azure_sql_connection_string()
        if not conn_str:
            print("❌ Cannot load Azure SQL connection string")
            return False

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Get current count
        cursor.execute("SELECT COUNT(*) FROM [dbo].[TokenRecords]")
        current_count = cursor.fetchone()[0]

        if current_count == 0:
            print("✅ No existing records to clear")
            conn.close()
            return True

        # Confirm deletion
        print(f"⚠️  About to delete {current_count:,} existing records")
        response = input("Are you sure? Type 'YES' to confirm: ")

        if response != 'YES':
            print("❌ Deletion cancelled")
            conn.close()
            return False

        # Delete all records
        cursor.execute("DELETE FROM [dbo].[TokenRecords]")
        conn.commit()

        print(f"✅ Successfully deleted {current_count:,} records")
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error clearing records: {e}")
        return False


def main():
    """Main function to orchestrate the distributed token sync with Azure SQL Database."""
    # Start main operation with correlation tracking
    main_correlation_id = audit_logger.start_operation("MAIN_SYNC_OPERATION")

    audit_logger.log_with_context(
        logger, logging.INFO, "=" * 80,
        component='MAIN', operation='STARTUP'
    )
    # Show startup message on console
    print("🚀 Starting Distributed Token Sync Service (Azure SQL Database + IPFS)")
    print("=" * 80)

    audit_logger.log_with_context(
        logger, logging.INFO, "Starting Distributed Token Sync Service (Azure SQL Database + IPFS)",
        component='MAIN', operation='STARTUP',
        extra_data={
            'version': '2.0',
            'azure_sql_enabled': True,
            'detailed_logging_enabled': True,
            'correlation_id': main_correlation_id
        }
    )
    audit_logger.log_with_context(
        logger, logging.INFO, "=" * 80,
        component='MAIN', operation='STARTUP'
    )

    session_id = None
    global connection_pool

    with OperationContext("DISTRIBUTED_TOKEN_SYNC", 'MAIN', logger):
        try:
            # Get script directory (where ipfs executable should be)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            audit_logger.log_with_context(
                logger, logging.INFO, f"Script directory: {script_dir}",
                component='MAIN', operation='INITIALIZATION',
                extra_data={'script_directory': script_dir}
            )

            # IPFS executable check already done during import - using smart detection
            audit_logger.log_with_context(
                logger, logging.INFO, f"Using IPFS binary: {IPFS_COMMAND}",
                component='MAIN', operation='IPFS_CHECK',
                extra_data={'ipfs_command': IPFS_COMMAND}
            )

            # Note: IPFS_PATH is set per-node dynamically - each folder has its own .ipfs
            audit_logger.log_with_context(
                logger, logging.INFO, "Using per-node IPFS_PATH detection (each folder has dedicated .ipfs)",
                component='MAIN', operation='IPFS_PATH_SETUP'
            )

            # Get public IP and initialize connection pool
            with OperationContext("GET_PUBLIC_IP", 'MAIN', logger, log_start=False):
                source_ip = get_public_ip()

            # Initialize Telegram notifications
            with OperationContext("INIT_TELEGRAM", 'MAIN', logger, log_start=False):
                telegram_enabled = initialize_telegram_notifications()

            with OperationContext("INIT_CONNECTION_POOL", 'MAIN', logger):
                init_connection_pool()

            # Send startup notification
            if telegram_enabled:
                try:
                    notify_startup("Distributed Token Sync - Azure SQL Database")
                except Exception as e:
                    logger.warning(f"Failed to send startup notification: {e}")

            # Create Azure SQL Database tables
            with OperationContext("CREATE_AZURE_SQL_TABLES", 'MAIN', logger):
                create_azure_sql_tables()

            # Create sync session for tracking
            with OperationContext("CREATE_SYNC_SESSION", 'MAIN', logger, log_start=False):
                session_id = create_sync_session(source_ip)
                audit_logger.log_with_context(
                    logger, logging.INFO, f"Started sync session: {session_id}",
                    component='MAIN', operation='SESSION_START',
                    extra_data={'session_id': session_id, 'source_ip': source_ip}
                )

            # Find all rubix.db files
            with OperationContext("FIND_DATABASES", 'MAIN', logger):
                # Dynamic search path based on executable location
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    # Bundled executable - search from executable's parent directory
                    search_path = str(Path(sys.executable).parent)
                    logger.info(f"Bundled executable detected, searching from: {search_path}")
                else:
                    # Python script - use original logic for development
                    search_path = os.path.join('..', 'Node') if os.path.exists('../Node') else '..'
                    logger.info(f"Python script mode, searching from: {search_path}")

                databases = find_rubix_databases(search_path)
                sync_metrics.total_databases_found = len(databases)

                audit_logger.log_with_context(
                    logger, logging.INFO, f"Found {len(databases)} database files",
                    component='MAIN', operation='DATABASE_DISCOVERY',
                    extra_data={'database_count': len(databases)}
                )

                if not databases:
                    audit_logger.log_with_context(
                        logger, logging.WARNING, "No rubix.db files found in current directory tree",
                        component='MAIN', operation='DATABASE_DISCOVERY'
                    )
                    return

            # Build IPFS path mapping for all databases
            with OperationContext("BUILD_IPFS_MAPPING", 'MAIN', logger):
                ipfs_mapping = build_ipfs_path_mapping(databases)

                # Log IPFS mapping summary (Telegram notification will be sent later during normal flow)
                valid_ipfs = sum(1 for path in ipfs_mapping.values() if path is not None)
                total_dbs = len(databases)
                missing_ipfs = total_dbs - valid_ipfs

                audit_logger.log_with_context(
                    logger, logging.INFO, f"IPFS mapping completed: {valid_ipfs}/{total_dbs} valid paths",
                    component='MAIN', operation='IPFS_MAPPING_COMPLETE',
                    extra_data={
                        'total_databases': total_dbs,
                        'valid_ipfs_paths': valid_ipfs,
                        'missing_ipfs_paths': missing_ipfs,
                        'unique_ipfs_dirs': len(set(path for path in ipfs_mapping.values() if path is not None))
                    }
                )

            # Get already processed databases
            with OperationContext("GET_PROCESSED_DATABASES", 'MAIN', logger, log_start=False):
                processed_dbs = get_processed_databases()
                audit_logger.log_with_context(
                    logger, logging.INFO, f"Found {len(processed_dbs)} previously processed databases",
                    component='MAIN', operation='PROCESSED_CHECK',
                    extra_data={'processed_count': len(processed_dbs)}
                )

            # Filter databases that need processing
            databases_to_process = [
                (db_path, last_mod)
                for db_path, last_mod in databases
                if needs_processing(db_path, last_mod, processed_dbs)
            ]

            if not databases_to_process:
                audit_logger.log_with_context(
                    logger, logging.INFO, "All databases are up to date. Nothing to process.",
                    component='MAIN', operation='PROCESSING_CHECK',
                    extra_data={'up_to_date_count': len(databases)}
                )
                return

            # Show processing plan on console
            print(f"\n🔄 Processing {len(databases_to_process)} databases ({len(databases) - len(databases_to_process)} up to date)")

            audit_logger.log_with_context(
                logger, logging.INFO,
                f"Processing {len(databases_to_process)} databases ({len(databases) - len(databases_to_process)} up to date)",
                component='MAIN', operation='PROCESSING_PLAN',
                extra_data={
                    'to_process': len(databases_to_process),
                    'up_to_date': len(databases) - len(databases_to_process),
                    'total': len(databases)
                }
            )

            # Process each database with enhanced monitoring
            for idx, (db_path, db_last_modified) in enumerate(databases_to_process, 1):
                db_correlation_id = audit_logger.start_operation(f"PROCESS_DB_{idx}")
                db_start_time = time.time()

                audit_logger.log_with_context(
                    logger, logging.INFO, f"[{idx}/{len(databases_to_process)}] Processing: {db_path}",
                    component='MAIN', operation='DATABASE_PROCESSING',
                    extra_data={
                        'database_index': idx,
                        'total_databases': len(databases_to_process),
                        'db_path': db_path,
                        'db_last_modified': db_last_modified
                    }
                )

                # Process database with incremental batches (IPFS + immediate DB insertion)
                with OperationContext(f"PROCESS_DATABASE_{Path(db_path).stem}", 'SYNC', sync_logger):
                    processing_success = process_database_incremental(db_path, db_last_modified, source_ip, script_dir, ipfs_mapping)

                if processing_success:
                    # ✅ Incremental processing completed successfully
                    # Note: Metrics, IPFS processing, and database insertion were all handled
                    # incrementally in process_database_incremental()

                    audit_logger.log_with_context(
                        logger, logging.INFO,
                        f"✅ Incremental processing completed for {extract_node_name(db_path)}",
                        component='SYNC', operation='DATABASE_PROCESSED_INCREMENTAL',
                        extra_data={
                            'database': db_path,
                            'processing_method': 'incremental_1000_batches',
                            'database_index': idx,
                            'total_databases': len(databases_to_process)
                        }
                    )

                    # Database processing completed - all handled by incremental processing
                    sync_metrics.total_databases_processed += 1

                else:
                    # Incremental processing failed - log the issue
                    audit_logger.log_with_context(
                        logger, logging.ERROR,
                        f"❌ Incremental processing failed for {extract_node_name(db_path)}",
                        component='SYNC', operation='DATABASE_FAILED',
                        extra_data={
                            'database': db_path,
                            'database_index': idx,
                            'total_databases': len(databases_to_process)
                        }
                    )

                audit_logger.end_operation()  # End database processing operation

                # Progress reporting
                if idx % PROGRESS_REPORT_INTERVAL == 0 or idx == len(databases_to_process):
                    elapsed = time.time() - sync_metrics.start_time.timestamp()
                    progress_pct = (idx / len(databases_to_process)) * 100
                    rate = sync_metrics.total_records_processed / max(elapsed, 1)

                    progress_data = {
                        'progress_percentage': progress_pct,
                        'databases_completed': idx,
                        'total_databases': len(databases_to_process),
                        'records_processed': sync_metrics.total_records_processed,
                        'processing_rate': rate,
                        'ipfs_success': sync_metrics.total_ipfs_success,
                        'sql_errors': sync_metrics.total_sql_errors,
                        'elapsed_time': elapsed
                    }

                    audit_logger.log_with_context(
                        logger, logging.INFO,
                        f"Progress: {progress_pct:.1f}% | Records: {sync_metrics.total_records_processed:,} | "
                        f"Rate: {rate:.1f}/sec | IPFS Success: {sync_metrics.total_ipfs_success:,} | "
                        f"SQL Errors: {sync_metrics.total_sql_errors:,}",
                        component='MAIN', operation='PROGRESS_REPORT',
                        extra_data=progress_data
                    )

                    # Send Telegram progress notification
                    if telegram_enabled:
                        try:
                            notify_progress(progress_data)
                        except Exception as e:
                            logger.warning(f"Failed to send progress notification: {e}")

            # Update final session metrics
            if session_id:
                with OperationContext("UPDATE_FINAL_SESSION", 'MAIN', logger, log_start=False):
                    update_sync_session(session_id, sync_metrics, "COMPLETED")

            # Generate comprehensive final report
            with OperationContext("GENERATE_FINAL_REPORT", 'MAIN', logger):
                generate_final_report()

                # Send Telegram completion notification
                if telegram_enabled:
                    try:
                        final_metrics = sync_metrics.to_dict()
                        notify_completion(final_metrics)
                    except Exception as e:
                        logger.warning(f"Failed to send completion notification: {e}")

        except KeyboardInterrupt:
            audit_logger.log_with_context(
                logger, logging.WARNING, "Process interrupted by user",
                component='MAIN', operation='INTERRUPTION'
            )
            if session_id:
                sync_metrics.add_error("system", "Process interrupted by user")
                update_sync_session(session_id, sync_metrics, "INTERRUPTED")

            # Send Telegram notification for interruption
            if telegram_enabled:
                try:
                    notify_error("system", "Sync process interrupted by user", {
                        'session_id': session_id,
                        'records_processed': sync_metrics.total_records_processed
                    })
                except Exception:
                    pass

            sys.exit(1)

        except Exception as e:
            audit_logger.log_with_context(
                logger, logging.ERROR, f"Fatal error: {e}",
                component='MAIN', operation='FATAL_ERROR',
                exc_info=True
            )
            sync_metrics.add_error("system", f"Fatal error: {e}")
            if session_id:
                update_sync_session(session_id, sync_metrics, "FAILED")

            # Send Telegram notification for fatal error
            if telegram_enabled:
                try:
                    notify_error("system", f"Fatal sync error: {str(e)[:200]}", {
                        'session_id': session_id,
                        'error_type': type(e).__name__,
                        'records_processed': sync_metrics.total_records_processed
                    })
                except Exception:
                    pass

            sys.exit(1)

        finally:
            # Clean up resources
            try:
                # Clean up connection pool
                if connection_pool:
                    connection_pool.close_all()
                    audit_logger.log_with_context(
                        logger, logging.INFO, "Connection pool closed",
                        component='MAIN', operation='CLEANUP'
                    )

                # Shutdown Telegram notifications
                if TELEGRAM_AVAILABLE:
                    shutdown_telegram()

                # End main operation
                audit_logger.end_operation()

            except Exception as cleanup_error:
                print(f"Error during cleanup: {cleanup_error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Distributed Token Sync with Azure SQL Database')
    parser.add_argument('--clear', action='store_true',
                        help='Clear all existing records before sync')
    parser.add_argument('--force-ipfs', action='store_true',
                        help='Force IPFS fetch for all tokens (even if already fetched)')
    parser.add_argument('--cleanup-locks', action='store_true',
                        help='Clean up records with IPFS lock errors for retry')
    parser.add_argument('--essential-only', action='store_true',
                        help='Capture only essential metadata (token_id, did, source_ip, node_name) without IPFS processing')

    args = parser.parse_args()

    print("🚀 Rubix Distributed Token Sync System")
    print("=" * 50)

    if args.clear:
        print("🗑️  Clearing existing records...")
        if not clear_all_records():
            print("❌ Failed to clear records. Exiting.")
            sys.exit(1)
        print()

    if args.cleanup_locks:
        print("🔧 Cleaning up IPFS lock errors...")
        if not cleanup_ipfs_lock_errors():
            print("❌ Failed to clean up lock errors. Exiting.")
            sys.exit(1)
        print()

    if args.essential_only:
        print("📋 Essential metadata capture mode: Capturing only core data (token_id, did, source_ip, node_name)")
        print("⚡ Skipping IPFS processing for faster execution")
        if not run_essential_metadata_capture():
            print("❌ Failed to capture essential metadata. Exiting.")
            sys.exit(1)
        print("✅ Essential metadata capture completed successfully!")
        sys.exit(0)

    if args.force_ipfs:
        print("🔄 Force IPFS mode: Will re-fetch all IPFS data")
        print()

    main()
