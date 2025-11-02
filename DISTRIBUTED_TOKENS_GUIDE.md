# Distributed Token Sync with IPFS - Complete Guide

This script scans directories for multiple `Rubix/rubix.db` SQLite databases, reads TokensTable data, **fetches IPFS metadata via `ipfs cat`**, and syncs everything to a centralized PostgreSQL database.

## Purpose

When you have multiple Rubix nodes across different directories (e.g., `/mnt/drived/node032`, `/mnt/drived/node033`), this script:
- **Discovers** all `Rubix/rubix.db` files recursively
- **Extracts** token data from each database's TokensTable
- **Fetches IPFS metadata** using `ipfs cat` for each token_id
- **Centralizes** everything into PostgreSQL with source tracking
- **Tracks** which databases have been processed and when
- **Re-syncs** only databases that have been modified

## Features

✅ **Recursive scanning** - Finds all `*/Rubix/rubix.db` files
✅ **IPFS integration** - Fetches `ipfs cat <token_id>` for each token
✅ **Automatic .ipfs detection** - Finds correct IPFS_PATH for each node
✅ **Source tracking** - Records which VM/IP and node each token came from
✅ **Parallel IPFS calls** - Fast processing with multiprocessing
✅ **NULL handling** - Properly handles empty/NULL values from SQLite
✅ **Smart sync** - Only processes new or modified databases
✅ **Duplicate handling** - Stores all records including duplicates
✅ **Progress tracking** - Real-time status with IPFS success/fail rates
✅ **Resumable** - Can interrupt and restart safely

## Directory Structure

Expected layout:

```
/mnt/drived/                        (or any directory)
├── sync_distributed_tokens.py     (this script)
├── ipfs                            (IPFS executable)
├── node032/
│   ├── .ipfs/                      (IPFS data directory for node032)
│   │   ├── blocks/
│   │   ├── datastore/
│   │   └── config
│   └── Rubix/
│       └── rubix.db               (SQLite database)
├── node033/
│   ├── .ipfs/
│   └── Rubix/
│       └── rubix.db
└── node034/
    ├── .ipfs/
    └── Rubix/
        └── rubix.db
```

## How It Works

### For Each Database Found:

1. **Scan** for `/mnt/drived/node*/Rubix/rubix.db`
2. **Extract node name** from path (e.g., `node032`)
3. **Find .ipfs directory** (e.g., `/mnt/drived/node032/.ipfs`)
4. **Read TokensTable** from SQLite database
5. **For each token**:
   - Set `IPFS_PATH=./node032/.ipfs`
   - Run `./ipfs cat <token_id>`
   - Store raw IPFS output (e.g., "TRI 0 bafyb...")
   - Handle failures gracefully (store NULL, log error)
6. **Batch insert** to PostgreSQL with all metadata

### Example Data Flow:

**SQLite Input** (`/mnt/drived/node032/Rubix/rubix.db`):
```
did: did:rubix:123abc...
token_id: QmNLpxYjcFZyW7wNKBJQWK6mWc9LLN1vQv86x9BGYwdGfg
token_status: active
created_at: 2025-01-15 10:30:00
```

**IPFS Command**:
```bash
export IPFS_PATH=/mnt/drived/node032/.ipfs
./ipfs cat QmNLpxYjcFZyW7wNKBJQWK6mWc9LLN1vQv86x9BGYwdGfg
```

**IPFS Output**:
```
TRI 0 bafybmibeud2c4ucgew6m5tttj7zneosplm4eiklwg4migdimdwmezkzi6u
```

**PostgreSQL Record**:
```
source_ip: 172.203.210.205
node_name: node032
did: did:rubix:123abc...
token_id: QmNLpxYjcFZyW7wNKBJQWK6mWc9LLN1vQv86x9BGYwdGfg
token_status: active
ipfs_data: "TRI 0 bafybmibeud2..."
ipfs_fetched: TRUE
ipfs_error: NULL
db_path: /mnt/drived/node032/Rubix/rubix.db
ipfs_path: /mnt/drived/node032/.ipfs
synced_at: 2025-01-15 11:00:00
```

## Database Schema

### TokenRecords Table

Stores all token data with IPFS metadata and source tracking:

```sql
CREATE TABLE TokenRecords (
    id SERIAL PRIMARY KEY,                    -- Auto-increment ID
    source_ip TEXT NOT NULL,                  -- Public IP of source VM
    node_name TEXT NOT NULL,                  -- Node name (e.g., "node032")

    -- From SQLite TokensTable
    did TEXT,
    token_id TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    token_status TEXT,
    parent_token_id TEXT,
    token_value TEXT,

    -- IPFS data
    ipfs_data TEXT,                           -- Raw output from ipfs cat
    ipfs_fetched BOOLEAN DEFAULT FALSE,       -- Whether IPFS call succeeded
    ipfs_error TEXT,                          -- Error message if IPFS failed

    -- Metadata
    db_path TEXT NOT NULL,                    -- Path to source rubix.db
    ipfs_path TEXT,                           -- Path to .ipfs directory
    db_last_modified TIMESTAMP NOT NULL,      -- When db file was modified
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When synced to PostgreSQL
);
```

**Indexes for fast queries:**
- `idx_tokenrecords_token_id` on token_id
- `idx_tokenrecords_did` on did
- `idx_tokenrecords_node_name` on node_name
- `idx_tokenrecords_source_ip` on source_ip
- `idx_tokenrecords_db_path` on db_path
- `idx_tokenrecords_ipfs_fetched` on ipfs_fetched

### ProcessedDatabases Table

Tracks which databases have been processed:

```sql
CREATE TABLE ProcessedDatabases (
    db_path TEXT PRIMARY KEY,
    last_modified TIMESTAMP NOT NULL,
    last_processed TIMESTAMP NOT NULL,
    record_count INTEGER DEFAULT 0,
    ipfs_success_count INTEGER DEFAULT 0,    -- How many IPFS calls succeeded
    ipfs_fail_count INTEGER DEFAULT 0        -- How many IPFS calls failed
);
```

## Installation

### Prerequisites

```bash
# Install Python dependencies
pip3 install -r requirements.txt
```

Required packages:
- `psycopg2-binary` - PostgreSQL adapter
- `requests` - For public IP detection

### Setup

1. **Ensure PostgreSQL is running** (from previous setup)
2. **Place script and ipfs executable** in the same directory (e.g., `/mnt/drived/`)
3. **Ensure .ipfs directories exist** for each node
4. **Make executable** (optional):
   ```bash
   chmod +x sync_distributed_tokens.py
   ```

## Usage

### Basic Usage

Run from the directory containing your node folders:

```bash
# Run from /mnt/drived
cd /mnt/drived
python3 sync_distributed_tokens.py
```

### First Run

On first run, the script will:
1. Detect your VM's public IP
2. Scan for all `*/Rubix/rubix.db` files
3. Create PostgreSQL tables (TokenRecords, ProcessedDatabases)
4. For each database:
   - Find corresponding `.ipfs` directory
   - Process all tokens
   - Fetch IPFS data in parallel
5. Insert all records with source metadata

**Example output:**
```
================================================================================
Starting Distributed Token Sync Service (with IPFS)
================================================================================
Script directory: /mnt/drived
Detected public IP: 172.203.210.205
Scanning for rubix.db files from: /mnt/drived
Found database: /mnt/drived/node032/Rubix/rubix.db
Found database: /mnt/drived/node033/Rubix/rubix.db
Found database: /mnt/drived/node034/Rubix/rubix.db
Total databases found: 3

Connecting to PostgreSQL database
PostgreSQL tables created or already exist
Found 0 previously processed databases
Processing 3 databases (0 up to date)

[1/3] Processing: /mnt/drived/node032/Rubix/rubix.db
Processing node032: /mnt/drived/node032/Rubix/rubix.db
  IPFS path: /mnt/drived/node032/.ipfs
  Found 5420 tokens in node032
  Fetching IPFS data for 5420 tokens using 8 workers...
  IPFS fetch: 5380 succeeded, 40 failed
  Inserted 1000 records into PostgreSQL
  Inserted 1000 records into PostgreSQL
  ...
Progress: 33.3% | Total records: 5,420 | IPFS success: 5,380 | IPFS fails: 40

[2/3] Processing: /mnt/drived/node033/Rubix/rubix.db
...

================================================================================
Sync completed in 285.42 seconds (4.8 minutes)
Databases found: 3
Databases processed: 3
Total records synced: 16,245
IPFS successful: 16,120 (99.2%)
IPFS failed: 125 (0.8%)
================================================================================
```

### Subsequent Runs

On subsequent runs:
- Only processes databases that were **modified** since last sync
- Skips unchanged databases automatically
- Much faster for regular syncs

```bash
python3 sync_distributed_tokens.py

# Output:
# Found 3 databases
# Found 3 previously processed databases
# Skipping /mnt/drived/node032/Rubix/rubix.db - not modified
# Skipping /mnt/drived/node033/Rubix/rubix.db - not modified
# Processing 1 databases (2 up to date)
```

## Configuration

Edit the script header to customize:

```python
# PostgreSQL connection
POSTGRES_CONNECTION_STRING = 'postgresql://postgres:password@localhost:5432/rubix_tokens'

# Performance tuning
NUM_DB_WORKERS = max(1, cpu_count() // 2)  # Parallel database processing
NUM_IPFS_WORKERS = cpu_count()             # Parallel IPFS calls
BATCH_SIZE = 1000                          # Records per batch insert
IPFS_TIMEOUT = 15                          # Timeout per IPFS call (seconds)
```

## Querying the Data

### View All Tokens with IPFS Data

```sql
SELECT node_name, token_id, ipfs_data, ipfs_fetched
FROM TokenRecords
WHERE ipfs_fetched = TRUE
ORDER BY synced_at DESC
LIMIT 100;
```

### Count Tokens by Node

```sql
SELECT node_name,
       COUNT(*) as total_tokens,
       SUM(CASE WHEN ipfs_fetched THEN 1 ELSE 0 END) as ipfs_success,
       SUM(CASE WHEN NOT ipfs_fetched THEN 1 ELSE 0 END) as ipfs_failed
FROM TokenRecords
GROUP BY node_name
ORDER BY total_tokens DESC;
```

### Find IPFS Failures

```sql
SELECT node_name, token_id, ipfs_error
FROM TokenRecords
WHERE ipfs_fetched = FALSE
LIMIT 50;
```

### Tokens with IPFS Data Across Multiple Nodes

```sql
SELECT token_id,
       COUNT(DISTINCT node_name) as node_count,
       array_agg(DISTINCT node_name) as nodes,
       array_agg(DISTINCT ipfs_data) as ipfs_results
FROM TokenRecords
WHERE token_id IS NOT NULL
GROUP BY token_id
HAVING COUNT(DISTINCT node_name) > 1
LIMIT 20;
```

### IPFS Success Rate by Node

```sql
SELECT node_name,
       COUNT(*) as total,
       SUM(CASE WHEN ipfs_fetched THEN 1 ELSE 0 END) as success,
       ROUND(100.0 * SUM(CASE WHEN ipfs_fetched THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM TokenRecords
GROUP BY node_name;
```

### Recently Synced with IPFS Data

```sql
SELECT * FROM TokenRecords
WHERE synced_at > NOW() - INTERVAL '1 hour'
  AND ipfs_fetched = TRUE
ORDER BY synced_at DESC;
```

### Processing History with IPFS Stats

```sql
SELECT db_path,
       record_count,
       ipfs_success_count,
       ipfs_fail_count,
       ROUND(100.0 * ipfs_success_count / NULLIF(record_count, 0), 2) as success_rate,
       last_processed
FROM ProcessedDatabases
ORDER BY last_processed DESC;
```

## Monitoring

### Watch Live Progress

```bash
# Monitor log file
tail -f sync_distributed_tokens.log

# Check database count
watch -n 5 'psql -U postgres -d rubix_tokens -t -c "SELECT COUNT(*) FROM TokenRecords;"'
```

### Check IPFS Statistics

```sql
-- Overall IPFS success rate
SELECT
    COUNT(*) as total_tokens,
    SUM(CASE WHEN ipfs_fetched THEN 1 ELSE 0 END) as ipfs_success,
    SUM(CASE WHEN NOT ipfs_fetched THEN 1 ELSE 0 END) as ipfs_failed,
    ROUND(100.0 * SUM(CASE WHEN ipfs_fetched THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct
FROM TokenRecords;
```

## Troubleshooting

### No Databases Found

```bash
# Check your current directory
pwd

# Manually search for databases
find . -name "rubix.db" -path "*/Rubix/*" 2>/dev/null

# Verify pattern matches
ls -la */Rubix/rubix.db
```

### IPFS Executable Not Found

```bash
# Check if ipfs exists in script directory
ls -la /mnt/drived/ipfs

# Test ipfs command
./ipfs version

# If missing, provide absolute path in script:
IPFS_COMMAND = '/absolute/path/to/ipfs'
```

### .ipfs Directory Not Found

The script looks for `.ipfs` in:
1. Node directory (e.g., `/mnt/drived/node032/.ipfs`)
2. Parent directory

If not found:
```bash
# Check manually
ls -la /mnt/drived/node032/.ipfs

# Verify IPFS_PATH is correct
export IPFS_PATH=/mnt/drived/node032/.ipfs
./ipfs config show
```

### IPFS Timeouts

If you see many "IPFS timeout" errors:
- Increase `IPFS_TIMEOUT` in the script (default: 15 seconds)
- Check IPFS daemon performance
- Reduce `NUM_IPFS_WORKERS` to avoid overwhelming IPFS

### High IPFS Failure Rate

```sql
-- Find most common errors
SELECT ipfs_error, COUNT(*) as count
FROM TokenRecords
WHERE ipfs_fetched = FALSE
GROUP BY ipfs_error
ORDER BY count DESC;
```

Common issues:
- **"Empty token_id"**: NULL token_ids in database
- **"No IPFS path found"**: Missing .ipfs directory
- **"IPFS timeout"**: Increase timeout or check IPFS performance
- **"block not found"**: Token data not in this node's IPFS

### NULL/Empty Values from SQLite

The script handles empty values properly:
- Empty strings → NULL in PostgreSQL
- NULL values → NULL in PostgreSQL
- Invalid timestamps → NULL

Check NULL statistics:
```sql
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN did IS NULL THEN 1 ELSE 0 END) as null_did,
    SUM(CASE WHEN token_id IS NULL THEN 1 ELSE 0 END) as null_token_id,
    SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) as null_created_at
FROM TokenRecords;
```

## Performance Considerations

### For Multiple Nodes

- **Parallel IPFS calls**: Adjust `NUM_IPFS_WORKERS` (default: CPU count)
- **Batch inserts**: Adjust `BATCH_SIZE` (default: 1000)
- **IPFS timeout**: Balance speed vs success rate

### Expected Performance

- **IPFS calls**: ~50-200 tokens/second (depends on IPFS performance)
- **Database inserts**: Very fast (batch operations)
- **Overall**: Mainly limited by IPFS cat speed

Example timings:
- 5,000 tokens: 2-5 minutes
- 50,000 tokens: 20-50 minutes
- 500,000 tokens: 3-8 hours

### Storage Requirements

Estimate storage needed:
- Each token record with IPFS data: ~800 bytes
- 1 million records: ~800 MB
- 10 million records: ~8 GB

Check current size:
```sql
SELECT pg_size_pretty(pg_total_relation_size('TokenRecords')) as table_size;
```

## Use Cases

### Scenario 1: Multi-Node Token Audit

Verify token consistency across nodes:

```sql
SELECT token_id,
       COUNT(DISTINCT node_name) as node_count,
       COUNT(DISTINCT ipfs_data) as unique_ipfs_data,
       array_agg(DISTINCT node_name) as nodes
FROM TokenRecords
WHERE token_id IS NOT NULL
  AND ipfs_fetched = TRUE
GROUP BY token_id
HAVING COUNT(DISTINCT ipfs_data) > 1;  -- Find mismatches
```

### Scenario 2: IPFS Data Analysis

Parse and analyze IPFS data:

```sql
-- Assuming IPFS data format: "TOKEN_NAME TOKEN_NUM CREATOR_DID"
SELECT
    split_part(ipfs_data, ' ', 1) as token_name,
    split_part(ipfs_data, ' ', 2)::integer as token_number,
    split_part(ipfs_data, ' ', 3) as creator_did,
    COUNT(*) as count
FROM TokenRecords
WHERE ipfs_fetched = TRUE
  AND ipfs_data IS NOT NULL
GROUP BY token_name, token_number, creator_did
ORDER BY count DESC;
```

### Scenario 3: Node Health Check

Monitor which nodes have healthy IPFS:

```sql
SELECT
    node_name,
    COUNT(*) as total_tokens,
    SUM(CASE WHEN ipfs_fetched THEN 1 ELSE 0 END) as ipfs_success,
    ROUND(100.0 * SUM(CASE WHEN ipfs_fetched THEN 1 ELSE 0 END) / COUNT(*), 2) as health_pct
FROM TokenRecords
GROUP BY node_name
ORDER BY health_pct DESC;
```

## Integration with Other Scripts

This script works alongside:

| Script | Purpose | Source | Target Table |
|--------|---------|--------|--------------|
| `sync_token_info.py` | IPFS token metadata | Single SQLite FTTokenTable → IPFS | TokenInfo |
| `sync_distributed_tokens.py` | Multi-node token records | Multiple SQLite TokensTable → IPFS | TokenRecords |

Both use the same PostgreSQL database but different tables!

## Best Practices

1. **Place ipfs executable** in same directory as script
2. **Ensure .ipfs directories** are accessible and healthy
3. **Run regularly** - Schedule periodic syncs
4. **Monitor logs** - Check for IPFS errors
5. **Tune workers** - Adjust based on your system
6. **Check IPFS health** - High failure rates indicate issues
7. **Archive old data** - Consider partitioning by synced_at

## Summary

This enhanced script provides:
- ✅ Complete token data (SQLite + IPFS) in one place
- ✅ Multi-node support with automatic .ipfs detection
- ✅ Parallel IPFS processing for speed
- ✅ Robust NULL/empty value handling
- ✅ Source tracking for audit and verification
- ✅ Efficient incremental syncs
- ✅ IPFS success/failure tracking
- ✅ Easy querying through PostgreSQL

Perfect for managing distributed Rubix deployments with full IPFS integration!
