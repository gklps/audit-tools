# Rubix Token Sync System - Complete Setup Guide

This guide will help you set up a self-hosted PostgreSQL database with pgAdmin 4 web interface on your Ubuntu VM, and configure the Python sync script to migrate 3.4M+ tokens from SQLite to PostgreSQL.

## Overview

The system consists of:
- **PostgreSQL 17**: Self-hosted database on `/datadrive/Rubix/postgres`
- **pgAdmin 4**: Web-based database administration interface
- **sync_token_info.py**: Parallel Python script to sync tokens from SQLite → PostgreSQL via IPFS
- **TokenInfo Table**: Stores token metadata (token_id, token_name, token_number, creator_did)

## Prerequisites

Before starting, ensure you have:

- ✅ Ubuntu VM with sudo access
- ✅ `/datadrive/Rubix` directory exists and is writable
- ✅ IPFS node configured at `./Node/creator/.ipfs`
- ✅ SQLite database at `/datadrive/Rubix/Node/creator/Rubix/rubix.db`
- ✅ Python 3.7+ installed
- ✅ `psycopg2-binary` Python package (`pip3 install psycopg2-binary`)

## Quick Start (Automated Setup)

### Option 1: Complete Automated Setup

```bash
# Transfer all files to your Ubuntu VM
scp setup_*.sh init_database.sh update_sync_script.sh setup_all.sh sync_token_info.py your-user@your-vm-ip:/datadrive/Rubix/

# SSH into your VM
ssh your-user@your-vm-ip

# Navigate to the directory
cd /datadrive/Rubix

# Run the master setup script
chmod +x setup_all.sh
./setup_all.sh
```

The script will prompt you for:
1. PostgreSQL `postgres` user password (choose a strong password)
2. pgAdmin login email
3. pgAdmin login password

**Estimated time**: 15-30 minutes

### Option 2: Step-by-Step Manual Setup

If you prefer to run each step manually:

```bash
# 1. Install PostgreSQL
chmod +x setup_postgres.sh
./setup_postgres.sh

# 2. Install pgAdmin 4
chmod +x setup_pgadmin.sh
./setup_pgadmin.sh

# 3. Initialize Database
chmod +x init_database.sh
./init_database.sh

# 4. Update Sync Script
chmod +x update_sync_script.sh
./update_sync_script.sh
```

## What Each Script Does

### 1. `setup_postgres.sh`
- Installs PostgreSQL 17 from official repository
- Creates custom data directory at `/datadrive/Rubix/postgres`
- Configures PostgreSQL for remote connections
- Sets up password authentication
- Creates `rubix_tokens` database
- Opens firewall port 5432
- Saves connection details to `postgres_connection.txt`

### 2. `setup_pgadmin.sh`
- Installs pgAdmin 4 in web mode
- Configures Apache web server
- Sets up pgAdmin authentication
- Enables remote access on port 80
- Saves access details to `pgadmin_access.txt`

### 3. `init_database.sh`
- Creates `TokenInfo` table with proper schema
- Adds indexes for performance
- Sets up auto-update triggers for `last_updated` column
- Displays table structure

### 4. `update_sync_script.sh`
- Updates `sync_token_info.py` connection string
- Configures script to use local PostgreSQL
- Creates backup of original script

## Database Schema

The `TokenInfo` table structure:

```sql
CREATE TABLE TokenInfo (
    token_id TEXT PRIMARY KEY,           -- IPFS token ID
    token_name TEXT NOT NULL,            -- Token name (e.g., "TRI")
    token_number INTEGER NOT NULL,       -- Token number
    creator_did TEXT NOT NULL,           -- Creator DID
    last_updated TIMESTAMP,              -- Auto-updated on changes
    created_at TIMESTAMP                 -- Record creation time
);
```

**Indexes** (for fast queries):
- `idx_token_name` on `token_name`
- `idx_creator_did` on `creator_did`
- `idx_token_number` on `token_number`
- `idx_last_updated` on `last_updated`

## Using the System

### Accessing pgAdmin 4

1. **Open your browser** and navigate to:
   ```
   http://YOUR_VM_IP/pgadmin4
   ```

2. **Login** with the credentials from `/datadrive/Rubix/pgadmin_access.txt`

3. **Add PostgreSQL Server**:
   - Right-click **Servers** → **Register** → **Server**
   - **General** tab:
     - Name: `Rubix Local PostgreSQL`
   - **Connection** tab:
     - Host: `localhost` (or your VM IP)
     - Port: `5432`
     - Maintenance database: `rubix_tokens`
     - Username: `postgres`
     - Password: [your postgres password]
     - Save password: ✅ Yes
   - Click **Save**

4. **View Data**:
   - Navigate: Servers → Rubix Local PostgreSQL → Databases → rubix_tokens → Schemas → public → Tables → TokenInfo
   - Right-click **TokenInfo** → **View/Edit Data** → **All Rows**

### Running the Token Sync

Start the parallel sync process:

```bash
# Navigate to IPFS directory
cd /datadrive/Rubix/Node/creator

# Run the sync script
python3 /datadrive/Rubix/sync_token_info.py
```

**Expected output:**
```
================================================================================
Starting PARALLEL Token Info Sync Service (Workers: 16)
================================================================================
Retrieved 3,448,000 token IDs from SQLite
Processing 3,448,000 tokens with 16 parallel workers
...
Progress: 0.1% | Speed: 88.9 tokens/sec | ETA: 645.3 minutes
```

### Monitoring Progress

**Watch the log file:**
```bash
tail -f /datadrive/Rubix/Node/creator/sync_token_info.log
```

**Check progress in pgAdmin:**
```sql
SELECT COUNT(*) as synced_tokens FROM TokenInfo;
```

**View recent syncs:**
```sql
SELECT * FROM TokenInfo
ORDER BY last_updated DESC
LIMIT 100;
```

**Check token name distribution:**
```sql
SELECT token_name, COUNT(*) as count
FROM TokenInfo
GROUP BY token_name
ORDER BY count DESC;
```

## Performance Tuning

The sync script is optimized for 3.4M+ tokens:

### Current Configuration (in `sync_token_info.py`)

```python
NUM_WORKERS = cpu_count() * 2  # 16 workers on 8-core VM
BATCH_SIZE = 1000              # Insert 1000 tokens per batch
IPFS_TIMEOUT = 15              # 15-second timeout per token
```

### Tuning for Your Environment

**For faster IPFS node:**
- Increase `NUM_WORKERS` to `cpu_count() * 3` or `cpu_count() * 4`
- Decrease `IPFS_TIMEOUT` to `10`

**For slower/shared resources:**
- Decrease `NUM_WORKERS` to `cpu_count()`
- Increase `BATCH_SIZE` to `2000` or `5000`

**Expected Performance:**
- **Conservative**: ~50 tokens/sec = 19 hours
- **Typical**: ~100 tokens/sec = 9.5 hours
- **Optimized**: ~200 tokens/sec = 4.8 hours

### Resume Capability

The script uses `ON CONFLICT DO UPDATE`, so if interrupted:
- Already synced tokens are skipped
- New/updated tokens are processed
- Just restart the script to resume

## Troubleshooting

### PostgreSQL Issues

**Can't connect to PostgreSQL:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql@17-main

# Check logs
sudo tail -f /datadrive/Rubix/postgres/log/postgresql-*.log

# Restart PostgreSQL
sudo systemctl restart postgresql@17-main
```

**Connection refused:**
- Check firewall: `sudo ufw status`
- Verify `listen_addresses = '*'` in `/datadrive/Rubix/postgres/postgresql.conf`
- Check `pg_hba.conf` has correct authentication rules

### pgAdmin Issues

**Can't access pgAdmin web interface:**
```bash
# Check Apache status
sudo systemctl status apache2

# Restart Apache
sudo systemctl restart apache2

# Check Apache logs
sudo tail -f /var/log/apache2/error.log
```

**Forgot pgAdmin password:**
```bash
# Reset pgAdmin password
sudo /usr/pgadmin4/bin/setup-web.sh
```

### Sync Script Issues

**IPFS timeout errors:**
- Increase `IPFS_TIMEOUT` in script
- Check IPFS node: `./ipfs version`
- Check IPFS daemon: `./ipfs swarm peers`

**Database connection errors:**
- Verify connection string in script
- Check postgres password
- Test connection: `psql -h localhost -U postgres -d rubix_tokens`

**Memory issues:**
- Decrease `NUM_WORKERS`
- Decrease `BATCH_SIZE`
- Monitor: `htop` or `free -h`

## Security Recommendations

### Essential Security Steps

1. **Change Default Postgres Password**:
   ```bash
   sudo -u postgres psql
   ALTER USER postgres WITH PASSWORD 'new_strong_password';
   \q
   ```

2. **Restrict PostgreSQL Access** (if not needed from internet):
   Edit `/datadrive/Rubix/postgres/pg_hba.conf`:
   ```
   # Change from:
   host    all    all    0.0.0.0/0    md5

   # To (local network only):
   host    all    all    192.168.1.0/24    md5
   ```

3. **Use SSL for PostgreSQL** (production environments):
   - Generate SSL certificates
   - Configure `postgresql.conf` for SSL
   - Update connection strings to use `sslmode=require`

4. **Secure pgAdmin with HTTPS**:
   - Install Certbot: `sudo apt install certbot python3-certbot-apache`
   - Get SSL certificate: `sudo certbot --apache`

5. **Firewall Configuration**:
   ```bash
   # Only allow specific IPs
   sudo ufw allow from YOUR_IP to any port 5432
   sudo ufw allow from YOUR_IP to any port 80
   ```

## File Locations Reference

| Item | Location |
|------|----------|
| PostgreSQL Data | `/datadrive/Rubix/postgres` |
| PostgreSQL Config | `/datadrive/Rubix/postgres/postgresql.conf` |
| Authentication Config | `/datadrive/Rubix/postgres/pg_hba.conf` |
| Connection Details | `/datadrive/Rubix/postgres_connection.txt` |
| pgAdmin Access Info | `/datadrive/Rubix/pgadmin_access.txt` |
| Sync Script | `/datadrive/Rubix/sync_token_info.py` |
| Sync Logs | `/datadrive/Rubix/Node/creator/sync_token_info.log` |
| SQLite Database | `/datadrive/Rubix/Node/creator/Rubix/rubix.db` |

## Useful SQL Queries

### Monitor Sync Progress

```sql
-- Total synced tokens
SELECT COUNT(*) as total_tokens FROM TokenInfo;

-- Tokens by name
SELECT token_name, COUNT(*) as count
FROM TokenInfo
GROUP BY token_name
ORDER BY count DESC;

-- Recent syncs (last 1 hour)
SELECT COUNT(*) as recent_syncs
FROM TokenInfo
WHERE last_updated > NOW() - INTERVAL '1 hour';

-- Sync rate (tokens per minute in last hour)
SELECT COUNT(*) / 60.0 as tokens_per_minute
FROM TokenInfo
WHERE last_updated > NOW() - INTERVAL '1 hour';

-- Top creators
SELECT creator_did, COUNT(*) as token_count
FROM TokenInfo
GROUP BY creator_did
ORDER BY token_count DESC
LIMIT 10;

-- Database size
SELECT pg_size_pretty(pg_database_size('rubix_tokens')) as database_size;

-- Table size
SELECT pg_size_pretty(pg_total_relation_size('TokenInfo')) as table_size;
```

## Maintenance Tasks

### Backup Database

```bash
# Backup to SQL file
pg_dump -U postgres -d rubix_tokens > backup_$(date +%Y%m%d).sql

# Backup to compressed format
pg_dump -U postgres -d rubix_tokens -Fc > backup_$(date +%Y%m%d).dump
```

### Restore Database

```bash
# From SQL file
psql -U postgres -d rubix_tokens < backup_20250127.sql

# From compressed format
pg_restore -U postgres -d rubix_tokens backup_20250127.dump
```

### Vacuum and Analyze (performance maintenance)

```bash
sudo -u postgres psql -d rubix_tokens -c "VACUUM ANALYZE TokenInfo;"
```

## Support

If you encounter issues:

1. Check the log files (locations listed above)
2. Verify all prerequisites are met
3. Review the troubleshooting section
4. Check PostgreSQL and pgAdmin documentation

## Summary

After setup, your system will have:
- ✅ Self-hosted PostgreSQL database with 3.4M+ token records
- ✅ pgAdmin 4 web interface for remote database access
- ✅ Automated parallel sync from SQLite → PostgreSQL
- ✅ Persistent storage on `/datadrive`
- ✅ Indexed queries for fast lookups
- ✅ One consistent database for all operations

**Total Setup Time**: 15-30 minutes
**Initial Sync Time**: 5-15 hours (resumable)
**Storage Required**: ~500MB - 1GB for 3.4M tokens
