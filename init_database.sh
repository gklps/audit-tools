#!/bin/bash
#
# Database Initialization Script
# Creates the TokenInfo table and indexes
#

set -e  # Exit on error

echo "=========================================="
echo "Database Initialization Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load connection details
POSTGRES_CONNECTION_FILE="/datadrive/Rubix/postgres_connection.txt"

if [ ! -f "${POSTGRES_CONNECTION_FILE}" ]; then
    echo -e "${RED}Error: PostgreSQL connection file not found!${NC}"
    echo "Please run ./setup_postgres.sh first"
    exit 1
fi

echo -e "${YELLOW}This script will create the TokenInfo table in your database${NC}"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Extract database name from connection file
DB_NAME=$(grep "Database:" ${POSTGRES_CONNECTION_FILE} | awk '{print $2}')

echo ""
echo -e "${GREEN}Creating TokenInfo table in database '${DB_NAME}'...${NC}"

# Create table with SQL script
sudo -u postgres psql -d ${DB_NAME} << 'EOF'

-- Create TokenInfo table
CREATE TABLE IF NOT EXISTS TokenInfo (
    token_id TEXT PRIMARY KEY,
    token_name TEXT NOT NULL,
    token_number INTEGER NOT NULL,
    creator_did TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_token_name ON TokenInfo(token_name);
CREATE INDEX IF NOT EXISTS idx_creator_did ON TokenInfo(creator_did);
CREATE INDEX IF NOT EXISTS idx_token_number ON TokenInfo(token_number);
CREATE INDEX IF NOT EXISTS idx_last_updated ON TokenInfo(last_updated);

-- Create a function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update last_updated
DROP TRIGGER IF EXISTS update_tokeninfo_last_updated ON TokenInfo;
CREATE TRIGGER update_tokeninfo_last_updated
    BEFORE UPDATE ON TokenInfo
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated_column();

-- Display table structure
\d TokenInfo

-- Display summary
SELECT
    'TokenInfo' as table_name,
    COUNT(*) as total_records
FROM TokenInfo;

EOF

echo ""
echo -e "${GREEN}=========================================="
echo "Database Initialization Complete!"
echo "==========================================${NC}"
echo ""
echo "Table 'TokenInfo' created with the following columns:"
echo "  - token_id (PRIMARY KEY)"
echo "  - token_name"
echo "  - token_number"
echo "  - creator_did"
echo "  - last_updated (auto-updated)"
echo "  - created_at"
echo ""
echo "Indexes created for optimized queries:"
echo "  - idx_token_name"
echo "  - idx_creator_did"
echo "  - idx_token_number"
echo "  - idx_last_updated"
echo ""
echo -e "${GREEN}Next step: Run ./update_sync_script.sh to configure the Python script${NC}"
echo ""
