#!/bin/bash

# Smart Driver Scoring System Launcher
# This script initializes Bluetooth and runs the dashboard

echo "Starting Driver Scoring System..."

# Ensure Bluetooth is powered on
echo "Checking Bluetooth..."
sudo rfkill unblock bluetooth
sleep 1

# Navigate to project directory
cd /home/admin/Smart-Driver-Scoring-System

# Activate virtual environment
source venv/bin/activate

# Set display for GUI
export DISPLAY=:0

# Run the dashboard (it will connect to BLE OBD automatically)
echo "Launching Dashboard..."
python3 src/ui/dashboard.py
