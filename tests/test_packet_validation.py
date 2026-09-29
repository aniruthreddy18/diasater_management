"""
Test standard packet validation, normalization, and central receiver GPS association.
"""

import pytest
from core.models import StandardPacket, HazardType, RawIngestPacket
from receiver.central_receiver import CentralReceiver


def test_standard_packet_creation():
    pkt = StandardPacket(
        device_id="FIRE_001",
        hazard_type=HazardType.WILDFIRE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"temperature": 48.2, "humidity": 21.0, "smoke": 734},
    )
    assert pkt.device_id == "FIRE_001"
    assert pkt.hazard_type == HazardType.WILDFIRE
    assert pkt.latitude == 17.3850
    assert pkt.sensor_data["temperature"] == 48.2


def test_hazard_type_normalization():
    # String normalization: "flood" -> FLASH_FLOOD, "fire" -> WILDFIRE
    pkt1 = StandardPacket(
        device_id="FLOOD_001",
        hazard_type="flood",
        latitude=17.0,
        longitude=78.0,
    )
    assert pkt1.hazard_type == HazardType.FLASH_FLOOD

    pkt2 = StandardPacket(
        device_id="FIRE_001",
        hazard_type="fire",
        latitude=17.0,
        longitude=78.0,
    )
    assert pkt2.hazard_type == HazardType.WILDFIRE


def test_central_receiver_gps_injection():
    receiver = CentralReceiver(default_lat=17.3850, default_lon=78.4867)

    # Raw packet without GPS coordinates should inherit Receiver GPS
    raw = {
        "device_id": "LANDSLIDE_001",
        "sensor_data": {"tilt_angle": 10.5, "soil_moisture": 45.0},
        "use_receiver_gps": True,
    }
    standard_pkt = receiver.ingest_raw_packet(raw)

    assert standard_pkt.latitude == 17.3850
    assert standard_pkt.longitude == 78.4867
    assert standard_pkt.hazard_type == HazardType.LANDSLIDE


def test_central_receiver_explicit_gps_preservation():
    receiver = CentralReceiver(default_lat=17.3850, default_lon=78.4867)

    # Packet with its own GPS coordinates preserves them
    raw = {
        "device_id": "FLOOD_002",
        "latitude": 18.1234,
        "longitude": 79.5678,
        "sensor_data": {"water_level": 85.0},
    }
    standard_pkt = receiver.ingest_raw_packet(raw)

    assert standard_pkt.latitude == 18.1234
    assert standard_pkt.longitude == 79.5678
    assert standard_pkt.hazard_type == HazardType.FLASH_FLOOD
