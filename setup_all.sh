#!/bin/bash
#
# Master Setup Script for Rubix Token Sync System
# This script orchestrates the complete setup
#

set -e  # Exit on error

echo "=========================================="
echo "Rubix Token Sync - Complete Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}This master script will:${NC}"
echo "1. Install and configure PostgreSQL"
echo "2. Install and configure pgAdmin 4 (web interface)"
echo "3. Initialize the database and create tables"
echo "4. Update the Python sync script"
echo ""
echo -e "${YELLOW}Prerequisites:${NC}"
echo "✓ Ubuntu VM with sudo access"
echo "✓ /datadrive/Rubix directory exists"
echo "✓ IPFS node running at ./Node/creator/.ipfs"
echo "✓ SQLite database at /datadrive/Rubix/Node/creator/Rubix/rubix.db"
echo ""
echo -e "${RED}IMPORTANT: This will take 15-30 minutes to complete${NC}"
echo ""
read -p "Press Enter to start the setup or Ctrl+C to cancel..."

# Make all scripts executable
echo ""
echo -e "${GREEN}Making scripts executable...${NC}"
chmod +x "${SCRIPT_DIR}/setup_postgres.sh"
chmod +x "${SCRIPT_DIR}/setup_pgadmin.sh"
chmod +x "${SCRIPT_DIR}/init_database.sh"
chmod +x "${SCRIPT_DIR}/update_sync_script.sh"

# Step 1: Setup PostgreSQL
echo ""
echo -e "${BLUE}=========================================="
echo "STEP 1: PostgreSQL Installation"
echo "==========================================${NC}"
"${SCRIPT_DIR}/setup_postgres.sh"

# Step 2: Setup pgAdmin
echo ""
echo -e "${BLUE}=========================================="
echo "STEP 2: pgAdmin 4 Installation"
echo "==========================================${NC}"
"${SCRIPT_DIR}/setup_pgadmin.sh"

# Step 3: Initialize Database
echo ""
echo -e "${BLUE}=========================================="
echo "STEP 3: Database Initialization"
echo "==========================================${NC}"
"${SCRIPT_DIR}/init_database.sh"

# Step 4: Copy sync script to destination
echo ""
echo -e "${BLUE}=========================================="
echo "STEP 4: Copy Sync Script"
echo "==========================================${NC}"
if [ -f "${SCRIPT_DIR}/sync_token_info.py" ]; then
    echo "Copying sync_token_info.py to /datadrive/Rubix/..."
    cp "${SCRIPT_DIR}/sync_token_info.py" /datadrive/Rubix/
    echo -e "${GREEN}✓ Sync script copied${NC}"
else
    echo -e "${YELLOW}Warning: sync_token_info.py not found in current directory${NC}"
    echo "Please manually copy it to /datadrive/Rubix/"
fi

# Step 5: Update sync script configuration
echo ""
echo -e "${BLUE}=========================================="
echo "STEP 5: Update Sync Script Configuration"
echo "==========================================${NC}"
if [ -f "/datadrive/Rubix/sync_token_info.py" ]; then
    "${SCRIPT_DIR}/update_sync_script.sh"
else
    echo -e "${YELLOW}Skipping - sync script not in place yet${NC}"
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Final summary
echo ""
echo -e "${GREEN}=========================================="
echo "       SETUP COMPLETE!"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo "  pgAdmin Web UI: http://${SERVER_IP}/pgadmin4"
echo "  PostgreSQL: ${SERVER_IP}:5432"
echo ""
echo -e "${BLUE}Configuration Files:${NC}"
echo "  PostgreSQL: /datadrive/Rubix/postgres_connection.txt"
echo "  pgAdmin: /datadrive/Rubix/pgadmin_access.txt"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo -e "${YELLOW}1. Access pgAdmin:${NC}"
echo "   - Open browser: http://${SERVER_IP}/pgadmin4"
echo "   - Login with credentials from pgadmin_access.txt"
echo "   - Add PostgreSQL server connection"
echo ""
echo -e "${YELLOW}2. Start Token Sync:${NC}"
echo "   cd /datadrive/Rubix/Node/creator"
echo "   python3 /datadrive/Rubix/sync_token_info.py"
echo ""
echo -e "${YELLOW}3. Monitor Progress:${NC}"
echo "   tail -f /datadrive/Rubix/Node/creator/sync_token_info.log"
echo ""
echo -e "${YELLOW}4. View Data in pgAdmin:${NC}"
echo "   - Connect to your server in pgAdmin"
echo "   - Navigate to: rubix_tokens > Schemas > public > Tables > TokenInfo"
echo "   - Right-click > View/Edit Data > All Rows"
echo ""
echo -e "${GREEN}=========================================="
echo "Happy Token Syncing!"
echo "==========================================${NC}"
echo ""
