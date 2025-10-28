# Rubix Token Sync - Quick Reference Card

## Installation (One-Time Setup)

```bash
cd /datadrive/Rubix
chmod +x setup_all.sh
./setup_all.sh
```

## Daily Operations

### Start Token Sync
```bash
cd /datadrive/Rubix/Node/creator
python3 /datadrive/Rubix/sync_token_info.py
```

### Monitor Progress
```bash
# Watch live log
tail -f /datadrive/Rubix/Node/creator/sync_token_info.log

# Check token count
sudo -u postgres psql -d rubix_tokens -c "SELECT COUNT(*) FROM TokenInfo;"
```

### Access pgAdmin
```
http://YOUR_VM_IP/pgadmin4
```
Credentials in: `/datadrive/Rubix/pgadmin_access.txt`

## PostgreSQL Commands

### Connect to Database
```bash
sudo -u postgres psql -d rubix_tokens
```

### Useful Queries
```sql
-- Total tokens
SELECT COUNT(*) FROM TokenInfo;

-- Sync progress (last hour)
SELECT COUNT(*) FROM TokenInfo
WHERE last_updated > NOW() - INTERVAL '1 hour';

-- Tokens by name
SELECT token_name, COUNT(*) FROM TokenInfo
GROUP BY token_name ORDER BY COUNT(*) DESC;
```

### Backup Database
```bash
pg_dump -U postgres -d rubix_tokens > backup_$(date +%Y%m%d).sql
```

## Service Management

### PostgreSQL
```bash
# Status
sudo systemctl status postgresql@17-main

# Restart
sudo systemctl restart postgresql@17-main

# View logs
sudo tail -f /datadrive/Rubix/postgres/log/postgresql-*.log
```

### pgAdmin / Apache
```bash
# Status
sudo systemctl status apache2

# Restart
sudo systemctl restart apache2

# View logs
sudo tail -f /var/log/apache2/error.log
```

## Troubleshooting

### Sync Script Errors
```bash
# Check connection file exists
cat /datadrive/Rubix/postgres_connection.txt

# Test PostgreSQL connection
psql -h localhost -U postgres -d rubix_tokens

# Check IPFS
cd /datadrive/Rubix/Node/creator
./ipfs version
```

### PostgreSQL Won't Start
```bash
# Check data directory permissions
ls -la /datadrive/Rubix/postgres

# Should be: drwx------ postgres postgres

# Fix if needed
sudo chown -R postgres:postgres /datadrive/Rubix/postgres
sudo chmod 700 /datadrive/Rubix/postgres
```

### Can't Access pgAdmin
```bash
# Check Apache is running
sudo systemctl status apache2

# Check firewall
sudo ufw status

# Open port if needed
sudo ufw allow 80/tcp
```

## Performance Tuning

Edit `/datadrive/Rubix/sync_token_info.py`:

```python
NUM_WORKERS = cpu_count() * 2  # Increase for faster sync
BATCH_SIZE = 1000              # Increase to 2000-5000
IPFS_TIMEOUT = 15              # Decrease to 10 for faster failures
```

## Important File Locations

| What | Where |
|------|-------|
| PostgreSQL Data | `/datadrive/Rubix/postgres` |
| Sync Script | `/datadrive/Rubix/sync_token_info.py` |
| Sync Logs | `/datadrive/Rubix/Node/creator/sync_token_info.log` |
| PG Connection | `/datadrive/Rubix/postgres_connection.txt` |
| pgAdmin Access | `/datadrive/Rubix/pgadmin_access.txt` |

## Expected Performance

- **Speed**: 50-200 tokens/second
- **Duration**: 5-15 hours for 3.4M tokens
- **Storage**: ~500MB - 1GB

## Emergency Stops

```bash
# Stop sync script
Ctrl+C (in running terminal)
# or
pkill -f sync_token_info.py

# Stop PostgreSQL
sudo systemctl stop postgresql@17-main

# Stop pgAdmin
sudo systemctl stop apache2
```

## Get Help

```bash
# View full setup guide
less /datadrive/Rubix/SETUP_GUIDE.md

# Check connection details
cat /datadrive/Rubix/postgres_connection.txt
cat /datadrive/Rubix/pgadmin_access.txt
```
