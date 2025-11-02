# 🚀 Rubix Token Sync - Enhanced Edition

A high-performance distributed token synchronization system that migrates token metadata from SQLite databases to Azure SQL Database via IPFS with comprehensive monitoring and real-time Telegram notifications.

## ✨ Features

- **🗄️ Azure SQL Database Integration** - Optimized for cloud-scale operations
- **📱 Real-time Telegram Notifications** - Multi-VM monitoring with machine identification
- **📊 Comprehensive Audit Logging** - Structured logs with correlation tracking
- **⚡ High Performance** - Bulk operations with connection pooling (300-1,000 records/sec)
- **🔄 Error Recovery** - 3-tier fallback mechanisms with retry logic
- **📈 Performance Analytics** - Built-in log analysis and metrics export
- **🖥️ Multi-VM Coordination** - Centralized monitoring across multiple machines
- **🛠️ Easy Deployment** - Single-script setup with automated configuration

## 🎯 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# 1. Download or clone this repository
git clone <repository-url>
cd rubix-token-sync

# 2. Run the automated setup
chmod +x setup.sh
./setup.sh

# 3. Run the sync
cd /datadrive/Rubix
./scripts/run_sync.sh
```

### Option 2: Manual Setup

```bash
# 1. Copy files to your VM
scp -r * user@your-vm:/datadrive/Rubix/

# 2. Install dependencies
cd /datadrive/Rubix
sudo apt update
sudo apt install python3-pip -y
pip3 install -r requirements.txt

# 3. Configure (edit with your credentials)
cp config/azure_sql_connection_template.txt azure_sql_connection.txt
cp config/telegram_config_template.json telegram_config.json

# 4. Run
python3 sync_distributed_tokens.py
```

## 📦 What's Included

```
rubix-token-sync/
├── 🐍 Core Application
│   ├── sync_distributed_tokens.py      # Main sync application
│   ├── telegram_notifier.py            # Telegram bot integration
│   ├── log_analyzer.py                 # Performance analysis tool
│   └── requirements.txt                # Python dependencies
│
├── 🛠️ Setup & Deployment
│   ├── setup.sh                        # Automated installation script
│   ├── run_sync.sh                     # Smart run script with tests
│   └── monitor.sh                      # Real-time monitoring dashboard
│
├── ⚙️ Configuration Templates
│   ├── azure_sql_connection_template.txt
│   └── telegram_config_template.json
│
└── 📚 Documentation
    ├── README.md                       # This file
    ├── AZURE_SQL_MIGRATION_GUIDE.md    # Migration documentation
    └── DETAILED_LOGGING_GUIDE.md       # Logging & monitoring guide
```

## 📱 Telegram Integration

### Pre-configured Bot
- **Bot**: `@rbtaudit_bot`
- **Token**: `8391226270:AAFv1p1nHf6gcEgXI7diiikczAW-I5Gg1KE`
- **Group**: [Audit Bot](https://t.me/+rHRidAoAUBViMjM1)

### Machine Identification
Each VM is automatically identified by:
```
🖥️ Prod-VM-1 (203.0.113.10)
🖥️ Prod-VM-2 (203.0.113.11)
🖥️ Backup-VM-1 (198.51.100.5)
```

### Notification Types
- **🚀 Startup**: Sync process begins
- **📊 Progress**: Every 10 minutes with metrics
- **❌ Errors**: Real-time error alerts
- **📁 Database Completion**: Large database milestones
- **✅ Final Completion**: Success summary with statistics

## 🏗️ Architecture

### Data Flow
```
SQLite (Rubix/rubix.db) → IPFS Network → Azure SQL Database → Telegram Notifications
     ↓                        ↓                ↓                    ↓
   Token IDs              Metadata          Structured           Real-time
   & Status              Retrieval           Storage             Monitoring
```

### Performance Configuration
```python
# Optimized for Azure SQL Database
BATCH_SIZE = 2000              # Records per batch
BULK_INSERT_SIZE = 10000       # Bulk operation threshold
NUM_IPFS_WORKERS = cpu_count() * 2    # Parallel IPFS calls
CONNECTION_POOL_SIZE = 10      # SQL connection pool
RETRY_ATTEMPTS = 3             # Error recovery attempts
```

## 📊 Expected Performance

| Environment | Processing Rate | IPFS Success | SQL Success |
|-------------|----------------|--------------|-------------|
| **Conservative** | 300-500/sec | >95% | >99% |
| **Typical** | 500-800/sec | >97% | >99.5% |
| **Optimized** | 800-1,000/sec | >98% | >99.9% |

## 🖥️ Multi-VM Deployment

### 1. Setup Each VM
```bash
# VM 1
./setup.sh
# Configure machine_name: "Prod-VM-1"

# VM 2
./setup.sh
# Configure machine_name: "Prod-VM-2"

# VM 3
./setup.sh
# Configure machine_name: "Prod-VM-3"
```

### 2. Coordinated Monitoring
All VMs report to the same Telegram group:
```
🖥️ Prod-VM-1 (203.0.113.10)   📊 Progress: 45.2% | Rate: 456/sec
🖥️ Prod-VM-2 (203.0.113.11)   📊 Progress: 67.8% | Rate: 387/sec
🖥️ Prod-VM-3 (203.0.113.12)   ❌ IPFS timeout error
```

## 🔧 Scripts Overview

### `setup.sh` - Automated Installation
- ✅ System dependency installation
- ✅ Python environment setup
- ✅ Application deployment
- ✅ Configuration wizard
- ✅ Connection testing
- ✅ Optional systemd service creation

**Usage:**
```bash
./setup.sh                    # Standard installation
./setup.sh --venv            # Use virtual environment
./setup.sh --skip-deps       # Skip system packages
```

### `run_sync.sh` - Smart Runner
- ✅ Prerequisites validation
- ✅ Connection testing
- ✅ System information display
- ✅ Background execution support
- ✅ Comprehensive error reporting

**Usage:**
```bash
./scripts/run_sync.sh                # Interactive run
./scripts/run_sync.sh --test-only    # Test connections only
./scripts/run_sync.sh --background   # Run in background
```

### `monitor.sh` - Real-time Dashboard
- ✅ Process status monitoring
- ✅ System metrics (CPU, memory, disk)
- ✅ Sync progress tracking
- ✅ Error summary and analysis
- ✅ Connection status checks
- ✅ Interactive controls

**Usage:**
```bash
./scripts/monitor.sh              # Single shot view
./scripts/monitor.sh --interactive # Live dashboard
```

## 📋 System Requirements

### Minimum Requirements
- **OS**: Ubuntu 18.04+ or Debian 10+
- **Python**: 3.8+
- **Memory**: 4GB RAM
- **Storage**: 10GB free space
- **Network**: Internet access for Azure SQL Database

### Recommended Requirements
- **OS**: Ubuntu 20.04 LTS
- **Python**: 3.9+
- **Memory**: 8GB RAM
- **Storage**: 50GB free space (for logs)
- **CPU**: 4+ cores for optimal IPFS parallelization

### Dependencies (Auto-installed)
- Microsoft ODBC Driver 17 for SQL Server
- Python packages: `pyodbc`, `pandas`, `requests`, `python-telegram-bot`

## 🛡️ Security Features

- **🔐 Encrypted Connections**: SSL/TLS for all database connections
- **🔑 Secure Credentials**: Protected configuration files (600 permissions)
- **🔒 Connection Pooling**: Secure, reusable database connections
- **📝 Audit Trail**: Complete operation logging with correlation IDs
- **🚫 Error Sanitization**: Sensitive data excluded from logs

## 📈 Monitoring & Analytics

### Real-time Monitoring
```bash
# Live main log
tail -f logs/sync_main_$(date +%Y%m%d).log

# Live error log
tail -f logs/sync_errors_$(date +%Y%m%d).log

# Performance analysis
python3 log_analyzer.py --hours 24
```

### Log Structure
```
logs/
├── sync_main_YYYYMMDD.log       # Main application (100MB, 10 backups)
├── sync_debug_YYYYMMDD.log      # Debug details (200MB, 5 backups)
├── sync_errors_YYYYMMDD.log     # Errors only (50MB, 50 backups)
├── sync_ipfs_YYYYMMDD.log       # IPFS operations (50MB, 10 backups)
├── sync_sql_YYYYMMDD.log        # Database operations (50MB, 10 backups)
├── sync_validation_YYYYMMDD.log # Data validation (50MB, 10 backups)
└── sync_sync_YYYYMMDD.log       # Sync coordination (50MB, 10 backups)
```

### Performance Analytics
```bash
# Generate comprehensive report
python3 log_analyzer.py --hours 24

# Export metrics to CSV
python3 log_analyzer.py --export-csv metrics.csv --hours 48

# Error analysis only
python3 log_analyzer.py --errors-only --hours 12
```

## 🚨 Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Test Azure SQL Database
python3 -c "
from sync_distributed_tokens import init_connection_pool
pool = init_connection_pool()
print('✅ Database connection successful!')
"

# Test Telegram
python3 -c "
from telegram_notifier import init_telegram_notifier
notifier = init_telegram_notifier()
print('✅ Telegram connection successful!' if notifier.test_connection() else '❌ Failed')
"
```

#### Performance Issues
```bash
# Check system resources
./scripts/monitor.sh

# Analyze performance patterns
python3 log_analyzer.py --hours 6

# Check IPFS connectivity
./ipfs version && ./ipfs id
```

#### Service Management
```bash
# Check systemd service
sudo systemctl status rubix-sync

# View service logs
sudo journalctl -u rubix-sync -f

# Restart service
sudo systemctl restart rubix-sync
```

## 🔄 Upgrade Path

### From Previous Version
1. **Backup**: `cp -r /datadrive/Rubix /datadrive/Rubix.backup`
2. **Deploy**: Copy new files to installation directory
3. **Configure**: Update configuration files with new options
4. **Test**: Run `./scripts/run_sync.sh --test-only`
5. **Deploy**: Start enhanced sync

### Configuration Migration
- Azure SQL Database connection strings are backward compatible
- Telegram configuration will be auto-migrated
- Log files will continue from existing rotation

## 📞 Support

### Documentation
- **Migration Guide**: `AZURE_SQL_MIGRATION_GUIDE.md`
- **Logging Guide**: `DETAILED_LOGGING_GUIDE.md`
- **Setup Logs**: Check `setup.log` for installation issues

### Monitoring Channels
- **Telegram Group**: Real-time notifications and multi-VM coordination
- **Log Files**: Comprehensive audit trail with structured logging
- **Monitor Dashboard**: `./scripts/monitor.sh --interactive`

### Performance Optimization
- **Increase Workers**: For faster IPFS nodes, increase `NUM_IPFS_WORKERS`
- **Batch Tuning**: Adjust `BATCH_SIZE` and `BULK_INSERT_SIZE` for your VM
- **Connection Pool**: Increase `CONNECTION_POOL_SIZE` for high throughput

---

## 🎉 Ready to Deploy!

Your enhanced Rubix Token Sync system is now ready for production deployment with enterprise-grade logging, monitoring, and multi-VM coordination capabilities.

**Start your sync journey:**
```bash
chmod +x setup.sh && ./setup.sh
```