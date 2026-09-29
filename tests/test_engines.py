"""
Test independent disaster processing engines (Landslide, Flood, Wildfire).
"""

import pytest
from core.models import StandardPacket, HazardType, RiskLevel
from engines.landslide_engine import LandslideEngine
from engines.flood_engine import FloodEngine
from engines.wildfire_engine import WildfireEngine


@pytest.mark.asyncio
async def test_landslide_engine_normal_vs_critical():
    engine = LandslideEngine()

    # 1. Normal packet
    normal_pkt = StandardPacket(
        device_id="LANDSLIDE_001",
        hazard_type=HazardType.LANDSLIDE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"tilt_angle": 2.0, "soil_moisture": 25.0, "vibration_intensity": 0.02},
    )
    res_normal = await engine.process_packet(normal_pkt)
    assert res_normal.detected is False
    assert res_normal.risk_level in (RiskLevel.NORMAL, RiskLevel.LOW)
    assert res_normal.final_risk_score < 40.0

    # 2. Critical landslide packet (high tilt + saturated soil + vibration)
    critical_pkt = StandardPacket(
        device_id="LANDSLIDE_001",
        hazard_type=HazardType.LANDSLIDE,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"tilt_angle": 28.0, "soil_moisture": 92.0, "vibration_intensity": 0.95},
    )
    res_critical = await engine.process_packet(critical_pkt)
    assert res_critical.detected is True
    assert res_critical.risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME)
    assert res_critical.final_risk_score >= 70.0


@pytest.mark.asyncio
async def test_flood_engine_normal_vs_critical():
    engine = FloodEngine()

    # 1. Normal packet
    normal_pkt = StandardPacket(
        device_id="FLOOD_001",
        hazard_type=HazardType.FLASH_FLOOD,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"water_level": 30.0, "rate_of_rise": 0.2, "rainfall_rate": 2.0},
    )
    res_normal = await engine.process_packet(normal_pkt)
    assert res_normal.detected is False
    assert res_normal.risk_level in (RiskLevel.NORMAL, RiskLevel.LOW)

    # 2. Critical surge packet (overtopping + rapid rate of rise + heavy rain)
    critical_pkt = StandardPacket(
        device_id="FLOOD_001",
        hazard_type=HazardType.FLASH_FLOOD,
        latitude=17.3850,
        longitude=78.4867,
        sensor_data={"water_level": 250.0, "rate_of_rise": 9.5, "rainfall_rate": 80.0},
    )
    res_critical = await engine.process_packet(critical_pkt)
    assert res_critical.detected is True
    assert res_critical.risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME)
    assert res_critical.final_risk_score >= 70.0
