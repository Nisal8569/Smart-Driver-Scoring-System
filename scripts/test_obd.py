import asyncio
import sys
import os

# Add project root to path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.acquisition.ble_device import BLEOBDAdapter

async def test_connection(address):
    print(f"Attempting to connect to OBD adapter at {address}...")
    adapter = BLEOBDAdapter(address)
    
    try:
        await adapter.connect()
        print("Successfully connected!")
        
        print("Querying data...")
        # Try to get some data
        data = await adapter.get_data()
        print("received data:", data)
        
        # Explicitly query RPM to see raw response if needed (debug)
        print("Querying RPM directly...")
        rpm_raw = await adapter.query_pid("01", "0C")
        print(f"Raw RPM response: {rpm_raw}")

    except Exception as e:
        print(f"Failed to connect or query: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await adapter.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_obd.py <MAC_ADDRESS>")
        print("Example: python scripts/test_obd.py 81:23:45:67:89:BA")
    else:
        address = sys.argv[1]
        asyncio.run(test_connection(address))
