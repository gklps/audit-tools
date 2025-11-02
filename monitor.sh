#!/bin/bash
# Rubix Token Sync - Monitor Script
# This script provides real-time monitoring of the sync process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$(pwd)"
REFRESH_INTERVAL=10

# Function to print colored output
print_header() {
    echo -e "${CYAN}$1${NC}"
}

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

print_metric() {
    echo -e "${PURPLE}$1${NC} $2"
}

# Function to clear screen
clear_screen() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                      🚀 RUBIX TOKEN SYNC MONITOR 📊                          ║${NC}"
    echo -e "${CYAN}║                           $(date '+%Y-%m-%d %H:%M:%S')                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to check if we're in the right directory
check_directory() {
    if [ ! -f "sync_distributed_tokens.py" ]; then
        if [ -d "$INSTALL_DIR" ]; then
            cd "$INSTALL_DIR"
        else
            print_error "Cannot find Rubix Token Sync installation."
            exit 1
        fi
    fi
}

# Function to get process status
get_process_status() {
    if pgrep -f "sync_distributed_tokens.py" > /dev/null; then
        PID=$(pgrep -f "sync_distributed_tokens.py")
        print_success "Process Status: RUNNING (PID: $PID)"

        # Get process details
        if command -v ps &> /dev/null; then
            PROCESS_INFO=$(ps -p $PID -o pid,ppid,pcpu,pmem,etime,cmd --no-headers 2>/dev/null || echo "Process info unavailable")
            echo "  📊 Process Details: $PROCESS_INFO"
        fi

        return 0
    else
        print_error "Process Status: NOT RUNNING"
        return 1
    fi
}

# Function to get system metrics
get_system_metrics() {
    print_header "🖥️  SYSTEM METRICS"
    echo "─────────────────────────────────────────────────────────────────────────────"

    # Hostname and IP
    print_metric "🏷️  Hostname:" "$(hostname)"
    print_metric "🌐 Public IP:" "$(curl -s ifconfig.me 2>/dev/null || echo 'Unable to detect')"

    # System load
    if [ -f /proc/loadavg ]; then
        LOAD=$(cat /proc/loadavg | awk '{print $1", "$2", "$3}')
        print_metric "⚡ Load Average:" "$LOAD"
    fi

    # Memory usage
    if command -v free &> /dev/null; then
        MEM_INFO=$(free -h | grep '^Mem:')
        MEM_USED=$(echo $MEM_INFO | awk '{print $3}')
        MEM_TOTAL=$(echo $MEM_INFO | awk '{print $2}')
        MEM_PERCENT=$(free | grep '^Mem:' | awk '{printf "%.1f%%", $3/$2 * 100.0}')
        print_metric "🧠 Memory:" "$MEM_USED / $MEM_TOTAL ($MEM_PERCENT)"
    fi

    # Disk usage
    DISK_INFO=$(df -h . | tail -1)
    DISK_USED=$(echo $DISK_INFO | awk '{print $3}')
    DISK_TOTAL=$(echo $DISK_INFO | awk '{print $2}')
    DISK_PERCENT=$(echo $DISK_INFO | awk '{print $5}')
    print_metric "💾 Disk Usage:" "$DISK_USED / $DISK_TOTAL ($DISK_PERCENT)"

    echo ""
}

# Function to get sync progress
get_sync_progress() {
    print_header "📊 SYNC PROGRESS"
    echo "─────────────────────────────────────────────────────────────────────────────"

    TODAY=$(date +%Y%m%d)
    MAIN_LOG="logs/sync_main_$TODAY.log"

    if [ -f "$MAIN_LOG" ]; then
        # Get latest progress
        LATEST_PROGRESS=$(grep "Progress:" "$MAIN_LOG" | tail -1)
        if [ -n "$LATEST_PROGRESS" ]; then
            echo "  $LATEST_PROGRESS"
        else
            print_warning "No progress information found"
        fi

        # Get session info
        SESSION_START=$(grep "Started sync session" "$MAIN_LOG" | tail -1 | awk '{print $1" "$2}')
        if [ -n "$SESSION_START" ]; then
            print_metric "🕐 Session Started:" "$SESSION_START"
        fi

        # Count databases processed
        DB_COMPLETED=$(grep -c "Database.*processing completed" "$MAIN_LOG" 2>/dev/null || echo "0")
        print_metric "📁 Databases Completed:" "$DB_COMPLETED"

        # Get latest performance metrics
        LATEST_RATE=$(grep "Rate:" "$MAIN_LOG" | tail -1 | grep -o '[0-9]*\.[0-9]*/sec' | head -1)
        if [ -n "$LATEST_RATE" ]; then
            print_metric "⚡ Processing Rate:" "$LATEST_RATE"
        fi

    else
        print_warning "No log file found for today ($MAIN_LOG)"
    fi

    echo ""
}

# Function to get error summary
get_error_summary() {
    print_header "⚠️  ERROR SUMMARY"
    echo "─────────────────────────────────────────────────────────────────────────────"

    TODAY=$(date +%Y%m%d)
    ERROR_LOG="logs/sync_errors_$TODAY.log"

    if [ -f "$ERROR_LOG" ]; then
        ERROR_COUNT=$(wc -l < "$ERROR_LOG")

        if [ "$ERROR_COUNT" -eq 0 ]; then
            print_success "No errors today! 🎉"
        else
            print_warning "Total Errors Today: $ERROR_COUNT"

            # Show error breakdown
            if [ "$ERROR_COUNT" -le 10 ]; then
                echo ""
                print_status "Recent errors:"
                tail -5 "$ERROR_LOG" | while read line; do
                    echo "  $line"
                done
            else
                echo ""
                print_status "Recent errors (last 5):"
                tail -5 "$ERROR_LOG" | while read line; do
                    echo "  $line"
                done

                # Error pattern analysis
                echo ""
                print_status "Error patterns:"
                grep -o 'ERROR.*:' "$ERROR_LOG" | sort | uniq -c | sort -nr | head -3 | while read count pattern; do
                    echo "  $count × $pattern"
                done
            fi
        fi
    else
        print_status "No error log found for today"
    fi

    echo ""
}

# Function to get database connection status
get_connection_status() {
    print_header "🔗 CONNECTION STATUS"
    echo "─────────────────────────────────────────────────────────────────────────────"

    # Test Azure SQL Database
    print_status "Testing Azure SQL Database..."
    python3 -c "
from sync_distributed_tokens import get_azure_sql_connection_string, init_connection_pool
try:
    conn_string = get_azure_sql_connection_string()
    if '{your_password}' in conn_string:
        print('❌ Azure SQL: Password not configured')
    else:
        pool = init_connection_pool()
        print('✅ Azure SQL: Connected')
except Exception as e:
    print(f'❌ Azure SQL: Failed - {str(e)[:50]}...')
" 2>/dev/null

    # Test Telegram
    print_status "Testing Telegram..."
    python3 -c "
from telegram_notifier import init_telegram_notifier
try:
    notifier = init_telegram_notifier()
    if notifier and notifier.config.enabled:
        if notifier.test_connection():
            print(f'✅ Telegram: Connected ({notifier.machine_id})')
        else:
            print('❌ Telegram: Connection failed')
    else:
        print('ℹ️  Telegram: Disabled')
except Exception as e:
    print(f'❌ Telegram: Failed - {str(e)[:50]}...')
" 2>/dev/null || echo "❌ Telegram: Test failed"

    echo ""
}

# Function to get recent activity
get_recent_activity() {
    print_header "📋 RECENT ACTIVITY (Last 10 entries)"
    echo "─────────────────────────────────────────────────────────────────────────────"

    TODAY=$(date +%Y%m%d)
    MAIN_LOG="logs/sync_main_$TODAY.log"

    if [ -f "$MAIN_LOG" ]; then
        # Get recent significant events
        tail -50 "$MAIN_LOG" | grep -E "(Progress:|COMPLETED|ERROR|Database.*completed|Started|IPFS)" | tail -10 | while read line; do
            # Extract timestamp and message
            TIMESTAMP=$(echo "$line" | awk '{print $1" "$2}')
            MESSAGE=$(echo "$line" | cut -d'-' -f4- | sed 's/^[[:space:]]*//')

            # Color code based on content
            if echo "$MESSAGE" | grep -q "ERROR"; then
                echo -e "  ${RED}$TIMESTAMP${NC} $MESSAGE"
            elif echo "$MESSAGE" | grep -q "COMPLETED\|completed"; then
                echo -e "  ${GREEN}$TIMESTAMP${NC} $MESSAGE"
            elif echo "$MESSAGE" | grep -q "Progress:"; then
                echo -e "  ${BLUE}$TIMESTAMP${NC} $MESSAGE"
            else
                echo -e "  ${NC}$TIMESTAMP $MESSAGE"
            fi
        done
    else
        print_warning "No activity log found for today"
    fi

    echo ""
}

# Function to show control options
show_controls() {
    print_header "🎛️  CONTROLS"
    echo "─────────────────────────────────────────────────────────────────────────────"
    echo "  [r] Refresh now    [q] Quit    [l] View live log    [a] Analyze performance"
    echo "  [s] Service status [e] View errors [h] Help"
    echo ""
}

# Function to show help
show_help() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                         🚀 MONITOR HELP GUIDE 📊                             ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Monitor Commands:"
    echo "─────────────────"
    echo "  r  - Refresh display immediately"
    echo "  q  - Quit monitor"
    echo "  l  - View live log (tail -f)"
    echo "  a  - Run performance analysis"
    echo "  s  - Show systemd service status"
    echo "  e  - View error log"
    echo "  h  - Show this help"
    echo ""
    echo "Useful Commands:"
    echo "─────────────────"
    echo "  ./scripts/run_sync.sh --test-only    # Test connections"
    echo "  python3 log_analyzer.py --hours 1    # Quick analysis"
    echo "  sudo systemctl status rubix-sync     # Service status"
    echo "  tail -f logs/sync_main_\$(date +%Y%m%d).log  # Live main log"
    echo "  tail -f logs/sync_errors_\$(date +%Y%m%d).log # Live error log"
    echo ""
    echo "Log Files:"
    echo "───────────"
    echo "  logs/sync_main_YYYYMMDD.log      - Main application log"
    echo "  logs/sync_errors_YYYYMMDD.log    - Error log"
    echo "  logs/sync_debug_YYYYMMDD.log     - Debug log"
    echo "  logs/sync_ipfs_YYYYMMDD.log      - IPFS operations"
    echo "  logs/sync_sql_YYYYMMDD.log       - Database operations"
    echo ""
    read -p "Press Enter to return to monitor..."
}

# Function to view live log
view_live_log() {
    clear
    TODAY=$(date +%Y%m%d)
    MAIN_LOG="logs/sync_main_$TODAY.log"

    if [ -f "$MAIN_LOG" ]; then
        echo -e "${CYAN}📊 Live Log View - Press Ctrl+C to return${NC}"
        echo "─────────────────────────────────────────────────────────────────────────────"
        tail -f "$MAIN_LOG"
    else
        echo "Log file not found: $MAIN_LOG"
        read -p "Press Enter to continue..."
    fi
}

# Function to view errors
view_errors() {
    clear
    TODAY=$(date +%Y%m%d)
    ERROR_LOG="logs/sync_errors_$TODAY.log"

    echo -e "${CYAN}⚠️  Error Log View${NC}"
    echo "─────────────────────────────────────────────────────────────────────────────"

    if [ -f "$ERROR_LOG" ]; then
        ERROR_COUNT=$(wc -l < "$ERROR_LOG")
        echo "Total errors today: $ERROR_COUNT"
        echo ""

        if [ "$ERROR_COUNT" -gt 0 ]; then
            if [ "$ERROR_COUNT" -le 50 ]; then
                cat "$ERROR_LOG"
            else
                echo "Showing last 50 errors (of $ERROR_COUNT total):"
                echo ""
                tail -50 "$ERROR_LOG"
            fi
        else
            echo "No errors today! 🎉"
        fi
    else
        echo "No error log found for today."
    fi

    echo ""
    read -p "Press Enter to continue..."
}

# Function to run performance analysis
run_analysis() {
    clear
    echo -e "${CYAN}📊 Performance Analysis${NC}"
    echo "─────────────────────────────────────────────────────────────────────────────"

    if [ -f "log_analyzer.py" ]; then
        python3 log_analyzer.py --hours 1
    else
        echo "Log analyzer not found."
    fi

    echo ""
    read -p "Press Enter to continue..."
}

# Function to show service status
show_service_status() {
    clear
    echo -e "${CYAN}🔧 Systemd Service Status${NC}"
    echo "─────────────────────────────────────────────────────────────────────────────"

    if systemctl is-active --quiet rubix-sync; then
        echo -e "${GREEN}✅ Service is running${NC}"
    else
        echo -e "${RED}❌ Service is not running${NC}"
    fi

    echo ""
    echo "Service Status:"
    sudo systemctl status rubix-sync --no-pager -l

    echo ""
    echo "Recent Service Logs:"
    sudo journalctl -u rubix-sync --no-pager -l --since "1 hour ago" | tail -20

    echo ""
    read -p "Press Enter to continue..."
}

# Interactive mode function
interactive_mode() {
    local input

    while true; do
        clear_screen
        get_process_status
        PROCESS_RUNNING=$?
        echo ""

        get_system_metrics
        get_sync_progress
        get_error_summary
        get_connection_status
        get_recent_activity
        show_controls

        # Auto-refresh or wait for input
        echo -n "Next refresh in $REFRESH_INTERVAL seconds (or press key for action): "
        read -t $REFRESH_INTERVAL -n 1 input
        echo ""

        case $input in
            'r'|'R')
                continue
                ;;
            'q'|'Q')
                clear
                print_success "Monitor stopped."
                break
                ;;
            'l'|'L')
                view_live_log
                ;;
            'a'|'A')
                run_analysis
                ;;
            's'|'S')
                show_service_status
                ;;
            'e'|'E')
                view_errors
                ;;
            'h'|'H')
                show_help
                ;;
            *)
                # Auto-refresh (timeout occurred)
                continue
                ;;
        esac
    done
}

# Single shot mode function
single_shot_mode() {
    clear_screen
    check_directory

    get_process_status
    echo ""
    get_system_metrics
    get_sync_progress
    get_error_summary
    get_connection_status
    get_recent_activity

    echo -e "${CYAN}Run with --interactive for continuous monitoring${NC}"
}

# Main function
main() {
    # Parse command line arguments
    INTERACTIVE=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --interactive|-i)
                INTERACTIVE=true
                shift
                ;;
            --refresh)
                REFRESH_INTERVAL="$2"
                shift 2
                ;;
            --help)
                echo "Rubix Token Sync Monitor"
                echo ""
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  -i, --interactive    Run in interactive mode"
                echo "  --refresh SECONDS    Set refresh interval (default: 10)"
                echo "  --help               Show this help"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check directory
    check_directory

    # Run in appropriate mode
    if [[ $INTERACTIVE == true ]]; then
        interactive_mode
    else
        single_shot_mode
    fi
}

# Run main function
main "$@"