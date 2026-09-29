"""
Test hardware identification and hazard routing.
"""

import pytest
from core.models import StandardPacket, HazardType
from classifier.data_classifier import DataClassifier


def test_device_id_classification():
    classifier = DataClassifier()

    assert classifier.identify_hazard_type("FIRE_001") == HazardType.WILDFIRE
    assert classifier.identify_hazard_type("WILDFIRE_NODE_3") == HazardType.WILDFIRE
    assert classifier.identify_hazard_type("FLOOD_001") == HazardType.FLASH_FLOOD
    assert classifier.identify_hazard_type("HYDRO_SENSOR_A") == HazardType.FLASH_FLOOD
    assert classifier.identify_hazard_type("LANDSLIDE_001") == HazardType.LANDSLIDE
    assert classifier.identify_hazard_type("SLOPE_MONITOR_9") == HazardType.LANDSLIDE


@pytest.mark.asyncio
async def test_route_and_process():
    classifier = DataClassifier()

    pkt_fire = StandardPacket(
        device_id="FIRE_001",
        hazard_type=HazardType.WILDFIRE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"temperature": 25.0, "humidity": 60.0, "smoke": 50.0},
    )
    ev_fire = await classifier.route_and_process(pkt_fire)
    assert ev_fire.hazard_type == HazardType.WILDFIRE

    pkt_flood = StandardPacket(
        device_id="FLOOD_001",
        hazard_type=HazardType.FLASH_FLOOD,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"water_level": 30.0},
    )
    ev_flood = await classifier.route_and_process(pkt_flood)
    assert ev_flood.hazard_type == HazardType.FLASH_FLOOD

    pkt_ls = StandardPacket(
        device_id="LANDSLIDE_001",
        hazard_type=HazardType.LANDSLIDE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"tilt_angle": 2.0, "soil_moisture": 25.0},
    )
    ev_ls = await classifier.route_and_process(pkt_ls)
    assert ev_ls.hazard_type == HazardType.LANDSLIDE
