# Microsoft ODBC Driver Troubleshooting Guide

## Common Issue: "Repository does not have a Release file"

If you encounter the error `The repository 'https://packages.microsoft.com/ubuntu/20.04/prod 20.04 Release' does not have a Release file`, here are the solutions:

## 🚀 Quick Fixes

### Option 1: Use --skip-deps Flag
```bash
./setup.sh --skip-deps
```
This skips the problematic ODBC installation and continues with Python setup.

### Option 2: Manual ODBC Installation
```bash
# Remove problematic repository
sudo rm -f /etc/apt/sources.list.d/mssql-release.list

# Clean up package cache
sudo apt clean
sudo apt update

# Install fallback ODBC drivers
sudo apt install -y unixodbc freetds-dev freetds-bin tdsodbc

# Then run setup
./setup.sh --skip-deps
```

### Option 3: Alternative Microsoft Repository
```bash
# Remove existing repository
sudo rm -f /etc/apt/sources.list.d/mssql-release.list

# For Ubuntu 20.04
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/20.04/prod focal main" | sudo tee /etc/apt/sources.list.d/mssql-release.list

# For Ubuntu 22.04
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/22.04/prod jammy main" | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Update and install
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql17
```

## 🔍 Diagnosis Commands

### Check your Ubuntu version:
```bash
lsb_release -a
```

### Check if ODBC driver is installed:
```bash
# Check for Microsoft ODBC driver
ls /opt/microsoft/msodbcsql*/

# Check ODBC configuration
odbcinst -q -d

# Test basic ODBC functionality
isql -v
```

### Test Azure SQL Database connection:
```bash
python3 -c "
import pyodbc
try:
    # Test with your connection string
    conn_str = 'Server=tcp:rauditser.database.windows.net,1433;Database=rauditd;Uid=rubix;Pwd=YOUR_PASSWORD;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    conn = pyodbc.connect(conn_str)
    print('✅ Azure SQL connection successful!')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

## 🛠️ Alternative ODBC Drivers

If Microsoft ODBC driver installation continues to fail, you can use FreeTDS as an alternative:

### Install FreeTDS:
```bash
sudo apt install -y unixodbc freetds-dev freetds-bin tdsodbc
```

### Configure FreeTDS:
Create `/etc/freetds/freetds.conf` with:
```ini
[rauditser]
    host = rauditser.database.windows.net
    port = 1433
    tds version = 7.4
    encryption = require
```

### Update connection string for FreeTDS:
```python
# Instead of ODBC Driver 17 for SQL Server, use:
conn_str = "Driver={FreeTDS};Server=rauditser.database.windows.net;Port=1433;Database=rauditd;Uid=rubix;Pwd=YOUR_PASSWORD;TDS_Version=7.4;Encrypt=yes;"
```

## 🔧 Common Solutions by Ubuntu Version

### Ubuntu 22.04 (Jammy)
```bash
sudo rm -f /etc/apt/sources.list.d/mssql-release.list
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/22.04/prod jammy main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18
```

### Ubuntu 20.04 (Focal)
```bash
sudo rm -f /etc/apt/sources.list.d/mssql-release.list
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/20.04/prod focal main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql17
```

### Ubuntu 18.04 (Bionic)
```bash
sudo rm -f /etc/apt/sources.list.d/mssql-release.list
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/18.04/prod bionic main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql17
```

## ✅ Verification

After installation, verify everything works:

```bash
# 1. Check ODBC drivers
odbcinst -q -d

# 2. Test sync application
./run_sync.sh --test-only

# 3. Check logs
tail -f logs/sync_*.log
```

## 📞 Still Having Issues?

If you continue to have problems:

1. **Use the fallback approach**: `./setup.sh --skip-deps` + manual ODBC installation
2. **Check the setup log**: `cat setup.log`
3. **Verify your Ubuntu version**: `lsb_release -a`
4. **Test with FreeTDS**: Often more reliable than Microsoft ODBC driver

The token sync will work with any ODBC driver that supports Azure SQL Database connections.