# Rubix Token Sync - Executable Distribution

Cross-platform executable for Rubix distributed token synchronization that runs on any OS without installation.

## 🚀 Quick Start

### Download and Run
1. Download the appropriate executable for your system:
   - **Windows**: `RubixTokenSync.exe`
   - **macOS**: `RubixTokenSync` (may be in a `.app` bundle)
   - **Linux**: `RubixTokenSync`

2. **Run the executable**:
   ```bash
   # Windows
   RubixTokenSync.exe

   # macOS/Linux
   ./RubixTokenSync
   ```

3. **First-time setup**: The tool will guide you through:
   - Setting up Azure SQL Database credentials
   - Configuring Telegram notifications (pre-configured)
   - Testing connections

4. **Start syncing**: Choose from the interactive menu options

## 📋 Features

### ✅ **Zero Installation Required**
- Bundles all dependencies (~50MB executable)
- Works on clean systems without Python or packages
- Single file distribution

### ✅ **Interactive Setup**
- Guided credential configuration
- System compatibility checking
- Connection testing
- User-friendly menus

### ✅ **Advanced Token Sync**
- Per-node IPFS detection and binary discovery
- Distributed database processing (500+ nodes)
- Azure SQL Database integration
- Real-time Telegram notifications
- Comprehensive audit logging

### ✅ **Cross-Platform Compatibility**
- **Windows**: Windows 10+ (64-bit)
- **macOS**: macOS 10.14+ (64-bit)
- **Linux**: Ubuntu 18.04+, CentOS 7+, or equivalent (64-bit)

## 🖥️ Interactive Mode (Default)

When you run the executable without arguments, it launches an interactive menu:

```
🚀 Rubix Token Sync Tool
========================

Current Configuration:
❌ MSSQL: Not configured
✅ Telegram: Connected to Audit Bot

Choose an option:
1. Run Standard Sync (incremental)
2. Run Full Sync (clear all + resync)
3. Test Connections Only
4. Setup MSSQL Credentials
5. Cleanup IPFS Lock Errors
6. Essential Metadata Only (fast)
7. View System Information
8. Exit

Enter choice [1-8]:
```

### Menu Options

1. **Standard Sync**: Incremental sync preserving existing data
2. **Full Sync**: Clear all records and resync from scratch ⚠️
3. **Test Connections**: Verify database and Telegram connectivity
4. **Setup MSSQL**: Configure Azure SQL Database credentials
5. **Cleanup IPFS**: Fix IPFS lock errors in existing data
6. **Essential Only**: Fast metadata capture without IPFS processing
7. **System Info**: Display system compatibility and configuration
8. **Exit**: Close the application

## 💻 Command Line Mode

For automated/scripted usage, the executable supports direct command-line options:

```bash
# Show help
./RubixTokenSync --help

# Standard incremental sync
./RubixTokenSync

# Full sync (clear all + resync)
./RubixTokenSync --clear --force-ipfs

# Re-fetch IPFS data only
./RubixTokenSync --force-ipfs

# Cleanup IPFS lock errors
./RubixTokenSync --cleanup-locks

# Essential metadata only (fast)
./RubixTokenSync --essential-only

# Test connections only
./RubixTokenSync --test-only

# Force interactive mode
./RubixTokenSync --interactive
```

## ⚙️ Configuration

The executable creates configuration files in the same directory:

### 🗄️ **Azure SQL Database** (`azure_sql_connection.txt`)
```
DRIVER={ODBC Driver 17 for SQL Server};
SERVER=tcp:rauditser.database.windows.net,1433;
DATABASE=rauditd;
UID=rubix;
PWD=your_password_here;
Encrypt=yes;
TrustServerCertificate=no;
Connection Timeout=30;
```

### 📱 **Telegram Notifications** (`telegram_config.json`)
```json
{
  "bot_token": "8391226270:AAFv1p1nHf6gcEgXI7diiikczAW-I5Gg1KE",
  "chat_id": "-1003231044644",
  "enabled": true,
  "machine_name": "YourMachine-Windows",
  "send_startup": true,
  "send_progress": true,
  "send_errors": true,
  "send_completion": true
}
```

> **Note**: Telegram is pre-configured. You only need to set up the Azure SQL Database credentials.

## 🛠️ Building Your Own Executable

If you want to build the executable yourself:

### Prerequisites
- Python 3.8+
- Git (to clone the repository)

### Build Process
```bash
# Clone repository
git clone <repository_url>
cd audit/tri

# Install build dependencies
python build_executable.py --install-deps

# Build executable
python build_executable.py

# Clean build artifacts only
python build_executable.py --clean-only
```

### Build Output
```
dist/
├── RubixTokenSync(.exe)              # Main executable
├── rubixTokenSync_platform_arch/     # Distribution package
│   ├── RubixTokenSync(.exe)
│   ├── README.txt
│   └── *.txt (templates)
└── rubixTokenSync_platform_arch.zip  # Archive for distribution
```

## 🔧 System Requirements

### Minimum Requirements
- **Memory**: 2GB RAM available
- **Disk**: 1GB free space
- **Network**: Internet connection for sync operations
- **IPFS**: IPFS binary accessible in system PATH or project directories

### Supported Operating Systems

| OS | Version | Architecture | Notes |
|---|---|---|---|
| Windows | 10+ | x64 | Tested on Windows 10/11 |
| macOS | 10.14+ | x64, ARM64 | Universal binary support |
| Linux | Ubuntu 18.04+, CentOS 7+ | x64 | Most modern distributions |

### Network Access Required
- **Azure SQL Database**: `rauditser.database.windows.net:1433`
- **Telegram API**: `api.telegram.org:443`
- **IPFS Network**: Various peer connections
- **External IP Detection**: `ifconfig.me`, `api.ipify.org`

## 📊 Sync Process Overview

```
1. 🔍 Discovery Phase
   ├── Scan for rubix.db files
   ├── Detect IPFS binaries per node
   ├── Build .ipfs directory mapping
   └── Validate system compatibility

2. 📊 Processing Phase
   ├── Read token data from SQLite
   ├── Fetch metadata from IPFS (parallel)
   ├── Process in 1000-record batches
   └── Insert to Azure SQL Database

3. 📱 Monitoring Phase
   ├── Real-time Telegram notifications
   ├── Progress tracking with ETA
   ├── Error logging and recovery
   └── Completion statistics
```

## 🐛 Troubleshooting

### Common Issues

**🔴 "MSSQL Not Configured"**
- Run option 4 from the menu to set up database credentials
- Ensure you have the correct password for the `rubix` user

**🔴 "IPFS Binary Not Found"**
- The executable will search for IPFS binaries automatically
- Ensure IPFS is installed and accessible
- Check that `.ipfs` directories exist alongside your `rubix.db` files

**🔴 "Telegram Connection Failed"**
- Telegram is pre-configured and should work automatically
- Check internet connection if notifications aren't working

**🔴 "Permission Denied" (Linux/macOS)**
```bash
chmod +x RubixTokenSync
./RubixTokenSync
```

**🔴 "App can't be opened" (macOS)**
```bash
# Allow unsigned app
sudo xattr -rd com.apple.quarantine RubixTokenSync
./RubixTokenSync
```

### Performance Optimization

**For Large Datasets (1M+ tokens):**
- Use "Essential Metadata Only" mode first for fast coverage
- Run full IPFS sync afterward
- Monitor available memory during processing

**For Slow Networks:**
- Use `--cleanup-locks` first to fix any IPFS issues
- Increase timeouts if needed (edit source and rebuild)

## 📈 Monitoring and Logs

### Real-time Monitoring
- **Interactive Progress**: Built-in progress bars with ETA
- **Telegram Updates**: Live notifications in your Audit Bot group
- **System Status**: Memory, disk, and network monitoring

### Log Files (created in executable directory)
```
logs/
├── sync_main_YYYYMMDD.log     # Main sync operations
├── sync_errors_YYYYMMDD.log   # Error details
└── sync_ipfs_YYYYMMDD.log     # IPFS-specific logs
```

### Statistics Tracking
- **Databases Processed**: Count and success rate
- **Tokens Synced**: Total and per-database counts
- **IPFS Success Rate**: Metadata fetch statistics
- **Performance Metrics**: Processing speed and duration

## 🔐 Security Notes

- **Credentials**: Stored in plain text config files (secure file permissions applied)
- **Network**: All database connections use SSL encryption
- **IPFS**: Read-only operations, no data modification
- **Logs**: May contain sensitive information, review before sharing

## 📞 Support

For issues, questions, or feature requests:
1. Check the troubleshooting section above
2. Review log files for detailed error information
3. Use the "System Information" menu option for compatibility details
4. Refer to project documentation or contact support

---

**Built with**: Python 3.8+, PyInstaller, Azure SQL Database, IPFS, Telegram Bot API

**License**: Please refer to project license

**Version**: 1.0.0