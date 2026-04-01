import asyncio
from bleak import BleakScanner, BleakClient

# Your Device MAC
ADDRESS = "81:23:45:67:89:BA"

async def run():
    print(f"Scanning for {ADDRESS} (Timeout: 20s)...")
    device = await BleakScanner.find_device_by_address(ADDRESS, timeout=20.0)
    
    if not device:
        print(f"Device not found!")
        return

    print(f"Found: {device.name}")
    print("Connecting...")

    try:
        async with BleakClient(device) as client:
            print(f"Connected: {client.is_connected}")
            
            print("\n--- Services & Characteristics ---")
            for service in client.services:
                print(f"[Service] {service.uuid}")
                for char in service.characteristics:
                    props = ",".join(char.properties)
                    print(f"  └─ [Char] {char.uuid} ({props})")
                    
            print("\n----------------------------------")
            print("Look for characteristics with 'write' AND 'notify' properties.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(run())
