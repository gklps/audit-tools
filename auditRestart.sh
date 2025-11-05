#!/bin/bash
# ============================================================
# Rubix Audit System Restart Script
# Stops infinite loops, cleans database, and starts fresh sync
# ============================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Script header
echo "============================================================"
echo "🔄 Rubix Audit System Restart Script"
echo "============================================================"
log "Starting complete system restart and cleanup..."

# Step 1: Stop any running sync processes
log "Step 1: Stopping running sync processes..."
if pgrep -f "RubixTokenSync" > /dev/null; then
    warning "Found running RubixTokenSync processes. Stopping them..."
    pkill -f "RubixTokenSync" || true
    sleep 2
    if pgrep -f "RubixTokenSync" > /dev/null; then
        warning "Force killing remaining processes..."
        pkill -9 -f "RubixTokenSync" || true
    fi
    success "All RubixTokenSync processes stopped"
else
    success "No running RubixTokenSync processes found"
fi

# Step 2: Clean up stale lock files
log "Step 2: Cleaning up stale sync files..."
FILES_TO_REMOVE=(
    "sync_distributed_tokens.lock"
    "sync_session_completed.flag"
    "*.log"
)

for file_pattern in "${FILES_TO_REMOVE[@]}"; do
    if ls $file_pattern 1> /dev/null 2>&1; then
        rm -f $file_pattern
        success "Removed: $file_pattern"
    fi
done

# Step 3: Database cleanup
log "Step 3: Cleaning up database duplicates..."

cat > temp_cleanup_db.py << 'EOF'
import pyodbc
import sys

# Connection string - using hardcoded credentials
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=tcp:rauditser.database.windows.net,1433;DATABASE=rauditd;UID=rubix;PWD=Hg&ERwR!8mhMv9mD&Mu;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

print("🔗 Connecting to Azure SQL Database...")
try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Check current state
    print("📊 Checking current database state...")
    cursor.execute("""
        SELECT COUNT(*) AS TotalRows,
               COUNT(DISTINCT token_id) AS UniqueTokenIDs,
               COUNT(*) - COUNT(DISTINCT token_id) AS DuplicateRows
        FROM [dbo].[TokenRecords]
    """)
    row = cursor.fetchone()
    total_rows, unique_tokens, duplicates = row[0], row[1], row[2]
    print(f"   📈 Current state: {total_rows:,} total rows")
    print(f"   🔑 Unique tokens: {unique_tokens:,}")
    print(f"   🔄 Duplicate rows: {duplicates:,}")

    if duplicates > 0:
        print(f"🧹 Removing {duplicates:,} duplicate records...")

        # Remove duplicates (keep most recent)
        cursor.execute("""
            WITH DuplicateTokens AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY token_id, source_ip, node_name
                           ORDER BY synced_at DESC, id DESC
                       ) as row_num
                FROM [dbo].[TokenRecords]
            )
            DELETE FROM [dbo].[TokenRecords]
            WHERE id IN (SELECT id FROM DuplicateTokens WHERE row_num > 1)
        """)
        deleted_count = cursor.rowcount
        print(f"   ✅ Deleted {deleted_count:,} duplicate records")
    else:
        print("   ✅ No duplicates found")

    # Reset processed databases tracking
    print("🔄 Resetting database processing state...")
    cursor.execute("DELETE FROM [dbo].[ProcessedDatabases]")
    reset_count = cursor.rowcount
    print(f"   ✅ Reset {reset_count} processed database records")

    # Clean up failed/interrupted sessions
    print("🧹 Cleaning up failed sync sessions...")
    cursor.execute("DELETE FROM [dbo].[SyncSessions] WHERE status IN ('INTERRUPTED', 'FAILED')")
    session_count = cursor.rowcount
    print(f"   ✅ Cleaned up {session_count} failed sessions")

    conn.commit()

    # Verify final state
    cursor.execute("""
        SELECT COUNT(*) AS TotalRows,
               COUNT(DISTINCT token_id) AS UniqueTokenIDs,
               COUNT(*) - COUNT(DISTINCT token_id) AS DuplicateRows
        FROM [dbo].[TokenRecords]
    """)
    row = cursor.fetchone()
    final_total, final_unique, final_dupes = row[0], row[1], row[2]

    print("📊 Final database state:")
    print(f"   📈 Total rows: {final_total:,}")
    print(f"   🔑 Unique tokens: {final_unique:,}")
    print(f"   🔄 Duplicates: {final_dupes:,}")

    if final_dupes == 0:
        print("✅ Database cleanup completed successfully!")
        sys.exit(0)
    else:
        print(f"❌ Warning: {final_dupes} duplicates still remain")
        sys.exit(1)

except pyodbc.Error as e:
    print(f"❌ Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
finally:
    if 'conn' in locals():
        conn.close()
EOF

# Run database cleanup
if python3 temp_cleanup_db.py; then
    success "Database cleanup completed successfully"
else
    error "Database cleanup failed"
    rm -f temp_cleanup_db.py
    exit 1
fi

# Clean up temporary script
rm -f temp_cleanup_db.py

# Step 4: Download latest release (if needed)
log "Step 4: Checking for latest RubixTokenSync version..."
if [ -f "RubixTokenSync" ]; then
    success "RubixTokenSync executable found"
else
    warning "RubixTokenSync executable not found in current directory"
    log "Please download the latest v1.0.5 release before continuing"
fi

# Step 5: System readiness check
log "Step 5: Performing system readiness check..."

# Check IPFS
if [ -f "./ipfs" ] || [ -f "/usr/local/bin/ipfs" ] || command -v ipfs &> /dev/null; then
    success "IPFS binary available"
else
    warning "IPFS binary not found - sync may fail"
fi

# Check Python dependencies
if python3 -c "import pyodbc, requests" 2>/dev/null; then
    success "Python dependencies available"
else
    warning "Missing Python dependencies (pyodbc, requests)"
fi

# Check disk space
AVAILABLE_SPACE=$(df . | tail -1 | awk '{print $4}')
if [ "$AVAILABLE_SPACE" -gt 1048576 ]; then  # 1GB in KB
    success "Sufficient disk space available"
else
    warning "Low disk space - less than 1GB available"
fi

# Final summary
echo ""
echo "============================================================"
echo "🎯 Restart Summary"
echo "============================================================"
success "✅ Stopped all running sync processes"
success "✅ Cleaned up stale lock and session files"
success "✅ Removed database duplicates and reset sync state"
success "✅ System ready for fresh sync"

echo ""
echo "Next Steps:"
echo "1. Run: ./RubixTokenSync --essential-only    (safe test)"
echo "2. Or:  ./RubixTokenSync                     (full interactive mode)"
echo ""
echo "The system is now clean and ready for a fresh sync!"
echo "============================================================"

log "Restart script completed successfully"