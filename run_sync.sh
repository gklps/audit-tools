#!/bin/bash
# Rubix Token Sync - Run Script
# This script runs the enhanced token sync with proper environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$(pwd)"
LOG_FILE="sync_run.log"

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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check if we're in the right directory
    if [ ! -f "sync_distributed_tokens.py" ]; then
        if [ -d "$INSTALL_DIR" ]; then
            cd "$INSTALL_DIR"
            print_status "Changed to installation directory: $INSTALL_DIR"
        else
            print_error "Cannot find sync_distributed_tokens.py. Please run from the correct directory."
            exit 1
        fi
    fi

    # Check Python dependencies
    python3 -c "
import sys
try:
    import pyodbc
    import pandas
    import requests
    print('✅ All required Python packages are available')
except ImportError as e:
    print(f'❌ Missing Python package: {e}')
    sys.exit(1)
" || {
        print_error "Python dependencies not met. Run setup.sh first."
        exit 1
    }

    # Check configuration files
    if [ ! -f "azure_sql_connection.txt" ]; then
        print_warning "Azure SQL connection not configured. Using template."
        if [ -f "config/azure_sql_connection_template.txt" ]; then
            cp config/azure_sql_connection_template.txt azure_sql_connection.txt
        fi
    fi

    if [ ! -f "telegram_config.json" ]; then
        print_warning "Telegram not configured. Using template."
        if [ -f "config/telegram_config_template.json" ]; then
            cp config/telegram_config_template.json telegram_config.json
        fi
    fi

    print_success "Prerequisites check completed."
}

# Function to show system information
show_system_info() {
    print_status "System Information:"
    echo "  🖥️  Hostname: $(hostname)"
    echo "  🌐 IP Address: $(curl -s ifconfig.me 2>/dev/null || echo 'Unable to detect')"
    echo "  📁 Working Directory: $(pwd)"
    echo "  🐍 Python Version: $(python3 --version)"
    echo "  💾 Available Disk Space: $(df -h . | tail -1 | awk '{print $4}')"
    echo "  🧠 Available Memory: $(free -h | grep '^Mem:' | awk '{print $7}')"
    echo "  🕐 Start Time: $(date)"
    echo ""
}

# Function to test connections
test_connections() {
    print_status "Testing connections..."

    # Test Azure SQL Database
    print_status "Testing Azure SQL Database connection..."
    python3 -c "
from sync_distributed_tokens import get_azure_sql_connection_string, init_connection_pool
try:
    conn_string = get_azure_sql_connection_string()
    if '{your_password}' in conn_string:
        print('⚠️  Azure SQL password not configured - sync will fail')
    else:
        pool = init_connection_pool()
        print('✅ Azure SQL Database connection successful!')
except Exception as e:
    print(f'❌ Azure SQL Database connection failed: {e}')
" 2>/dev/null

    # Test Telegram
    print_status "Testing Telegram connection..."
    python3 -c "
from telegram_notifier import init_telegram_notifier
try:
    notifier = init_telegram_notifier()
    if notifier and notifier.config.enabled and notifier.test_connection():
        print(f'✅ Telegram connection successful! Machine: {notifier.machine_id}')
        notifier.send_message('🧪 **Connection Test**\n\nThis is a test message to verify Telegram integration is working.')
    elif notifier and not notifier.config.enabled:
        print('ℹ️  Telegram notifications disabled in configuration')
    else:
        print('❌ Telegram connection failed - check configuration')
except Exception as e:
    print(f'❌ Telegram test failed: {e}')
" 2>/dev/null || print_warning "Telegram test failed"

    echo ""
}

# Function to show pre-run summary
show_pre_run_summary() {
    echo "========================================"
    print_status "🚀 Ready to Start Rubix Token Sync"
    echo "========================================"
    echo ""

    # Show configuration summary
    if [ -f "telegram_config.json" ]; then
        MACHINE_NAME=$(python3 -c "import json; print(json.load(open('telegram_config.json')).get('machine_name', 'Unknown'))" 2>/dev/null || echo "Unknown")
        TELEGRAM_ENABLED=$(python3 -c "import json; print(json.load(open('telegram_config.json')).get('enabled', False))" 2>/dev/null || echo "false")
        echo "  📱 Machine Name: $MACHINE_NAME"
        echo "  📞 Telegram Notifications: $TELEGRAM_ENABLED"
    fi

    if [ -f "azure_sql_connection.txt" ]; then
        if grep -q "{your_password}" azure_sql_connection.txt; then
            echo "  🗄️  Database: ❌ Not configured (password needed)"
        else
            echo "  🗄️  Database: ✅ Azure SQL Database configured"
        fi
    fi

    echo ""
    print_status "📊 Monitoring Options:"
    echo "  • Real-time logs: tail -f logs/sync_main_\$(date +%Y%m%d).log"
    echo "  • Error logs: tail -f logs/sync_errors_\$(date +%Y%m%d).log"
    echo "  • Performance analysis: python3 log_analyzer.py --hours 1"
    echo "  • Telegram notifications: Check your 'Audit Bot' group"
    echo ""
}

# Function to run the sync
run_sync() {
    print_status "Starting Rubix Token Sync..."

    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_status "Virtual environment activated"
    fi

    # Create logs directory if it doesn't exist
    mkdir -p logs

    # Set Python path
    export PYTHONPATH="$(pwd):$PYTHONPATH"

    # Run the sync with proper error handling
    if python3 sync_distributed_tokens.py; then
        print_success "Sync completed successfully!"

        # Show completion summary
        echo ""
        echo "========================================"
        print_success "✅ Sync Completion Summary"
        echo "========================================"

        # Try to get final metrics
        if [ -f "logs/sync_main_$(date +%Y%m%d).log" ]; then
            echo ""
            print_status "📊 Final Statistics (from logs):"
            grep -E "(COMPLETED|Progress: 100|Total records|IPFS successful|Duration)" logs/sync_main_$(date +%Y%m%d).log | tail -10 || echo "  No completion statistics found"
        fi

        # Check for errors
        if [ -f "logs/sync_errors_$(date +%Y%m%d).log" ]; then
            ERROR_COUNT=$(wc -l < logs/sync_errors_$(date +%Y%m%d).log)
            if [ "$ERROR_COUNT" -gt 0 ]; then
                print_warning "⚠️  $ERROR_COUNT errors were logged during sync"
                echo "  Check: logs/sync_errors_$(date +%Y%m%d).log"
            else
                print_success "🎉 No errors during sync!"
            fi
        fi

    else
        print_error "Sync failed with exit code $?"

        echo ""
        print_status "🔍 Troubleshooting Information:"

        # Show recent errors
        if [ -f "logs/sync_errors_$(date +%Y%m%d).log" ]; then
            echo ""
            print_status "Recent errors (last 5):"
            tail -5 logs/sync_errors_$(date +%Y%m%d).log || echo "  No error log available"
        fi

        # Show system status
        echo ""
        print_status "System status:"
        echo "  💾 Disk space: $(df -h . | tail -1 | awk '{print $4}') available"
        echo "  🧠 Memory: $(free -h | grep '^Mem:' | awk '{print $7}') available"

        return 1
    fi
}

# Function to handle cleanup
cleanup() {
    echo ""
    print_status "🧹 Cleaning up..."

    # Deactivate virtual environment if active
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate 2>/dev/null || true
    fi

    print_status "🕐 End time: $(date)"
}

# Function to show help
show_help() {
    echo "Rubix Token Sync - Run Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --test-only    Only test connections, don't run sync"
    echo "  --background   Run in background (nohup)"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run sync interactively"
    echo "  $0 --test-only       # Test connections only"
    echo "  $0 --background      # Run in background"
    echo ""
    echo "Monitoring:"
    echo "  tail -f logs/sync_main_\$(date +%Y%m%d).log    # Watch main log"
    echo "  ./scripts/monitor.sh                          # System monitor"
    echo "  python3 log_analyzer.py --hours 1             # Performance analysis"
}

# Main function
main() {
    # Parse command line arguments
    TEST_ONLY=false
    BACKGROUND=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --background)
                BACKGROUND=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Set up signal handlers for cleanup
    trap cleanup EXIT INT TERM

    # Start logging
    exec > >(tee -a "$LOG_FILE")
    exec 2>&1

    echo "========================================"
    echo "🚀 Rubix Token Sync - Enhanced Runner"
    echo "========================================"
    echo ""

    # Run setup steps
    check_prerequisites
    show_system_info
    test_connections

    if [[ $TEST_ONLY == true ]]; then
        print_success "Connection tests completed. Exiting as requested."
        exit 0
    fi

    show_pre_run_summary

    # Confirm before starting
    if [[ $BACKGROUND != true ]]; then
        echo ""
        read -p "Ready to start sync? (y/n): " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            print_status "Sync cancelled by user."
            exit 0
        fi
    fi

    echo ""
    echo "========================================"
    print_status "🏃 Starting Sync Process"
    echo "========================================"

    # Run sync
    if [[ $BACKGROUND == true ]]; then
        print_status "Running in background..."
        nohup bash -c "$(declare -f run_sync); run_sync" > sync_background.log 2>&1 &
        BG_PID=$!
        print_success "Sync started in background with PID: $BG_PID"
        print_status "Monitor with: tail -f sync_background.log"
        print_status "Kill with: kill $BG_PID"
    else
        run_sync
    fi
}

# Run main function with all arguments
main "$@"