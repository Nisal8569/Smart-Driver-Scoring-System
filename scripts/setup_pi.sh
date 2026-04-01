#!/bin/bash

# Exit on error
set -e

echo "=========================================="
echo "  Smart Driver Scoring System - Pi Setup"
echo "=========================================="

# 1. Update System
echo "[1/4] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install System Dependencies
# - libglib2.0-dev: Required for bleak/bluez
# - libbluetooth-dev: Bluetooth development headers
# - libopenblas-dev: Optimized math libraries for NumPy/Pandas (replacing libatlas-base-dev)
# - python3-tk: Required for Tkinter UI
# - git: For version control
echo "[2/4] Installing system dependencies..."
sudo apt install -y python3-pip python3-venv libglib2.0-dev libbluetooth-dev libopenblas-dev python3-tk git

# 3. Create Virtual Environment (Optional but recommended)
if [ ! -d "venv" ]; then
    echo "[3/4] Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
else
    echo "[3/4] using existing virtual environment..."
    source venv/bin/activate
fi

# 4. Install Python Dependencies
echo "[4/4] Installing Python requirements..."
pip3 install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
else
    echo "Warning: requirements.txt not found!"
fi

# 5. Bluetooth Permissions
echo "Setting Bluetooth permissions..."
# Give Python interpreter capability to access Bluetooth without sudo
# Note: This path might vary depending on venv vs system python
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))

echo "=========================================="
echo "  Setup Complete! Reboot recommended."
echo "=========================================="
echo " To run the system:"
echo " 1. source venv/bin/activate"
echo " 2. python3 main_ble.py"
echo "=========================================="
