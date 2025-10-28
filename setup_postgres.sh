#!/bin/bash
#
# PostgreSQL Installation and Configuration Script
# This script installs PostgreSQL with custom data directory and enables remote access
#

set -e  # Exit on error

echo "=========================================="
echo "PostgreSQL Installation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_VERSION="17"
DATA_DIR="/datadrive/Rubix/postgres"
DB_NAME="rubix_tokens"
POSTGRES_USER="postgres"

echo -e "${YELLOW}This script will:${NC}"
echo "1. Install PostgreSQL ${POSTGRES_VERSION}"
echo "2. Configure data directory at ${DATA_DIR}"
echo "3. Enable remote connections"
echo "4. Create database '${DB_NAME}'"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Step 1: Install PostgreSQL
echo ""
echo -e "${GREEN}[Step 1/7] Installing PostgreSQL ${POSTGRES_VERSION}...${NC}"
sudo apt update
sudo apt install -y wget gnupg2

# Add PostgreSQL repository
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo sh -c "echo 'deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main' > /etc/apt/sources.list.d/pgdg.list"

# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql-${POSTGRES_VERSION} postgresql-contrib-${POSTGRES_VERSION}

# Stop PostgreSQL service
echo -e "${GREEN}[Step 2/7] Stopping PostgreSQL service...${NC}"
sudo systemctl stop postgresql

# Step 2: Create custom data directory
echo -e "${GREEN}[Step 3/7] Creating custom data directory at ${DATA_DIR}...${NC}"
sudo mkdir -p ${DATA_DIR}
sudo chown postgres:postgres ${DATA_DIR}
sudo chmod 700 ${DATA_DIR}

# Initialize the new data directory
echo -e "${GREEN}[Step 4/7] Initializing PostgreSQL data directory...${NC}"
sudo -u postgres /usr/lib/postgresql/${POSTGRES_VERSION}/bin/initdb -D ${DATA_DIR}

# Step 3: Update PostgreSQL configuration
echo -e "${GREEN}[Step 5/7] Configuring PostgreSQL for remote access...${NC}"

# Update postgresql.conf
POSTGRES_CONF="${DATA_DIR}/postgresql.conf"
sudo -u postgres bash -c "cat >> ${POSTGRES_CONF} << 'EOF'

# Custom configuration for remote access
listen_addresses = '*'
port = 5432
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_statement = 'all'
log_duration = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

EOF
"

# Update pg_hba.conf for password authentication
PG_HBA_CONF="${DATA_DIR}/pg_hba.conf"
sudo -u postgres bash -c "cat > ${PG_HBA_CONF} << 'EOF'
# PostgreSQL Client Authentication Configuration File
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     md5

# IPv4 local connections
host    all             all             127.0.0.1/32            md5

# IPv4 remote connections (requires password)
host    all             all             0.0.0.0/0               md5

# IPv6 local connections
host    all             all             ::1/128                 md5

# IPv6 remote connections
host    all             all             ::/0                    md5
EOF
"

# Update systemd service to use custom data directory
echo -e "${GREEN}[Step 6/7] Updating systemd service configuration...${NC}"
sudo mkdir -p /etc/systemd/system/postgresql@${POSTGRES_VERSION}-main.service.d
sudo bash -c "cat > /etc/systemd/system/postgresql@${POSTGRES_VERSION}-main.service.d/override.conf << EOF
[Service]
Environment=PGDATA=${DATA_DIR}
EOF
"

# Reload systemd and start PostgreSQL
sudo systemctl daemon-reload
sudo systemctl start postgresql@${POSTGRES_VERSION}-main
sudo systemctl enable postgresql@${POSTGRES_VERSION}-main

# Wait for PostgreSQL to start
echo "Waiting for PostgreSQL to start..."
sleep 3

# Step 4: Set postgres user password
echo ""
echo -e "${GREEN}[Step 7/7] Setting up PostgreSQL password...${NC}"
echo ""
echo -e "${YELLOW}Please enter a strong password for the PostgreSQL 'postgres' user:${NC}"
read -s POSTGRES_PASSWORD
echo ""
echo -e "${YELLOW}Confirm password:${NC}"
read -s POSTGRES_PASSWORD_CONFIRM
echo ""

if [ "$POSTGRES_PASSWORD" != "$POSTGRES_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}Passwords do not match! Exiting.${NC}"
    exit 1
fi

# Set the password
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '${POSTGRES_PASSWORD}';"

# Create the database
echo -e "${GREEN}Creating database '${DB_NAME}'...${NC}"
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME};"

# Configure firewall (if ufw is active)
echo ""
echo -e "${GREEN}Configuring firewall...${NC}"
if sudo ufw status | grep -q "Status: active"; then
    echo "UFW is active. Opening port 5432..."
    sudo ufw allow 5432/tcp
    echo -e "${GREEN}Port 5432 opened in firewall${NC}"
else
    echo -e "${YELLOW}UFW is not active. Skipping firewall configuration.${NC}"
    echo "If you have another firewall, please manually open port 5432"
fi

# Get server IP address
SERVER_IP=$(hostname -I | awk '{print $1}')

# Save connection details
CONNECTION_FILE="/datadrive/Rubix/postgres_connection.txt"
cat > ${CONNECTION_FILE} << EOF
PostgreSQL Connection Details
==============================

Host: ${SERVER_IP}
Port: 5432
Database: ${DB_NAME}
Username: postgres
Password: ${POSTGRES_PASSWORD}

Connection String:
postgresql://postgres:${POSTGRES_PASSWORD}@${SERVER_IP}:5432/${DB_NAME}

Local Connection String (for scripts on this VM):
postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/${DB_NAME}

Data Directory: ${DATA_DIR}

==============================
KEEP THIS FILE SECURE!
==============================
EOF

chmod 600 ${CONNECTION_FILE}

echo ""
echo -e "${GREEN}=========================================="
echo "PostgreSQL Installation Complete!"
echo "==========================================${NC}"
echo ""
echo "Server IP: ${SERVER_IP}"
echo "Database: ${DB_NAME}"
echo "Port: 5432"
echo ""
echo "Connection details saved to: ${CONNECTION_FILE}"
echo ""
echo -e "${YELLOW}Test connection:${NC}"
echo "  psql -h localhost -U postgres -d ${DB_NAME}"
echo ""
echo -e "${GREEN}Next step: Run ./setup_pgadmin.sh to install pgAdmin 4${NC}"
echo ""
