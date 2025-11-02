# Distributed Token Sync - Quick Reference

## Quick Start

```bash
# Install dependencies
pip3 install requests psycopg2-binary

# Run from directory to scan
cd /datadrive
python3 /path/to/sync_distributed_tokens.py
```

## What It Does

- Scans for all `*/Rubix/rubix.db` files recursively
- Reads TokensTable from each SQLite database
- Syncs to PostgreSQL TokenRecords table
- Tracks source VM IP and database path
- Only re-processes modified databases

## Usage

```bash
# Scan from /datadrive
cd /datadrive
python3 sync_distributed_tokens.py

# Scan from current directory
cd /any/directory
python3 sync_distributed_tokens.py

# Monitor progress
tail -f sync_distributed_tokens.log
```

## PostgreSQL Tables

### TokenRecords
Stores all token data with source tracking:
- source_ip, did, token_id
- created_at, updated_at, token_status
- parent_token_id, token_value
- db_path, db_last_modified, synced_at

### ProcessedDatabases
Tracks which databases have been synced:
- db_path, last_modified, last_processed, record_count

## Useful Queries

```sql
-- Total records
SELECT COUNT(*) FROM TokenRecords;

-- Tokens by source
SELECT source_ip, COUNT(*) FROM TokenRecords
GROUP BY source_ip;

-- Tokens by database
SELECT db_path, COUNT(*) FROM TokenRecords
GROUP BY db_path;

-- Recently synced
SELECT * FROM TokenRecords
WHERE synced_at > NOW() - INTERVAL '1 hour'
ORDER BY synced_at DESC;

-- Processing history
SELECT * FROM ProcessedDatabases
ORDER BY last_processed DESC;

-- Find duplicates
SELECT token_id, COUNT(*) as count
FROM TokenRecords
WHERE token_id IS NOT NULL
GROUP BY token_id
HAVING COUNT(*) > 1;
```

## View in pgAdmin

1. Open `http://YOUR_IP/pgadmin4`
2. Navigate to: rubix_tokens → Schemas → public → Tables → TokenRecords
3. Right-click → View/Edit Data → All Rows

## Configuration

Edit script to customize:

```python
POSTGRES_CONNECTION_STRING = 'postgresql://...'
NUM_WORKERS = cpu_count()  # Parallel workers
BATCH_SIZE = 1000          # Records per batch
```

## Scheduling

```bash
# Run every 6 hours via cron
crontab -e

# Add:
0 */6 * * * cd /datadrive && python3 /path/to/sync_distributed_tokens.py
```

## Troubleshooting

```bash
# Find databases manually
find /datadrive -name "rubix.db" -path "*/Rubix/*"

# Check PostgreSQL
sudo systemctl status postgresql@17-main

# Test connection
psql -h localhost -U postgres -d rubix_tokens

# View logs
tail -f sync_distributed_tokens.log
```

## Key Features

✅ Smart sync - only processes modified databases
✅ Source tracking - records VM IP for each token
✅ Duplicate handling - preserves all records
✅ Resumable - safe to interrupt and restart
✅ Fast - parallel processing of multiple databases

## File Locations

| Item | Location |
|------|----------|
| Script | `/datadrive/audit-tools/sync_distributed_tokens.py` |
| Log | `./sync_distributed_tokens.log` (where run from) |
| Postgres Connection | `/datadrive/Rubix/postgres_connection.txt` |

## Two Scripts, Two Purposes

| Script | Purpose | Source | Target Table |
|--------|---------|--------|--------------|
| `sync_token_info.py` | IPFS token metadata | SQLite FTTokenTable → IPFS | TokenInfo |
| `sync_distributed_tokens.py` | Distributed token records | Multiple SQLite TokensTable | TokenRecords |

Both use same PostgreSQL database, different tables!
