"""
Test simultaneous multi-disaster independent state management.
Verifies that detection of one hazard never overwrites or clears another hazard's state.
"""

import pytest
from core.models import HazardType, RiskLevel, HazardEvent
from state.state_manager import StateManager


@pytest.mark.asyncio
async def test_simultaneous_disaster_coexistence():
    state_mgr = StateManager()

    # 1. Initially, all hazards are NORMAL
    init_status = await state_mgr.get_multi_disaster_status()
    assert init_status.active_hazard_count == 0
    assert init_status.wildfire.detected is False
    assert init_status.flash_flood.detected is False
    assert init_status.landslide.detected is False

    # 2. Fire is detected (e.g. Wildfire Alert)
    fire_event = HazardEvent(
        event_id="EV_FIRE_1",
        device_id="FIRE_001",
        hazard_type=HazardType.WILDFIRE,
        latitude=17.4050,
        longitude=78.5020,
        timestamp="2026-09-27T10:00:00Z",
        detected=True,
        base_risk_score=65.0,
        firms_confirmed=True,
        nearest_firms_distance_km=4.2,
        firms_adjustment=15.0,
        final_risk_score=80.0,
        risk_level=RiskLevel.HIGH,
        sensor_data={"temperature": 48.0, "smoke": 600.0},
        message="Wildfire detected with FIRMS confirmation.",
    )
    await state_mgr.update_hazard_state(fire_event)

    status_1 = await state_mgr.get_multi_disaster_status()
    assert status_1.active_hazard_count == 1
    assert status_1.wildfire.detected is True
    assert status_1.wildfire.risk_score == 80.0
    assert status_1.flash_flood.detected is False
    assert status_1.landslide.detected is False

    # 3. Flash Flood is SIMULTANEOUSLY detected!
    flood_event = HazardEvent(
        event_id="EV_FLOOD_1",
        device_id="FLOOD_001",
        hazard_type=HazardType.FLASH_FLOOD,
        latitude=17.3780,
        longitude=78.4950,
        timestamp="2026-09-27T10:05:00Z",
        detected=True,
        base_risk_score=75.0,
        final_risk_score=75.0,
        risk_level=RiskLevel.HIGH,
        sensor_data={"water_level": 230.0, "rate_of_rise": 8.5},
        message="Flash flood surge detected.",
    )
    await state_mgr.update_hazard_state(flood_event)

    status_2 = await state_mgr.get_multi_disaster_status()
    # CORE REQUIREMENT VERIFICATION:
    # Both Fire AND Flash Flood must be DETECTED simultaneously!
    assert status_2.active_hazard_count == 2
    assert status_2.wildfire.detected is True
    assert status_2.wildfire.risk_score == 80.0
    assert status_2.flash_flood.detected is True
    assert status_2.flash_flood.risk_score == 75.0
    assert status_2.landslide.detected is False

    # 4. Landslide is ALSO SIMULTANEOUSLY detected!
    ls_event = HazardEvent(
        event_id="EV_LS_1",
        device_id="LANDSLIDE_001",
        hazard_type=HazardType.LANDSLIDE,
        latitude=17.3920,
        longitude=78.4720,
        timestamp="2026-09-27T10:10:00Z",
        detected=True,
        base_risk_score=90.0,
        final_risk_score=90.0,
        risk_level=RiskLevel.EXTREME,
        sensor_data={"tilt_angle": 30.0, "soil_moisture": 92.0},
        message="Catastrophic slope failure detected.",
    )
    await state_mgr.update_hazard_state(ls_event)

    status_3 = await state_mgr.get_multi_disaster_status()
    # ALL THREE HAZARDS DETECTED SIMULTANEOUSLY
    assert status_3.active_hazard_count == 3
    assert status_3.wildfire.detected is True
    assert status_3.flash_flood.detected is True
    assert status_3.landslide.detected is True

    # 5. When Flash Flood recedes back to NORMAL, Fire and Landslide must remain DETECTED!
    flood_receded = HazardEvent(
        event_id="EV_FLOOD_2",
        device_id="FLOOD_001",
        hazard_type=HazardType.FLASH_FLOOD,
        latitude=17.3780,
        longitude=78.4950,
        timestamp="2026-09-27T11:00:00Z",
        detected=False,
        base_risk_score=15.0,
        final_risk_score=15.0,
        risk_level=RiskLevel.NORMAL,
        sensor_data={"water_level": 35.0},
        message="Waterway returned to normal stage.",
    )
    await state_mgr.update_hazard_state(flood_receded)

    status_4 = await state_mgr.get_multi_disaster_status()
    assert status_4.active_hazard_count == 2
    assert status_4.flash_flood.detected is False  # Receded
    assert status_4.wildfire.detected is True      # Fire STILL DETECTED
    assert status_4.landslide.detected is True     # Landslide STILL DETECTED
