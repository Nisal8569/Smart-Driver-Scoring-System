import asyncio
import re
from bleak import BleakClient
from typing import Optional, Dict, List

TX_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"
RX_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"

# Matches OBD-II response: "41 0C A1 B2" → pid="0C", data="A1 B2"
PID_RESPONSE_RE = re.compile(r'41\s+([0-9A-Fa-f]{2})((?:\s+[0-9A-Fa-f]{2})+)')


class BLEOBDAdapter:
    def __init__(self, address: str):
        self.address = address
        self.client: Optional[BleakClient] = None
        self.response_buffer = b""
        self.is_ready = False

    def _notification_handler(self, sender, data: bytes):
        self.response_buffer += data

    async def connect(self):
        print(f"Connecting to OBDBLE at {self.address}...")
        self.client = BleakClient(self.address, timeout=20.0)
        await self.client.connect()
        await self.client.start_notify(RX_CHAR_UUID, self._notification_handler)

        await self._send_raw("AT Z")
        await asyncio.sleep(2)
        await self._send_raw("AT E0")
        await self._send_raw("AT SP 0")
        await self._send_raw("AT H0")

        self.is_ready = True
        print("OBDBLE connected and initialized")

    async def _send_raw(self, command: str) -> str:
        self.response_buffer = b""
        await asyncio.sleep(0.05)
        self.response_buffer = b""

        cmd_bytes = (command + "\r").encode('ascii')
        await self.client.write_gatt_char(TX_CHAR_UUID, cmd_bytes, response=False)

        if command.startswith("AT Z"):
            await asyncio.sleep(1.0)
        else:
            timeout = 1.5
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                if b">" in self.response_buffer:
                    break
                await asyncio.sleep(0.01)

        response = self.response_buffer.decode('ascii', errors='ignore').strip()
        response = response.replace(">", "").replace("\r", " ").replace("\n", " ").strip()
        return response

    def _parse_pid_response(self, response: str, expected_pid: str) -> Optional[List[int]]:
        match = PID_RESPONSE_RE.search(response)
        if not match:
            return None
        if match.group(1).upper() != expected_pid.upper():
            return None
        data_hex = match.group(2).strip().split()
        try:
            return [int(b, 16) for b in data_hex]
        except ValueError:
            return None

    async def query_pid(self, mode: str, pid: str) -> Optional[List[int]]:
        response = await self._send_raw(f"{mode}{pid}")
        return self._parse_pid_response(response, pid)

    async def get_data(self) -> Dict[str, Optional[float]]:
        if not self.is_ready:
            return {"speed": None, "rpm": None, "throttle": None,
                    "engine_load": None, "relative_throttle": None}

        data = {}
        try:
            rpm_bytes = await self.query_pid("01", "0C")
            if rpm_bytes and len(rpm_bytes) >= 2:
                data["rpm"] = ((rpm_bytes[0] * 256) + rpm_bytes[1]) / 4.0

            speed_bytes = await self.query_pid("01", "0D")
            if speed_bytes and len(speed_bytes) >= 1:
                data["speed"] = float(speed_bytes[0])

            throttle_bytes = await self.query_pid("01", "11")
            if throttle_bytes and len(throttle_bytes) >= 1:
                data["throttle"] = throttle_bytes[0] * 100.0 / 255.0

            load_bytes = await self.query_pid("01", "04")
            if load_bytes and len(load_bytes) >= 1:
                data["engine_load"] = load_bytes[0] * 100.0 / 255.0

            rel_thr_bytes = await self.query_pid("01", "45")
            if rel_thr_bytes and len(rel_thr_bytes) >= 1:
                data["relative_throttle"] = rel_thr_bytes[0] * 100.0 / 255.0

        except Exception as e:
            print(f"Error querying data: {e}")

        for key in ["speed", "rpm", "throttle", "engine_load", "relative_throttle"]:
            if key not in data or data[key] is None:
                data[key] = 0.0

        return data

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.stop_notify(RX_CHAR_UUID)
            await self.client.disconnect()
            print("OBDBLE disconnected")
