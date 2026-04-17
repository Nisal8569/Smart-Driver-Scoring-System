import asyncio
from unittest.mock import AsyncMock, patch
from src.acquisition.ble_device import BLEOBDAdapter


def test_it02_reconnect_after_drop_restores_ready_state():
    asyncio.run(_run())


async def _run():
    with patch("src.acquisition.ble_device.BleakClient") as MockBleakClient:
        mock_client = AsyncMock()
        MockBleakClient.return_value = mock_client

        adapter = BLEOBDAdapter("AA:BB:CC:DD:EE:FF")

        async def fake_write(uuid, data, response=False):
            if not data.startswith(b"AT Z"):
                adapter.response_buffer = b">"

        mock_client.write_gatt_char = fake_write

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await adapter.connect()
            assert adapter.is_ready is True

            adapter.is_ready = False
            assert adapter.is_ready is False

            await adapter.connect()
            assert adapter.is_ready is True
