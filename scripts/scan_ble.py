import asyncio
from bleak import BleakScanner

async def scan():
    print("Scanning for BLE devices for 5 seconds...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    print(f"Found {len(devices)} devices:")
    print("-" * 50)
    for d in devices:
        print(f"Address: {d.address} | Name: {d.name or 'Unknown'}")
        # Metadata might contain manufacturer data etc.
        # print(f"  Metadata: {d.metadata}")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(scan())
