#!/bin/bash
#
# Update Sync Script Configuration
# Updates sync_token_info.py to use local PostgreSQL
#

set -e  # Exit on error

echo "=========================================="
echo "Update Sync Script Configuration"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# File paths
SYNC_SCRIPT="/datadrive/Rubix/sync_token_info.py"
POSTGRES_CONNECTION_FILE="/datadrive/Rubix/postgres_connection.txt"

# Check if files exist
if [ ! -f "${POSTGRES_CONNECTION_FILE}" ]; then
    echo -e "${RED}Error: PostgreSQL connection file not found!${NC}"
    echo "Please run ./setup_postgres.sh first"
    exit 1
fi

if [ ! -f "${SYNC_SCRIPT}" ]; then
    echo -e "${RED}Error: sync_token_info.py not found at ${SYNC_SCRIPT}${NC}"
    echo "Please copy sync_token_info.py to /datadrive/Rubix/"
    exit 1
fi

# Extract connection string from file
LOCAL_CONNECTION=$(grep "Local Connection String" -A 1 ${POSTGRES_CONNECTION_FILE} | tail -1)

if [ -z "${LOCAL_CONNECTION}" ]; then
    echo -e "${RED}Error: Could not extract connection string${NC}"
    exit 1
fi

echo -e "${YELLOW}Current sync script location: ${SYNC_SCRIPT}${NC}"
echo -e "${YELLOW}New connection string: ${LOCAL_CONNECTION}${NC}"
echo ""
read -p "Press Enter to update the script or Ctrl+C to cancel..."

# Backup the original file
BACKUP_FILE="${SYNC_SCRIPT}.backup.$(date +%Y%m%d_%H%M%S)"
cp "${SYNC_SCRIPT}" "${BACKUP_FILE}"
echo -e "${GREEN}Backup created: ${BACKUP_FILE}${NC}"

# Update the connection string in the script
sed -i "s|POSTGRES_CONNECTION_STRING = '.*'|POSTGRES_CONNECTION_STRING = '${LOCAL_CONNECTION}'|" "${SYNC_SCRIPT}"

# Verify the change
if grep -q "${LOCAL_CONNECTION}" "${SYNC_SCRIPT}"; then
    echo -e "${GREEN}✓ Connection string updated successfully!${NC}"
else
    echo -e "${RED}✗ Failed to update connection string${NC}"
    echo "Restoring backup..."
    cp "${BACKUP_FILE}" "${SYNC_SCRIPT}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Sync Script Updated Successfully!"
echo "==========================================${NC}"
echo ""
echo "The sync script now uses the local PostgreSQL database"
echo ""
echo -e "${YELLOW}To start syncing tokens:${NC}"
echo "  cd /datadrive/Rubix/Node/creator"
echo "  python3 /datadrive/Rubix/sync_token_info.py"
echo ""
echo -e "${YELLOW}Monitor progress:${NC}"
echo "  tail -f /datadrive/Rubix/Node/creator/sync_token_info.log"
echo ""
echo -e "${GREEN}Backup saved at: ${BACKUP_FILE}${NC}"
echo ""
