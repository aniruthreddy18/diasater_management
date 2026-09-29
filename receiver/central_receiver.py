"""
Central Receiver & GPS Coordination Unit
Multi-Disaster Early Warning System
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from config.settings import settings
from core.models import StandardPacket, RawIngestPacket, HazardType
from classifier.data_classifier import data_classifier

logger = logging.getLogger(__name__)


class CentralReceiver:
    """
    Central Data Collection Point for all three independent hardware systems.
    Pairs incoming telemetry with GPS coordinates from the receiver module
    (if node does not provide dedicated GPS), normalizes into a StandardPacket,
    and forwards to the Data Classifier.
    """

    def __init__(
        self,
        default_lat: Optional[float] = None,
        default_lon: Optional[float] = None,
        device_id: Optional[str] = None,
    ):
        self.default_latitude = default_lat if default_lat is not None else settings.receiver.default_latitude
        self.default_longitude = default_lon if default_lon is not None else settings.receiver.default_longitude
        self.receiver_id = device_id or settings.receiver.device_id
        self._current_receiver_gps = {
            "latitude": self.default_latitude,
            "longitude": self.default_longitude,
            "fix_time": datetime.now(timezone.utc).isoformat(),
        }

    def update_receiver_gps(self, latitude: float, longitude: float) -> None:
        """Update receiver GPS location (e.g. from an attached hardware GPS module)."""
        self._current_receiver_gps = {
            "latitude": latitude,
            "longitude": longitude,
            "fix_time": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Central Receiver GPS updated: (%.4f, %.4f)", latitude, longitude)

    def get_receiver_gps(self) -> Dict[str, Any]:
        """Return the current geographic coordinates from the receiver GPS module."""
        return dict(self._current_receiver_gps)

    def ingest_raw_packet(self, raw_data: Dict[str, Any]) -> StandardPacket:
        """
        Accept raw telemetry dict from physical hardware (HTTP, WebSocket, or Serial),
        resolve GPS coordinates, classify hazard type, and construct a StandardPacket.
        """
        device_id = str(raw_data.get("device_id", "UNKNOWN_NODE")).strip()

        # Classify hazard type
        hazard_type = data_classifier.identify_hazard_type(
            device_id=device_id,
            explicit_type=raw_data.get("hazard_type")
        )

        # Coordinate resolution: use packet GPS, or fallback to Central Receiver GPS
        use_receiver_gps = raw_data.get("use_receiver_gps", False)
        pkt_lat = raw_data.get("latitude")
        pkt_lon = raw_data.get("longitude")

        if use_receiver_gps or pkt_lat is None or pkt_lon is None:
            latitude = self._current_receiver_gps["latitude"]
            longitude = self._current_receiver_gps["longitude"]
            logger.debug("Packet [%s] tagged with Central Receiver GPS (%.4f, %.4f)",
                         device_id, latitude, longitude)
        else:
            latitude = float(pkt_lat)
            longitude = float(pkt_lon)

        timestamp = raw_data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        sensor_data = raw_data.get("sensor_data", {})

        standard_packet = StandardPacket(
            device_id=device_id,
            hazard_type=hazard_type,
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            sensor_data=sensor_data,
        )

        logger.info(
            "Central Receiver Ingested [%s] -> Type=%s at (%.4f, %.4f)",
            device_id, hazard_type.value, latitude, longitude
        )
        return standard_packet


# Global central receiver instance
central_receiver = CentralReceiver()
