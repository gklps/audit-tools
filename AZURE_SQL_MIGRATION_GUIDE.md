# Azure SQL Database Migration Guide

## Overview

This document outlines the migration from PostgreSQL to Azure SQL Database for the Rubix Token Sync System. The updated system provides enhanced performance, better monitoring, and comprehensive error handling.

## Key Improvements

### 1. **Azure SQL Database Integration**
- **Connection**: ADO.NET connection string with SSL encryption
- **Performance**: Optimized bulk inserts using `fast_executemany`
- **Schema**: SQL Server-optimized table structures with proper indexing
- **Connection Pooling**: Thread-safe connection pool for better resource management

### 2. **Enhanced Data Transfer Efficiency**
- **Bulk Operations**: Uses bulk insert for datasets ≥10,000 records
- **Batch Processing**: 2,000 records per batch (optimized for Azure SQL)
- **Parallel Processing**: Increased IPFS workers (CPU count × 2)
- **Retry Logic**: 3 retry attempts for failed IPFS calls with exponential backoff
- **Fallback Strategy**: Individual inserts when bulk operations fail

### 3. **Comprehensive Reporting & Monitoring**
- **Real-time Metrics**: Thread-safe metrics tracking with SyncMetrics class
- **Session Tracking**: Each sync run tracked in SyncSessions table
- **Progress Reporting**: Regular progress updates every 100 records
- **JSON Reports**: Detailed JSON reports with performance analytics
- **Error Tracking**: Categorized error logging with context

### 4. **Data Validation & Quality**
- **TokenRecord Structure**: Structured data validation using dataclasses
- **Format Validation**: Token ID and DID format validation
- **Size Limits**: IPFS data size validation (50KB limit)
- **Missing Data Detection**: Comprehensive missing detail tracking

## Database Schema

### TokenRecords Table (Primary Data)
```sql
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
```

### ProcessedDatabases Table (Metadata)
```sql
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
```

### SyncSessions Table (Session Tracking)
```sql
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
```

## Performance Optimizations

### Connection Configuration
```python
# Optimized performance settings
NUM_IPFS_WORKERS = cpu_count() * 2      # Increased IPFS throughput
BATCH_SIZE = 2000                       # Larger batches for Azure SQL
BULK_INSERT_SIZE = 10000               # Bulk insert threshold
CONNECTION_POOL_SIZE = 10              # Connection pool for Azure SQL
RETRY_ATTEMPTS = 3                     # Retry failed operations
```

### Expected Performance
- **Conservative**: 150-200 records/second
- **Typical**: 300-500 records/second
- **Optimized**: 800-1,000 records/second (with fast IPFS and good network)

### Data Transfer Strategy
1. **Small Datasets** (<10K records): Batch processing (2K per batch)
2. **Large Datasets** (≥10K records): Bulk insert with `fast_executemany`
3. **Failed Operations**: Automatic fallback to individual inserts
4. **Error Recovery**: Retry logic with exponential backoff

## Installation & Setup

### 1. Update Dependencies
```bash
pip install -r requirements.txt
```

New dependencies:
- `pyodbc==5.0.1` (SQL Server driver)
- `pandas==2.1.4` (Data processing)
- `sqlalchemy==2.0.23` (Database utilities)

### 2. Configure Azure SQL Connection
```bash
# Copy template and update password
cp azure_sql_connection_template.txt /datadrive/Rubix/azure_sql_connection.txt

# Edit the connection file with your password
nano /datadrive/Rubix/azure_sql_connection.txt
```

### 3. Update Connection String
Replace `{your_password}` with the actual password:
```
Server=tcp:rauditser.database.windows.net,1433;Initial Catalog=rauditd;Persist Security Info=False;User ID=rubix;Password=YOUR_ACTUAL_PASSWORD;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;
```

### 4. Test Connection
```bash
python3 sync_distributed_tokens.py --test-connection
```

## Running the Sync

### Standard Execution
```bash
python3 sync_distributed_tokens.py
```

### Monitor Progress
```bash
# Follow the log in real-time
tail -f sync_distributed_tokens.log

# Monitor specific metrics
grep "Progress:" sync_distributed_tokens.log | tail -10
```

## Monitoring & Reporting

### Real-time Monitoring
The system provides detailed progress updates:
```
Progress: 25.0% | Records: 125,430 | Rate: 387.2/sec | IPFS Success: 119,203 | SQL Errors: 0
```

### Session Tracking
Query current and historical sync sessions:
```sql
-- Current running sessions
SELECT * FROM [dbo].[SyncSessions] WHERE [status] = 'RUNNING';

-- Performance summary
SELECT
    [session_id],
    [start_time],
    [end_time],
    [total_records_processed],
    [total_records_processed] / NULLIF(DATEDIFF(SECOND, [start_time], [end_time]), 0) as [records_per_second],
    ([total_ipfs_success] * 100.0 / NULLIF([total_records_processed], 0)) as [ipfs_success_rate],
    [status]
FROM [dbo].[SyncSessions]
ORDER BY [start_time] DESC;
```

### Detailed Reports
Each sync generates a JSON report with comprehensive metrics:
```json
{
  "total_records_processed": 3400000,
  "duration_seconds": 3600.5,
  "records_per_second": 944.3,
  "ipfs_success_rate": 98.7,
  "sql_success_rate": 99.9,
  "total_databases_processed": 145,
  "errors": [...]
}
```

## Error Handling & Recovery

### Automatic Error Recovery
1. **IPFS Timeouts**: 3 retry attempts with exponential backoff
2. **SQL Failures**: Automatic fallback from bulk to individual inserts
3. **Connection Issues**: Connection pool automatically recovers lost connections
4. **Data Validation**: Invalid records logged but don't stop processing

### Error Categories
- **`ipfs`**: IPFS fetch failures, timeouts, invalid responses
- **`database`**: SQL connection, query, or constraint errors
- **`validation`**: Data format, size, or content validation failures
- **`system`**: System-level errors, interruptions, resource issues

### Error Analysis Queries
```sql
-- Error summary by type (last 24 hours)
SELECT
    [node_name],
    COUNT(*) as [total_records],
    SUM(CAST([ipfs_fetched] AS INT)) as [ipfs_success],
    COUNT(*) - SUM(CAST([ipfs_fetched] AS INT)) as [ipfs_failures],
    SUM(CASE WHEN [validation_errors] IS NOT NULL THEN 1 ELSE 0 END) as [validation_errors]
FROM [dbo].[TokenRecords]
WHERE [synced_at] > DATEADD(HOUR, -24, GETUTCDATE())
GROUP BY [node_name]
ORDER BY [total_records] DESC;

-- Most common IPFS errors
SELECT
    [ipfs_error],
    COUNT(*) as [error_count]
FROM [dbo].[TokenRecords]
WHERE [ipfs_error] IS NOT NULL
    AND [synced_at] > DATEADD(HOUR, -24, GETUTCDATE())
GROUP BY [ipfs_error]
ORDER BY [error_count] DESC;
```

## Security Considerations

### Connection Security
- ✅ **SSL/TLS Encryption**: `Encrypt=True` enforces encrypted connections
- ✅ **Connection Timeout**: 30-second timeout prevents hanging connections
- ✅ **SQL Authentication**: Uses dedicated database user (not admin)
- ⚠️ **Credential Storage**: Store connection strings in secure, restricted files

### File Permissions
```bash
# Secure the connection file
chmod 600 /datadrive/Rubix/azure_sql_connection.txt
chown root:root /datadrive/Rubix/azure_sql_connection.txt
```

### Network Security
- Azure SQL Database firewall rules should restrict access to known IPs
- Use Azure Private Link for additional network isolation if required

## Troubleshooting

### Common Issues

#### 1. **Connection Failures**
```
Error: Login failed for user 'rubix'
```
**Solution**: Verify password in connection string and Azure SQL firewall rules.

#### 2. **ODBC Driver Missing**
```
Error: Data source name not found and no default driver specified
```
**Solution**: Install Microsoft ODBC Driver for SQL Server:
```bash
# Ubuntu/Debian
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

#### 3. **Performance Issues**
- **Slow IPFS**: Increase `IPFS_TIMEOUT` and reduce `NUM_IPFS_WORKERS`
- **Database Locks**: Reduce `BATCH_SIZE` and `CONNECTION_POOL_SIZE`
- **Memory Issues**: Lower `BULK_INSERT_SIZE` and increase batch processing

#### 4. **Validation Errors**
Check the `validation_errors` field in TokenRecords:
```sql
SELECT TOP 10 [token_id], [validation_errors]
FROM [dbo].[TokenRecords]
WHERE [validation_errors] IS NOT NULL
ORDER BY [synced_at] DESC;
```

### Performance Tuning

For different environments, adjust these parameters:

#### High-Performance Environment
```python
NUM_IPFS_WORKERS = cpu_count() * 3
BATCH_SIZE = 5000
BULK_INSERT_SIZE = 20000
CONNECTION_POOL_SIZE = 15
```

#### Resource-Constrained Environment
```python
NUM_IPFS_WORKERS = max(2, cpu_count() // 2)
BATCH_SIZE = 1000
BULK_INSERT_SIZE = 5000
CONNECTION_POOL_SIZE = 5
```

## Migration Checklist

- [ ] Install new dependencies (`pip install -r requirements.txt`)
- [ ] Configure Azure SQL Database connection string
- [ ] Test database connectivity
- [ ] Run initial sync with small dataset
- [ ] Monitor performance and adjust parameters
- [ ] Set up automated monitoring and alerting
- [ ] Document any environment-specific configurations
- [ ] Plan rollback strategy if needed

## Support & Maintenance

### Regular Maintenance
1. **Monitor sync sessions**: Check for failed or stuck sessions
2. **Review error patterns**: Analyze common errors and optimize
3. **Performance monitoring**: Track processing rates and optimize as needed
4. **Database maintenance**: Regular index maintenance and statistics updates

### Backup Strategy
- **Database Backups**: Azure SQL Database automated backups
- **Configuration Files**: Backup connection strings and configuration
- **Log Files**: Archive sync logs for historical analysis

For additional support, refer to the existing `DISTRIBUTED_TOKENS_GUIDE.md` and `QUICK_REFERENCE.md` files for operational procedures.