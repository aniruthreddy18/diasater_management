"""
Test NASA FIRMS cross-check corroboration, distance calculation, and risk score adjustments.
"""

import pytest
from core.models import StandardPacket, HazardType
from firms.distance import haversine_distance_km
from firms.client import FirmsClient, FirmsHotspot
from engines.wildfire_engine import WildfireEngine
from engines.landslide_engine import LandslideEngine


def test_haversine_distance_calculation():
    # Distance between (17.3850, 78.4867) and (17.4100, 78.5100) is approx ~3.6 - 4.2 km
    dist = haversine_distance_km(17.3850, 78.4867, 17.4100, 78.5100)
    assert 3.5 <= dist <= 4.5

    # Distance to identical point should be 0.0 km
    dist_zero = haversine_distance_km(17.3850, 78.4867, 17.3850, 78.4867)
    assert dist_zero == 0.0


@pytest.mark.asyncio
async def test_wildfire_firms_match_within_radius():
    # Setup custom FIRMS client with a known hotspot 4 km away
    custom_firms = FirmsClient(match_radius_km=25.0, risk_boost=15.0)
    custom_firms.clear_simulated_hotspots()
    custom_firms.add_simulated_hotspot(
        FirmsHotspot(
            latitude=17.4100,
            longitude=78.5100,
            brightness=340.0,
            confidence="high",
        )
    )

    engine = WildfireEngine(firms=custom_firms)

    # Fire telemetry triggering detection
    pkt = StandardPacket(
        device_id="FIRE_001",
        hazard_type=HazardType.WILDFIRE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"temperature": 50.0, "humidity": 18.0, "smoke": 700.0, "flame_detected": True},
    )

    event = await engine.process_packet(pkt)

    assert event.detected is True
    assert event.firms_confirmed is True
    assert event.firms_adjustment == 15.0
    assert event.nearest_firms_distance_km is not None
    assert event.nearest_firms_distance_km <= 25.0
    # Final risk score must include the +15% boost
    assert event.final_risk_score == min(100.0, event.base_risk_score + 15.0)


@pytest.mark.asyncio
async def test_wildfire_firms_unconfirmed_when_hotspot_outside_radius():
    # Hotspot located 100 km away
    custom_firms = FirmsClient(match_radius_km=10.0, risk_boost=15.0)
    custom_firms.clear_simulated_hotspots()
    custom_firms.add_simulated_hotspot(
        FirmsHotspot(
            latitude=18.3000,
            longitude=79.3000,
            brightness=320.0,
        )
    )

    engine = WildfireEngine(firms=custom_firms)

    pkt = StandardPacket(
        device_id="FIRE_001",
        hazard_type=HazardType.WILDFIRE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"temperature": 48.0, "humidity": 20.0, "smoke": 550.0},
    )

    event = await engine.process_packet(pkt)

    assert event.detected is True
    assert event.firms_confirmed is False
    assert event.firms_adjustment == 0.0
    assert event.final_risk_score == event.base_risk_score


@pytest.mark.asyncio
async def test_wildfire_firms_cap_at_100_percent():
    # If base risk is already 95%, +15% must cap at 100.0%
    custom_firms = FirmsClient(match_radius_km=25.0, risk_boost=15.0)
    custom_firms.clear_simulated_hotspots()
    custom_firms.add_simulated_hotspot(
        FirmsHotspot(latitude=17.3850, longitude=78.4867)
    )

    engine = WildfireEngine(firms=custom_firms)

    pkt = StandardPacket(
        device_id="FIRE_001",
        hazard_type=HazardType.WILDFIRE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"temperature": 65.0, "humidity": 8.0, "smoke": 950.0, "flame_detected": True},
    )

    event = await engine.process_packet(pkt)
    assert event.final_risk_score == 100.0


@pytest.mark.asyncio
async def test_non_wildfire_never_interacts_with_firms():
    # Landslide engine must never attach FIRMS confirmation or adjustments
    ls_engine = LandslideEngine()
    pkt = StandardPacket(
        device_id="LANDSLIDE_001",
        hazard_type=HazardType.LANDSLIDE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"tilt_angle": 30.0, "soil_moisture": 90.0},
    )
    event = await ls_engine.process_packet(pkt)
    assert event.firms_confirmed is None
    assert event.nearest_firms_distance_km is None
    assert event.firms_adjustment == 0.0
