#!/bin/bash

# Fix Raspberry Pi Bluetooth for BLE devices
# This script configures BlueZ to prioritize BLE connections

echo "Configuring Bluetooth for BLE-only mode..."

# Stop Bluetooth service
sudo systemctl stop bluetooth

# Create/edit BlueZ main.conf to disable BR/EDR
sudo tee /etc/bluetooth/main.conf > /dev/null <<EOF
[General]
# Disable classic Bluetooth (BR/EDR), use BLE only
ControllerMode = le

# Privacy settings
Privacy = device

# Class of Device (ignored in LE mode but set anyway)
Class = 0x000100

# Faster connection
FastConnectable = true

# Disable pairing for BLE devices that don't require it
JustWorksRepairing = always

# Temporary pairing (no bonding)
TemporaryTimeout = 30
EOF

# Restart Bluetooth service
sudo systemctl restart bluetooth

# Wait for service to start
sleep 2

# Configure adapter for LE only
sudo btmgmt --index 0 bredr off
sudo btmgmt --index 0 le on
sudo btmgmt --index 0 power on

echo "✓ Bluetooth configured for BLE-only mode"
echo ""
echo "Now try: python3 scripts/test_obd.py 81:23:45:67:89:BA"
