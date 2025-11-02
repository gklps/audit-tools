# Detailed Logging and Telegram Notification Guide

## Overview

The Rubix Token Sync System now includes comprehensive audit logging and real-time Telegram notifications for monitoring multiple VMs. This guide covers the enhanced logging system, Telegram bot integration, and monitoring capabilities.

## 📋 **Enhanced Logging System**

### Log File Structure

The system creates multiple log files in the `logs/` directory:

```
logs/
├── sync_main_YYYYMMDD.log       # Main application logs (INFO+)
├── sync_debug_YYYYMMDD.log      # Complete debug logs (DEBUG+)
├── sync_errors_YYYYMMDD.log     # Error-only logs (ERROR+)
├── sync_ipfs_YYYYMMDD.log       # IPFS-specific operations
├── sync_sql_YYYYMMDD.log        # Database operations
├── sync_validation_YYYYMMDD.log # Data validation logs
└── sync_sync_YYYYMMDD.log       # Sync process coordination
```

### Log Format

Each log entry follows a structured format:
```
YYYY-MM-DD HH:MM:SS - LEVEL - COMPONENT:OPERATION [CORRELATION_ID] - MESSAGE
```

**Example:**
```
2024-01-15 14:30:45 - INFO - SQL:BULK_INSERT [a1b2c3d4] - Bulk insert completed successfully: 2000 records
2024-01-15 14:30:46 - ERROR - IPFS:FETCH [a1b2c3d4] - IPFS timeout for token QmXYZ123
Stack Trace: subprocess.TimeoutExpired...
```

### Log Rotation

- **Main/Debug Logs**: 100MB/200MB max size, 10/5 backups
- **Error Logs**: 50MB max size, 50 backups (long retention)
- **Component Logs**: 50MB max size, 10 backups each

### Correlation Tracking

Each operation gets a unique 8-character correlation ID that tracks related log entries across components:

```python
# Operations are automatically tracked with correlation IDs
with OperationContext("BULK_INSERT_2000_RECORDS", 'SQL', sql_logger):
    # All logs within this context share the same correlation ID
    bulk_insert_records(records)
```

## 🔍 **Log Analysis Tools**

### Using the Log Analyzer

The `log_analyzer.py` script provides comprehensive log analysis:

```bash
# Generate summary report for last 24 hours
python3 log_analyzer.py --hours 24

# Analyze only errors
python3 log_analyzer.py --errors-only --hours 12

# Export metrics to CSV
python3 log_analyzer.py --export-csv metrics.csv --hours 48

# Specify custom logs directory
python3 log_analyzer.py --logs-dir /custom/path/logs
```

### Sample Analysis Output

```
================================================================================
RUBIX TOKEN SYNC - LOG ANALYSIS REPORT
Generated: 2024-01-15 15:30:00
Analysis Period: Last 24 hours
================================================================================

📊 PERFORMANCE SUMMARY
----------------------------------------
Total Records Processed: 3,456,789
Average Processing Rate: 387.2 records/sec
IPFS Success Rate: 98.7%
SQL Success Rate: 99.9%
Validation Pass Rate: 97.3%

🔍 OPERATION BREAKDOWN
----------------------------------------
IPFS Operations: 3,400,234 success, 56,555 failed
SQL Operations: 3,456,789 success, 0 failed
Bulk Inserts: 1,728 operations

⚠️  ERROR ANALYSIS
----------------------------------------
Total Errors: 56,789
Error Rate: 1.64%

Top Error Types:
  timeout: 45,234
  ipfs: 8,976
  validation: 2,345
  other: 234

📈 HOURLY PERFORMANCE TRENDS
----------------------------------------
  2024-01-15 08:00: 423.5 records/sec (samples: 12)
  2024-01-15 09:00: 456.7 records/sec (samples: 18)
  ...
```

## 📱 **Telegram Bot Integration**

### Setup Requirements

1. **Create Telegram Bot**:
   ```
   1. Message @BotFather on Telegram
   2. Send /newbot
   3. Choose bot name and username
   4. Copy the bot token
   ```

2. **Get Chat ID**:
   ```
   1. Add bot to your chat/channel
   2. Send a message to the bot
   3. Visit: https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   4. Copy the chat ID from the response
   ```

### Configuration

Copy and edit the Telegram configuration:
```bash
cp telegram_config_template.json telegram_config.json
nano telegram_config.json
```

**Configuration Options:**
```json
{
  "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "chat_id": "-1001234567890",
  "enabled": true,
  "machine_name": "Production-VM-1",
  "public_ip": "203.0.113.12",
  "send_startup": true,
  "send_progress": true,
  "send_errors": true,
  "send_completion": true,
  "progress_interval": 300,
  "max_message_length": 4000
}
```

### Machine Identification

Each VM is automatically identified by:
- **Machine Name**: Custom name (e.g., "Production-VM-1")
- **Public IP**: Automatically detected IPv4 address
- **Combined ID**: "Production-VM-1 (203.0.113.12)"

### Notification Types

#### 1. **Startup Notification**
```
🖥️ Production-VM-1 (203.0.113.12)
🚀 SYNC STARTED
```
Type: Distributed Token Sync - Azure SQL Database
Time: 2024-01-15 14:30:00 UTC
Status: Initializing...
```

#### 2. **Progress Updates** (every 5 minutes)
```
🖥️ Production-VM-1 (203.0.113.12)
📊 SYNC PROGRESS
```
██████████████░░░░░░ 73.5%

Records: 2,543,210
Rate: 387.2/sec
IPFS Success: 2,511,234
SQL Errors: 0
Elapsed: 109.3 min
```

#### 3. **Error Notifications**
```
🖥️ Production-VM-1 (203.0.113.12)
❌ ERROR DETECTED
```
Type: database
Time: 14:35:22
Message: Connection timeout to Azure SQL
```
Context:
error_type: TimeoutError
session_id: abc123def
records_processed: 1234567
```

#### 4. **Database Completion** (for large databases)
```
🖥️ Production-VM-1 (203.0.113.12)
📁 DATABASE COMPLETED
```
Name: node042_rubix
Records: 25,430
Duration: 67.2s
IPFS Rate: 98.3%
```

#### 5. **Final Completion**
```
🖥️ Production-VM-1 (203.0.113.12)
✅ SYNC COMPLETED
```
Duration: 115.7 minutes
Databases: 145
Records: 3,456,789
Avg Rate: 498.2/sec

Success Rates:
├─ IPFS: 98.7%
└─ SQL: 99.9%

Errors: 56,789
```

## 🛠️ **Operational Procedures**

### Starting a Sync with Monitoring

```bash
# 1. Ensure dependencies are installed
pip3 install -r requirements.txt

# 2. Configure Telegram (one time per VM)
cp telegram_config_template.json telegram_config.json
# Edit with your bot token and chat ID

# 3. Configure Azure SQL connection
cp azure_sql_connection_template.txt /datadrive/Rubix/azure_sql_connection.txt
# Edit with your password

# 4. Run sync with full logging and Telegram
python3 sync_distributed_tokens.py

# 5. Monitor logs in real-time (separate terminal)
tail -f logs/sync_main_$(date +%Y%m%d).log
```

### Multi-VM Monitoring Dashboard

For monitoring multiple VMs, Telegram messages will be tagged with machine identification:

```
🖥️ Prod-VM-1 (203.0.113.10)   📊 Progress: 45.2% | Rate: 456/sec
🖥️ Prod-VM-2 (203.0.113.11)   📊 Progress: 67.8% | Rate: 387/sec
🖥️ Prod-VM-3 (203.0.113.12)   📊 Progress: 23.1% | Rate: 512/sec
🖥️ Prod-VM-1 (203.0.113.10)   ❌ IPFS timeout error
🖥️ Prod-VM-2 (203.0.113.11)   📁 Database node087 completed
```

### Real-time Log Analysis

```bash
# Monitor errors across all components
grep "ERROR" logs/sync_*.log | tail -20

# Track progress updates
grep "Progress:" logs/sync_main_*.log | tail -10

# Monitor IPFS performance
grep "IPFS.*SUCCESS" logs/sync_ipfs_*.log | wc -l

# Check recent SQL operations
grep "Database.*SUCCESS" logs/sync_sql_*.log | tail -10
```

### Performance Monitoring Queries

Use these queries to monitor sync performance in Azure SQL Database:

```sql
-- Current active sessions
SELECT
    session_id,
    source_ip,
    start_time,
    total_records_processed,
    total_records_processed / NULLIF(DATEDIFF(SECOND, start_time, GETUTCDATE()), 0) as current_rate,
    status
FROM SyncSessions
WHERE status = 'RUNNING'
ORDER BY start_time DESC;

-- Error patterns by machine
SELECT
    source_ip,
    COUNT(*) as total_records,
    SUM(CASE WHEN ipfs_fetched = 1 THEN 1 ELSE 0 END) as ipfs_success,
    SUM(CASE WHEN validation_errors IS NOT NULL THEN 1 ELSE 0 END) as validation_errors
FROM TokenRecords
WHERE synced_at > DATEADD(HOUR, -24, GETUTCDATE())
GROUP BY source_ip
ORDER BY total_records DESC;

-- Processing rate by hour
SELECT
    DATEPART(HOUR, synced_at) as hour,
    COUNT(*) as records_processed,
    COUNT(*) / 60.0 as avg_records_per_minute
FROM TokenRecords
WHERE synced_at > DATEADD(DAY, -1, GETUTCDATE())
GROUP BY DATEPART(HOUR, synced_at)
ORDER BY hour;
```

## 🔧 **Troubleshooting**

### Common Issues

#### 1. **Telegram Not Working**
```bash
# Check if telegram_notifier is available
python3 -c "import telegram_notifier; print('OK')"

# Check bot token and chat ID
python3 -c "
from telegram_notifier import init_telegram_notifier
notifier = init_telegram_notifier()
print('Test result:', notifier.test_connection() if notifier else 'No config')
"

# Test message
python3 -c "
from telegram_notifier import init_telegram_notifier
notifier = init_telegram_notifier()
if notifier: notifier.send_message('Test message from sync system')
"
```

#### 2. **Log Files Not Created**
```bash
# Check logs directory permissions
ls -la logs/
mkdir -p logs
chmod 755 logs

# Check disk space
df -h

# Verify logging initialization
grep "logging" logs/sync_debug_*.log | head -5
```

#### 3. **Missing Correlation IDs**
```bash
# Check if operations are using context managers
grep "OperationContext" sync_distributed_tokens.py

# Verify correlation tracking
grep "\[.*\]" logs/sync_main_*.log | head -10
```

### Advanced Debugging

#### Enable Detailed IPFS Logging
```python
# Add to sync script for debugging IPFS issues
ipfs_logger.setLevel(logging.DEBUG)
```

#### Custom Error Notifications
```python
# Send custom Telegram alert
from telegram_notifier import notify_error
notify_error("custom", "Custom alert message", {
    "vm_id": "special-vm",
    "custom_data": "value"
})
```

#### Log Analysis for Specific Issues
```bash
# Find all timeout errors with context
grep -A 5 -B 5 "timeout" logs/sync_errors_*.log

# Track specific token processing
grep "QmYourTokenId" logs/sync_ipfs_*.log

# Monitor memory usage patterns
grep -E "(memory|Memory)" logs/sync_debug_*.log
```

## 📊 **Best Practices**

### For Single VM Operations
- Monitor `sync_main_*.log` for general progress
- Check `sync_errors_*.log` daily for patterns
- Use Telegram for real-time awareness

### For Multi-VM Operations
- Use unique machine names in Telegram config
- Set different progress intervals (300s for busy VMs, 600s for slower)
- Monitor Telegram channel for cross-VM coordination
- Use log analyzer weekly for performance comparison

### Log Retention Strategy
- **Main logs**: Keep 1 month (10 rotations × 100MB)
- **Error logs**: Keep 6 months (50 rotations × 50MB)
- **Debug logs**: Keep 1 week (5 rotations × 200MB)
- **Component logs**: Keep 2 weeks (10 rotations × 50MB)

### Performance Optimization
- Increase progress intervals during high-load periods
- Use DEBUG level sparingly in production
- Archive old logs to external storage
- Monitor log file sizes and adjust rotation as needed

## 🎯 **Summary**

The enhanced logging and Telegram notification system provides:

✅ **Complete Audit Trail**: Every operation tracked with correlation IDs
✅ **Real-time Monitoring**: Telegram notifications for multiple VMs
✅ **Error Analysis**: Comprehensive error categorization and tracking
✅ **Performance Insights**: Detailed metrics and trend analysis
✅ **Multi-VM Support**: Automatic machine identification and coordination
✅ **Operational Visibility**: Progress tracking and completion notifications

This system enables confident operation of distributed sync processes across multiple VMs with full visibility into performance, errors, and completion status.