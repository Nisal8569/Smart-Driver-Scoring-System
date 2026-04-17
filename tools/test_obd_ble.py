import asyncio
from bleak import BleakClient

# OBDBLE Characteristics
OBDBLE_ADDRESS = "81:23:45:67:89:BA"
TX_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"  # Write commands here
RX_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"  # Receive responses here

class BLEOBDClient:
    def __init__(self, address):
        self.address = address
        self.client = None
        self.response = b""
        
    def notification_handler(self, sender, data):
        """Called when data is received from the car"""
        print(f"<< {data.decode('ascii', errors='ignore').strip()}")
        self.response += data
        
    async def connect(self):
        print(f"Connecting to {self.address}...")
        self.client = BleakClient(self.address)
        await self.client.connect()
        print("✓ Connected!")
        
        # Enable notifications
        await self.client.start_notify(RX_CHAR_UUID, self.notification_handler)
        print("✓ Notifications enabled\n")
        
    async def send_command(self, cmd):
        """Send an OBD command"""
        self.response = b""
        cmd_bytes = (cmd + "\r").encode('ascii')
        print(f">> {cmd}")
        await self.client.write_gatt_char(TX_CHAR_UUID, cmd_bytes, response=False)
        await asyncio.sleep(1.5)  # Wait for response
        
    async def initialize_obd(self):
        """Send initialization commands to ELM327"""
        print("Initializing OBD adapter...")
        await self.send_command("AT Z")      # Reset
        await self.send_command("AT E0")     # Echo off
        await self.send_command("AT SP 0")   # Auto protocol
        await self.send_command("AT H1")     # Headers on (helpful for debugging)
        print("\n✓ Initialized!\n")
        
    async def query_rpm(self):
        """Query engine RPM (PID 010C)"""
        print("Querying RPM...")
        await self.send_command("010C")
        
    async def query_speed(self):
        """Query vehicle speed (PID 010D)"""
        print("Querying Speed...")
        await self.send_command("010D")
        
    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.stop_notify(RX_CHAR_UUID)
            await self.client.disconnect()
            print("\n✓ Disconnected")


async def main():
    obd = BLEOBDClient(OBDBLE_ADDRESS)
    
    try:
        await obd.connect()
        await obd.initialize_obd()
        
        # Test some queries
        await obd.query_rpm()
        await obd.query_speed()
        
        print("\n✓ Test Complete! OBD communication working.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await obd.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
