# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Rubix Token Sync System** - a high-performance distributed token synchronization system that migrates token metadata from SQLite databases to PostgreSQL via IPFS. The system supports both single-node and multi-node distributed deployments with web-based administration.

**Key Components:**
- **Data Pipeline**: SQLite → IPFS → PostgreSQL
- **Single-node sync**: `sync_token_info.py` (3.4M+ tokens)
- **Multi-node sync**: `sync_distributed_tokens.py` (distributed databases)
- **Web UI**: pgAdmin 4 for database administration
- **Infrastructure**: Automated setup scripts for PostgreSQL + pgAdmin

## Development Commands

### Initial Setup
```bash
# Complete automated setup (Ubuntu/Linux)
cd /datadrive/Rubix
chmod +x setup_all.sh
./setup_all.sh
```

### Development Dependencies
```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Dependencies are minimal:
# - psycopg2-binary==2.9.9 (PostgreSQL adapter)
# - requests==2.31.0 (HTTP client for IP detection)
```

### Running the System
```bash
# Single-node token sync (primary script)
cd /datadrive/Rubix/Node/creator
python3 /datadrive/Rubix/sync_token_info.py

# Multi-node distributed sync
python3 /datadrive/Rubix/sync_distributed_tokens.py

# Monitor sync progress
tail -f /datadrive/Rubix/Node/creator/sync_token_info.log
```

### Database Operations
```bash
# Connect to PostgreSQL
sudo -u postgres psql -d rubix_tokens

# Quick progress check
sudo -u postgres psql -d rubix_tokens -c "SELECT COUNT(*) FROM TokenInfo;"

# Backup database
pg_dump -U postgres -d rubix_tokens > backup_$(date +%Y%m%d).sql
```

### Service Management
```bash
# PostgreSQL service
sudo systemctl status postgresql@17-main
sudo systemctl restart postgresql@17-main

# pgAdmin web interface
sudo systemctl status apache2
sudo systemctl restart apache2

# Access pgAdmin: http://SERVER_IP/pgadmin4
```

## Architecture Overview

### Data Flow Architecture
```
SQLite FTTokenTable (3.4M tokens)
    ↓ (batch read)
IPFS Network (`ipfs cat TOKEN_ID`)
    ↓ (parse: "NAME NUMBER DID")
PostgreSQL TokenInfo Table
    ↓ (web access)
pgAdmin 4 Web Interface
```

### Core Processing Pattern
```python
# High-level sync workflow (sync_token_info.py:main)
1. get_token_ids_from_sqlite() → List[token_ids]
2. process_batch_parallel() → Pool(NUM_WORKERS)
3. fetch_and_parse_token() → IPFS call + parsing
4. batch_insert_tokens() → PostgreSQL batch insert
5. Progress tracking + error handling
```

### Performance Configuration
Located in `sync_token_info.py:15-20`:
```python
NUM_WORKERS = cpu_count() * 2    # 16 workers on 8-core VM
BATCH_SIZE = 1000               # Records per batch
IPFS_TIMEOUT = 15               # Seconds per IPFS call
```

## Key Components

### Primary Scripts

**`sync_token_info.py`** (11,182 bytes) - Single-node sync
- **Entry Point**: `main()` function
- **Purpose**: Sync 3.4M+ tokens from SQLite → PostgreSQL via IPFS
- **Key Functions**:
  - `get_token_ids_from_sqlite()` - Retrieves token IDs from FTTokenTable
  - `fetch_and_parse_token()` - IPFS call + parsing (parallelizable)
  - `batch_insert_tokens()` - Batch PostgreSQL insert with conflict resolution
- **Configuration**: Hardcoded paths and connection strings (lines 15-30)

**`sync_distributed_tokens.py`** (21,163 bytes) - Multi-node sync
- **Entry Point**: `main()` function
- **Purpose**: Distributed sync across multiple Rubix nodes
- **Key Functions**:
  - `find_rubix_databases()` - Recursive database discovery
  - `process_database()` - SQLite extraction + IPFS parallel fetch
  - `update_processed_database()` - Metadata tracking
- **Features**: Source IP tracking, smart .ipfs detection, resumable operations

### Setup Scripts (Infrastructure as Code)
- **`setup_all.sh`** - Master orchestrator, runs all setup steps
- **`setup_postgres.sh`** - PostgreSQL 17 installation + configuration
- **`setup_pgadmin.sh`** - pgAdmin 4 web UI setup
- **`init_database.sh`** - Database schema creation + indexes
- **`update_sync_script.sh`** - Connection string configuration

### Database Schema

**TokenInfo Table** (single-node):
```sql
CREATE TABLE TokenInfo (
    token_id TEXT PRIMARY KEY,           -- IPFS token ID
    token_name TEXT NOT NULL,            -- Token name (e.g., "TRI")
    token_number INTEGER NOT NULL,       -- Token sequence number
    creator_did TEXT NOT NULL,           -- Creator DID
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
-- 4 performance indexes on token_name, creator_did, token_number, last_updated
```

**TokenRecords Table** (multi-node):
```sql
CREATE TABLE TokenRecords (
    id SERIAL PRIMARY KEY,
    source_ip TEXT NOT NULL,             -- VM public IP
    node_name TEXT NOT NULL,             -- Node identifier
    did TEXT, token_id TEXT,             -- From SQLite
    ipfs_data TEXT,                      -- Raw IPFS output
    ipfs_fetched BOOLEAN DEFAULT FALSE,  -- Success flag
    db_path TEXT NOT NULL,               -- Source database path
    synced_at TIMESTAMP DEFAULT NOW()
);
-- 6 indexes for querying by token_id, node_name, source_ip, etc.
```

## Important File Locations

### Configuration Files
- **`requirements.txt`** - Python dependencies (psycopg2-binary, requests)
- **`/datadrive/Rubix/postgres_connection.txt`** - PostgreSQL credentials ⚠️ Sensitive
- **`/datadrive/Rubix/pgadmin_access.txt`** - pgAdmin login ⚠️ Sensitive

### Runtime Paths
- **PostgreSQL Data**: `/datadrive/Rubix/postgres`
- **Sync Logs**: `/datadrive/Rubix/Node/creator/sync_token_info.log`
- **SQLite Source**: `/datadrive/Rubix/Node/creator/Rubix/rubix.db`
- **IPFS Directory**: `./Node/creator/.ipfs`

### Documentation
- **`SETUP_GUIDE.md`** (11,327 bytes) - Comprehensive installation guide
- **`QUICK_REFERENCE.md`** (3,359 bytes) - Daily operations reference
- **`DISTRIBUTED_TOKENS_GUIDE.md`** (16,332 bytes) - Multi-node documentation
- **`DISTRIBUTED_QUICK_REF.md`** (3,334 bytes) - Distributed quick reference

## Development Patterns

### Error Handling
```python
# Pattern: Graceful degradation with logging
try:
    result = subprocess.run([IPFS_COMMAND, 'cat', token_id],
                          capture_output=True, text=True, timeout=IPFS_TIMEOUT)
    if result.returncode == 0:
        return parse_ipfs_output(result.stdout.strip())
except subprocess.TimeoutExpired:
    logger.warning(f"IPFS timeout for token {token_id}")
    return None  # Skip token, continue processing
```

### Batch Processing
```python
# Pattern: Batch inserts with conflict resolution
INSERT_QUERY = """
INSERT INTO TokenInfo (token_id, token_name, token_number, creator_did)
VALUES %s
ON CONFLICT (token_id) DO UPDATE SET
    token_name = EXCLUDED.token_name,
    last_updated = NOW()
"""
execute_values(cursor, INSERT_QUERY, batch_data, page_size=1000)
```

### Multiprocessing
```python
# Pattern: Pool-based parallel processing
with Pool(processes=NUM_WORKERS) as pool:
    results = pool.map(fetch_and_parse_token, token_ids_batch)
    successful_tokens = [token for token in results if token is not None]
```

## Performance Characteristics

### Expected Throughput
- **Conservative**: 50 tokens/sec (19 hours for 3.4M tokens)
- **Typical**: 100 tokens/sec (9.5 hours for 3.4M tokens)
- **Optimized**: 200 tokens/sec (4.8 hours for 3.4M tokens)

### Tuning Parameters
```python
# Faster IPFS node
NUM_WORKERS = cpu_count() * 3
IPFS_TIMEOUT = 10

# Slower/shared resources
NUM_WORKERS = cpu_count()
BATCH_SIZE = 2000
```

### Storage Requirements
- ~800 bytes per token record with IPFS data
- 3.4M records ≈ 2.7 GB total storage

## Security Considerations

⚠️ **Sensitive Files** (restrict access):
- `/datadrive/Rubix/postgres_connection.txt` - Database credentials
- `/datadrive/Rubix/pgadmin_access.txt` - Web UI credentials

**Known Issues**:
- Hardcoded connection strings in `sync_token_info.py:25-30`
- Firewall rules open globally (ports 5432, 80)
- No SSL/TLS configuration by default

## Integration Points

### External Dependencies
- **IPFS Node**: Must be running at `./Node/creator/.ipfs`
- **PostgreSQL 17**: Custom installation at `/datadrive/Rubix/postgres`
- **SQLite**: Source databases (read-only access)
- **Apache HTTP**: Web server for pgAdmin 4

### Network Services
- **PostgreSQL**: Port 5432 (database access)
- **pgAdmin Web UI**: Port 80 (HTTP access)
- **IPFS API**: Local socket communication

## Common Development Tasks

### Adding New Token Fields
1. Modify database schema in `init_database.sh`
2. Update `TokenInfo` table structure
3. Modify `batch_insert_tokens()` in sync scripts
4. Add parsing logic in `fetch_and_parse_token()`
5. Update SQL queries in documentation

### Performance Optimization
1. Adjust `NUM_WORKERS`, `BATCH_SIZE`, `IPFS_TIMEOUT` in sync scripts
2. Monitor with `htop` and PostgreSQL query logs
3. Add database indexes for new query patterns
4. Consider connection pooling for high throughput

### Troubleshooting Sync Issues
1. Check IPFS connectivity: `./ipfs version`
2. Verify PostgreSQL connection: `psql -h localhost -U postgres -d rubix_tokens`
3. Monitor logs: `tail -f /datadrive/Rubix/Node/creator/sync_token_info.log`
4. Check service status: `systemctl status postgresql@17-main`

### Monitoring Sync Progress
```sql
-- Progress tracking queries
SELECT COUNT(*) FROM TokenInfo;                    -- Total synced
SELECT COUNT(*) FROM TokenInfo
WHERE last_updated > NOW() - INTERVAL '1 hour';   -- Recent syncs
SELECT COUNT(*) / 60.0 FROM TokenInfo
WHERE last_updated > NOW() - INTERVAL '1 hour';   -- Tokens/minute
```