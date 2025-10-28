#!/bin/bash
#
# pgAdmin 4 Installation and Configuration Script
# This script installs pgAdmin 4 in web mode for remote access
#

set -e  # Exit on error

echo "=========================================="
echo "pgAdmin 4 Installation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PGADMIN_PORT=5050  # Default pgAdmin port (you can change this)

echo -e "${YELLOW}This script will:${NC}"
echo "1. Install pgAdmin 4 in web mode"
echo "2. Configure pgAdmin to run as a service"
echo "3. Set up access on port ${PGADMIN_PORT}"
echo "4. Enable remote access"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Step 1: Install pgAdmin 4
echo ""
echo -e "${GREEN}[Step 1/5] Adding pgAdmin repository...${NC}"

# Install required packages
sudo apt install -y curl ca-certificates

# Add pgAdmin repository
curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg

sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list'

# Update and install pgAdmin 4
echo -e "${GREEN}[Step 2/5] Installing pgAdmin 4...${NC}"
sudo apt update
sudo apt install -y pgadmin4-web

# Step 2: Configure pgAdmin
echo ""
echo -e "${GREEN}[Step 3/5] Configuring pgAdmin 4...${NC}"
echo ""
echo -e "${YELLOW}Please enter an email address for pgAdmin login:${NC}"
read PGADMIN_EMAIL

echo ""
echo -e "${YELLOW}Please enter a password for pgAdmin login:${NC}"
read -s PGADMIN_PASSWORD
echo ""
echo -e "${YELLOW}Confirm password:${NC}"
read -s PGADMIN_PASSWORD_CONFIRM
echo ""

if [ "$PGADMIN_PASSWORD" != "$PGADMIN_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}Passwords do not match! Exiting.${NC}"
    exit 1
fi

# Run pgAdmin setup
echo ""
echo "Setting up pgAdmin..."
sudo /usr/pgadmin4/bin/setup-web.sh --yes << EOF
${PGADMIN_EMAIL}
${PGADMIN_PASSWORD}
EOF

# Step 3: Configure pgAdmin for remote access
echo ""
echo -e "${GREEN}[Step 4/5] Configuring pgAdmin for remote access...${NC}"

# Create custom pgAdmin configuration
PGADMIN_CONFIG_FILE="/usr/pgadmin4/web/config_local.py"
sudo bash -c "cat > ${PGADMIN_CONFIG_FILE} << 'EOF'
# pgAdmin 4 Custom Configuration

# Server settings
DEFAULT_SERVER = '0.0.0.0'
DEFAULT_SERVER_PORT = ${PGADMIN_PORT}

# Security settings
CSRF_SESSION_KEY = 'your-secret-key-here-$(openssl rand -hex 32)'
SECRET_KEY = 'your-secret-key-here-$(openssl rand -hex 32)'

# Session settings
SESSION_COOKIE_NAME = 'pgadmin4_session'
SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Enhanced logging
CONSOLE_LOG_LEVEL = 'INFO'
FILE_LOG_LEVEL = 'INFO'

# Disable upgrade check (optional)
UPGRADE_CHECK_ENABLED = False
EOF
"

# Restart Apache to apply changes
echo -e "${GREEN}Restarting Apache web server...${NC}"
sudo systemctl restart apache2

# Step 4: Configure firewall
echo ""
echo -e "${GREEN}[Step 5/5] Configuring firewall...${NC}"
if sudo ufw status | grep -q "Status: active"; then
    echo "UFW is active. Opening port 80 (Apache/pgAdmin)..."
    sudo ufw allow 'Apache Full'
    echo -e "${GREEN}Apache ports opened in firewall${NC}"
else
    echo -e "${YELLOW}UFW is not active. Skipping firewall configuration.${NC}"
    echo "If you have another firewall, please manually open port 80"
fi

# Get server IP address
SERVER_IP=$(hostname -I | awk '{print $1}')

# Load PostgreSQL connection details if available
POSTGRES_CONNECTION_FILE="/datadrive/Rubix/postgres_connection.txt"
if [ -f "${POSTGRES_CONNECTION_FILE}" ]; then
    POSTGRES_HOST=$(grep "Host:" ${POSTGRES_CONNECTION_FILE} | awk '{print $2}')
    POSTGRES_DB=$(grep "Database:" ${POSTGRES_CONNECTION_FILE} | awk '{print $2}')
else
    POSTGRES_HOST="localhost"
    POSTGRES_DB="rubix_tokens"
fi

# Save pgAdmin access details
PGADMIN_ACCESS_FILE="/datadrive/Rubix/pgadmin_access.txt"
cat > ${PGADMIN_ACCESS_FILE} << EOF
pgAdmin 4 Access Details
========================

pgAdmin Web Interface: http://${SERVER_IP}/pgadmin4

Login Credentials:
Email: ${PGADMIN_EMAIL}
Password: ${PGADMIN_PASSWORD}

To add PostgreSQL connection in pgAdmin:
1. Login to pgAdmin web interface
2. Right-click "Servers" > "Register" > "Server"
3. General Tab:
   - Name: Rubix Local PostgreSQL
4. Connection Tab:
   - Host: ${POSTGRES_HOST}
   - Port: 5432
   - Maintenance database: ${POSTGRES_DB}
   - Username: postgres
   - Password: [enter your postgres password]
   - Save password: Yes
5. Click Save

========================
KEEP THIS FILE SECURE!
========================
EOF

chmod 600 ${PGADMIN_ACCESS_FILE}

echo ""
echo -e "${GREEN}=========================================="
echo "pgAdmin 4 Installation Complete!"
echo "==========================================${NC}"
echo ""
echo "Access pgAdmin at: ${GREEN}http://${SERVER_IP}/pgadmin4${NC}"
echo ""
echo "Login Email: ${PGADMIN_EMAIL}"
echo ""
echo "Access details saved to: ${PGADMIN_ACCESS_FILE}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Open your browser and go to http://${SERVER_IP}/pgadmin4"
echo "2. Login with your email and password"
echo "3. Add your PostgreSQL server using the connection details"
echo "4. Run ./update_sync_script.sh to configure the Python script"
echo ""
echo -e "${YELLOW}Note:${NC} If you can't access pgAdmin remotely, check your VM's firewall"
echo "      and cloud provider's security group settings."
echo ""
