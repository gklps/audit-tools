#!/bin/bash
# Rubix Token Sync - Automated Setup Script
# This script sets up the complete enhanced token sync system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$(pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="setup.log"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons."
        print_status "Please run as a regular user with sudo privileges."
        exit 1
    fi
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."

    # Check Ubuntu/Debian
    if ! command -v apt &> /dev/null; then
        print_error "This script requires Ubuntu/Debian with apt package manager."
        exit 1
    fi

    # Check Python 3.8+
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2>/dev/null || echo "0.0")
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        print_error "Python 3.8+ is required. Found: $python_version"
        exit 1
    fi

    print_success "System requirements met."
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."

    # Update package list
    sudo apt update

    # Install required packages
    sudo apt install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        curl \
        wget \
        unixodbc-dev \
        gnupg2

    # Install Microsoft ODBC Driver for SQL Server
    print_status "Installing Microsoft ODBC Driver for SQL Server..."

    # Remove any existing problematic repository entries
    sudo rm -f /etc/apt/sources.list.d/mssql-release.list

    # Detect Ubuntu version and use appropriate repository
    UBUNTU_VERSION=$(lsb_release -rs)
    UBUNTU_CODENAME=$(lsb_release -cs)

    print_status "Detected Ubuntu $UBUNTU_VERSION ($UBUNTU_CODENAME)"

    # Use different approach based on Ubuntu version
    if [[ "$UBUNTU_VERSION" == "22.04" ]] || [[ "$UBUNTU_CODENAME" == "jammy" ]]; then
        # Ubuntu 22.04 - use the official method
        print_status "Setting up for Ubuntu 22.04..."
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
        echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/22.04/prod jammy main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
    elif [[ "$UBUNTU_VERSION" == "20.04" ]] || [[ "$UBUNTU_CODENAME" == "focal" ]]; then
        # Ubuntu 20.04 - use the official method
        print_status "Setting up for Ubuntu 20.04..."
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
        echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/20.04/prod focal main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
    elif [[ "$UBUNTU_VERSION" == "18.04" ]] || [[ "$UBUNTU_CODENAME" == "bionic" ]]; then
        # Ubuntu 18.04
        print_status "Setting up for Ubuntu 18.04..."
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
        echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/18.04/prod bionic main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
    else
        # Fallback for other versions - try Ubuntu 20.04 repository
        print_warning "Unsupported Ubuntu version. Trying Ubuntu 20.04 repository as fallback..."
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
        echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/20.04/prod focal main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
    fi

    # Update package list and install ODBC driver
    print_status "Updating package list..."
    if sudo apt update; then
        print_status "Installing ODBC driver..."
        if sudo ACCEPT_EULA=Y apt install -y msodbcsql17; then
            print_success "Microsoft ODBC Driver installed successfully."
        else
            print_warning "Failed to install msodbcsql17. Trying alternative installation..."
            # Try installing with msodbcsql18 as fallback
            if sudo ACCEPT_EULA=Y apt install -y msodbcsql18; then
                print_success "Microsoft ODBC Driver 18 installed successfully."
            else
                print_error "Failed to install Microsoft ODBC Driver. You may need to install it manually."
                print_status "Alternative: Install unixodbc and use FreeTDS driver as fallback"
                sudo apt install -y unixodbc freetds-dev freetds-bin tdsodbc
                print_warning "Installed FreeTDS as ODBC fallback. You may need to configure connection strings differently."
            fi
        fi
    else
        print_error "Failed to update package list. Repository may be temporarily unavailable."
        print_status "Installing fallback ODBC drivers..."
        sudo apt install -y unixodbc freetds-dev freetds-bin tdsodbc
        print_warning "Installed FreeTDS as ODBC fallback. You may need to configure connection strings differently."
    fi

    # Verify ODBC installation
    print_status "Verifying ODBC installation..."
    if command -v sqlcmd &> /dev/null || [ -f "/opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.so" ] || [ -f "/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.so" ]; then
        print_success "ODBC driver verification passed."
    else
        print_warning "ODBC driver verification failed. You may need to install it manually."
        echo ""
        echo "Manual installation commands:"
        echo "# Remove existing repository"
        echo "sudo rm -f /etc/apt/sources.list.d/mssql-release.list"
        echo ""
        echo "# Add Microsoft repository (adjust for your Ubuntu version)"
        echo "curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg"
        echo "echo \"deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/20.04/prod focal main\" | sudo tee /etc/apt/sources.list.d/mssql-release.list"
        echo ""
        echo "# Install ODBC driver"
        echo "sudo apt update"
        echo "sudo ACCEPT_EULA=Y apt install -y msodbcsql17"
        echo ""
    fi

    print_success "System dependencies installation completed."
}

# Function to create installation directory
create_install_dir() {
    print_status "Creating installation directory: $INSTALL_DIR"

    sudo mkdir -p "$INSTALL_DIR"
    sudo chown $USER:$USER "$INSTALL_DIR"

    # Create subdirectories
    mkdir -p "$INSTALL_DIR/logs"

    print_success "Installation directory created."
}

# Function to copy application files
copy_files() {
    print_status "Copying application files..."

    # Copy main application files
    cp "$SCRIPT_DIR/sync_distributed_tokens.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/telegram_notifier.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/log_analyzer.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"

    # Copy configuration templates
    cp "$SCRIPT_DIR/azure_sql_connection_template.txt" "$INSTALL_DIR/config/"
    cp "$SCRIPT_DIR/telegram_config_template.json" "$INSTALL_DIR/config/"

    # Copy documentation
    cp "$SCRIPT_DIR/AZURE_SQL_MIGRATION_GUIDE.md" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/DETAILED_LOGGING_GUIDE.md" "$INSTALL_DIR/"

    # Make scripts executable (they're already in the cloned directory)
    chmod +x "$INSTALL_DIR/run_sync.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/monitor.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/setup.sh" 2>/dev/null || true

    print_success "Application files copied."
}

# Function to create run script if it doesn't exist
create_run_script() {
    cat > "$INSTALL_DIR/run_sync.sh" << 'EOF'
#!/bin/bash
# Run Rubix Token Sync

# Work from current directory

echo "🚀 Starting Rubix Token Sync..."
echo "📁 Working directory: $(pwd)"
echo "🕐 Start time: $(date)"
echo "================================"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Run the sync
python3 sync_distributed_tokens.py

echo "================================"
echo "🕐 End time: $(date)"
EOF
}

# Function to create monitor script if it doesn't exist
create_monitor_script() {
    cat > "$INSTALL_DIR/monitor.sh" << 'EOF'
#!/bin/bash
# Monitor Rubix Token Sync

# Work from current directory

echo "📊 Rubix Token Sync Monitor"
echo "================================"

# Check if sync is running
if pgrep -f "sync_distributed_tokens.py" > /dev/null; then
    echo "✅ Sync process is running"
    echo "PID: $(pgrep -f sync_distributed_tokens.py)"
else
    echo "❌ Sync process is not running"
fi

echo ""
echo "📈 Recent Progress (last 10 lines):"
echo "-----------------------------------"
if [ -f "logs/sync_main_$(date +%Y%m%d).log" ]; then
    tail -10 "logs/sync_main_$(date +%Y%m%d).log" | grep -E "(Progress:|COMPLETED|ERROR)" || echo "No recent progress found"
else
    echo "No log file found for today"
fi

echo ""
echo "💾 Disk Usage:"
echo "---------------"
df -h /datadrive

echo ""
echo "🧠 Memory Usage:"
echo "----------------"
free -h

echo ""
echo "📊 Log Analysis (last 1 hour):"
echo "-------------------------------"
if [ -f "log_analyzer.py" ]; then
    python3 log_analyzer.py --hours 1 2>/dev/null | head -20 || echo "Log analyzer not available"
else
    echo "Log analyzer not found"
fi
EOF
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."

    cd "$INSTALL_DIR"

    # Create virtual environment (optional but recommended)
    if [ "$1" = "--venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
    fi

    # Install Python packages
    pip3 install --upgrade pip

    # Try installing with flexible requirements first
    if pip3 install -r requirements.txt; then
        print_success "All dependencies installed successfully."
    else
        print_warning "Main requirements failed. Trying minimal requirements..."
        if pip3 install -r requirements-minimal.txt; then
            print_success "Minimal dependencies installed successfully."
        else
            print_error "Package installation failed. Installing core packages individually..."
            pip3 install "pyodbc>=4.0.0" || print_warning "Failed to install pyodbc"
            pip3 install "requests>=2.25.0" || print_warning "Failed to install requests"
            pip3 install "pandas>=1.3.0,<2.1.0" || print_warning "Failed to install pandas"
            pip3 install "python-telegram-bot>=13.0,<21.0" || print_warning "Failed to install telegram bot"
        fi
    fi

    # Verify installations
    python3 -c "
import pyodbc
import pandas
import requests
try:
    import telegram
    telegram_available = True
except ImportError:
    telegram_available = False

print('✅ pyodbc:', pyodbc.version)
print('✅ pandas:', pandas.__version__)
print('✅ requests:', requests.__version__)
if telegram_available:
    print('✅ telegram: Available')
else:
    print('⚠️ telegram: Not available (optional)')
"

    print_success "Python dependencies installed."
}

# Function to configure the application
configure_app() {
    print_status "Configuring application..."

    cd "$INSTALL_DIR"

    # Prompt for configuration
    echo ""
    print_status "=== Configuration Setup ==="

    # Azure SQL Database configuration
    read -p "Do you want to configure Azure SQL Database now? (y/n): " configure_db
    if [[ $configure_db =~ ^[Yy]$ ]]; then
        echo ""
        print_status "Azure SQL Database Configuration:"
        read -p "Enter your Azure SQL password: " -s sql_password
        echo ""

        # Create Azure SQL config
        sed "s/{your_password}/$sql_password/g" config/azure_sql_connection_template.txt > azure_sql_connection.txt
        chmod 600 azure_sql_connection.txt
        print_success "Azure SQL Database configured."
    else
        print_warning "Azure SQL Database configuration skipped. You can configure it later by editing azure_sql_connection.txt"
    fi

    # Telegram configuration
    echo ""
    read -p "Do you want to configure Telegram notifications now? (y/n): " configure_telegram
    if [[ $configure_telegram =~ ^[Yy]$ ]]; then
        echo ""
        print_status "Telegram Configuration:"

        # Use existing bot token from template
        BOT_TOKEN="8391226270:AAFv1p1nHf6gcEgXI7diiikczAW-I5Gg1KE"
        CHAT_ID="-1003231044644"

        read -p "Enter machine name for this VM (e.g., Prod-VM-1): " machine_name
        machine_name=${machine_name:-"VM-$(hostname)"}

        # Create Telegram config
        cat > telegram_config.json << EOF
{
  "bot_token": "$BOT_TOKEN",
  "chat_id": "$CHAT_ID",
  "enabled": true,
  "machine_name": "$machine_name",
  "public_ip": "",
  "send_startup": true,
  "send_progress": true,
  "send_errors": true,
  "send_completion": true,
  "progress_interval": 600,
  "max_message_length": 4000
}
EOF

        # Test Telegram connection
        print_status "Testing Telegram connection..."
        python3 -c "
from telegram_notifier import init_telegram_notifier
notifier = init_telegram_notifier()
if notifier and notifier.test_connection():
    print('✅ Telegram connection successful!')
    notifier.send_message('🚀 VM Setup Complete: $machine_name is ready for sync operations')
else:
    print('❌ Telegram test failed - check configuration later')
" 2>/dev/null || print_warning "Telegram test failed - will retry during runtime"

        print_success "Telegram configured for machine: $machine_name"
    else
        print_warning "Telegram configuration skipped. You can configure it later by editing telegram_config.json"
    fi
}

# Function to test the installation
test_installation() {
    print_status "Testing installation..."

    cd "$INSTALL_DIR"

    # Test database connection
    if [ -f "azure_sql_connection.txt" ]; then
        print_status "Testing Azure SQL Database connection..."
        python3 -c "
from sync_distributed_tokens import get_azure_sql_connection_string, init_connection_pool
try:
    conn_string = get_azure_sql_connection_string()
    pool = init_connection_pool()
    print('✅ Azure SQL Database connection successful!')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
" 2>/dev/null || print_warning "Database connection test failed - check configuration"
    fi

    # Test Python imports
    python3 -c "
import sync_distributed_tokens
import telegram_notifier
import log_analyzer
print('✅ All Python modules imported successfully!')
" || {
        print_error "Python module import failed"
        return 1
    }

    print_success "Installation test completed."
}

# Function to create systemd service
create_service() {
    print_status "Do you want to create a systemd service for automatic startup?"
    read -p "Create systemd service? (y/n): " create_svc

    if [[ $create_svc =~ ^[Yy]$ ]]; then
        print_status "Creating systemd service..."

        sudo tee /etc/systemd/system/rubix-sync.service > /dev/null << EOF
[Unit]
Description=Rubix Token Sync Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/sync_distributed_tokens.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

        # Reload systemd and enable service
        sudo systemctl daemon-reload
        sudo systemctl enable rubix-sync.service

        print_success "Systemd service created and enabled."
        print_status "Use 'sudo systemctl start rubix-sync' to start the service."
        print_status "Use 'sudo systemctl status rubix-sync' to check status."
    fi
}

# Function to show completion summary
show_summary() {
    echo ""
    echo "================================"
    print_success "🎉 Installation Complete!"
    echo "================================"
    echo ""
    print_status "📁 Installation Directory: $INSTALL_DIR"
    print_status "📊 Configuration Files:"
    echo "   - Azure SQL: $INSTALL_DIR/azure_sql_connection.txt"
    echo "   - Telegram: $INSTALL_DIR/telegram_config.json"
    echo ""
    print_status "🚀 To run the sync:"
    echo "   cd $INSTALL_DIR"
    echo "   ./scripts/run_sync.sh"
    echo ""
    print_status "📊 To monitor:"
    echo "   ./scripts/monitor.sh"
    echo ""
    print_status "🔧 Service management (if installed):"
    echo "   sudo systemctl start rubix-sync"
    echo "   sudo systemctl status rubix-sync"
    echo "   sudo journalctl -u rubix-sync -f"
    echo ""
    print_status "📚 Documentation:"
    echo "   - $INSTALL_DIR/AZURE_SQL_MIGRATION_GUIDE.md"
    echo "   - $INSTALL_DIR/DETAILED_LOGGING_GUIDE.md"
    echo ""
    print_status "📱 Telegram Group: https://t.me/+rHRidAoAUBViMjM1"
    echo ""
    print_warning "⚠️  Remember to configure Azure SQL firewall rules for this VM's IP address!"
    echo ""
}

# Main installation function
main() {
    echo "========================================"
    echo "🚀 Rubix Token Sync - Enhanced Setup"
    echo "========================================"
    echo ""

    # Parse command line arguments
    USE_VENV=false
    SKIP_DEPS=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --venv)
                USE_VENV=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --help)
                echo "Rubix Token Sync - Setup Script"
                echo ""
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --venv      Create and use Python virtual environment"
                echo "  --skip-deps Skip system dependency installation (useful if ODBC fails)"
                echo "  --help      Show this help message"
                echo ""
                echo "If Microsoft ODBC driver installation fails:"
                echo "  1. Run with --skip-deps: ./setup.sh --skip-deps"
                echo "  2. Install ODBC manually:"
                echo "     sudo apt install -y unixodbc freetds-dev freetds-bin tdsodbc"
                echo "  3. Continue with Python setup"
                echo ""
                echo "The script will automatically handle repository issues and provide fallback options."
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Log everything
    exec > >(tee -a "$LOG_FILE")
    exec 2>&1

    print_status "Starting installation at $(date)"
    print_status "Log file: $LOG_FILE"

    # Run installation steps
    check_root
    check_requirements

    if [[ $SKIP_DEPS != true ]]; then
        install_system_deps
    else
        print_warning "Skipping system dependency installation"
    fi

    create_install_dir
    copy_files

    if [[ $USE_VENV == true ]]; then
        install_python_deps --venv
    else
        install_python_deps
    fi

    configure_app
    test_installation
    create_service
    show_summary

    print_success "Setup completed successfully at $(date)"
}

# Run main function
main "$@"