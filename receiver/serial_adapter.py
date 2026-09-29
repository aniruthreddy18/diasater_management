"""
Serial / UART Adapter for Physical Microcontrollers
Multi-Disaster Early Warning System
"""

import json
import logging
from typing import Optional, Callable
from .central_receiver import central_receiver, CentralReceiver

logger = logging.getLogger(__name__)


class SerialAdapter:
    """
    Adapter for reading incoming telemetry lines from physical microcontrollers
    (ESP32, Arduino, Raspberry Pi, or LoRa UART receivers) over Serial USB/UART.
    """

    def __init__(self, receiver: Optional[CentralReceiver] = None):
        self.receiver = receiver or central_receiver
        self._is_running = False

    def parse_line(self, line: str) -> Optional[dict]:
        """
        Parse an incoming line of text from a serial port.
        Supports JSON format:
        {"device_id": "FIRE_001", "sensor_data": {"temperature": 45.2, ...}}
        """
        cleaned = line.strip()
        if not cleaned:
            return None

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "device_id" in data:
                return data
            logger.warning("Serial packet missing 'device_id': %s", cleaned)
            return None
        except json.JSONDecodeError:
            # Fallback format: DEVICE_ID,TEMP,HUMIDITY,SMOKE or similar CSV
            parts = [p.strip() for p in cleaned.split(",")]
            if len(parts) >= 2:
                device_id = parts[0]
                logger.info("Parsed CSV serial line from %s: %s", device_id, parts[1:])
                # Generic dictionary
                return {
                    "device_id": device_id,
                    "sensor_data": {"raw_values": parts[1:]},
                    "use_receiver_gps": True,
                }
            logger.error("Failed to parse serial line: %s", cleaned)
            return None

    def ingest_line(self, line: str):
        """Parse and ingest a raw serial telemetry line."""
        parsed = self.parse_line(line)
        if parsed:
            return self.receiver.ingest_raw_packet(parsed)
        return None
