#!/bin/bash

# Exit on error
set -e

echo "=========================================="
echo "  Smart Driver Sync Service Setup"
echo "=========================================="

# 1. Define paths
PROJECT_ROOT=$(pwd)
SERVICE_FILE="scripts/sync.service"
SYSTEMD_PATH="/etc/systemd/system/smart-sync.service"

# Check if we are in the right directory
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: scripts/sync.service not found. Please run this from the project root."
    exit 1
fi

# 2. Update paths in the service file to match current directory
echo "Updating service file paths..."
# We assume the user 'admin' and path '/home/admin/Smart-Driver-Scoring-System'
# If the path is different, we adjust it dynamically
CURRENT_USER=$(whoami)
sed -i "s|User=admin|User=$CURRENT_USER|g" $SERVICE_FILE
sed -i "s|/home/admin/Smart-Driver-Scoring-System|$PROJECT_ROOT|g" $SERVICE_FILE

# 3. Copy service file to systemd
echo "Installing systemd service..."
sudo cp $SERVICE_FILE $SYSTEMD_PATH

# 4. Reload systemd and enable service
echo "Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable smart-sync.service
sudo systemctl restart smart-sync.service

echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo " To check status:"
echo " sudo systemctl status smart-sync.service"
echo " To view logs:"
echo " tail -f logs/sync_trips.log"
echo "=========================================="
echo ""
echo "IMPORTANT: Ensure you have configured Git credentials (PAT or SSH) on this Pi."
echo "Example for PAT:"
echo "git remote set-url origin https://<username>:<token>@github.com/Nisal8569/Smart-Driver-Scoring-System.git"
echo "=========================================="
