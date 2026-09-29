"""
Test Telegram alert formatting, rate limiting / cooldowns, and dispatch.
"""

import time
import pytest
from core.models import HazardEvent, HazardType, RiskLevel
from alerts.formatter import format_telegram_alert
from alerts.telegram_bot import TelegramAlertDispatcher


def test_telegram_message_formatter_content():
    event = HazardEvent(
        event_id="EV_FIRE_TEST",
        device_id="FIRE_001",
        hazard_type=HazardType.WILDFIRE,
        latitude=17.3850,
        longitude=78.4867,
        timestamp="2026-09-27T11:30:00Z",
        detected=True,
        base_risk_score=65.0,
        firms_confirmed=True,
        nearest_firms_distance_km=4.25,
        firms_adjustment=15.0,
        final_risk_score=80.0,
        risk_level=RiskLevel.HIGH,
        sensor_data={"temperature": 48.2, "smoke": 734.0, "humidity": 21.0},
        message="Wildfire danger verified.",
    )

    msg = format_telegram_alert(event)

    # Check key requirements from Section 16:
    # Disaster type emoji & name
    assert "🔥 *WILDFIRE EARLY WARNING ALERT* 🔥" in msg
    # Location / coordinates
    assert "17.3850, 78.4867" in msg
    # Google maps link
    assert "https://www.google.com/maps?q=17.385,78.4867" in msg
    # Risk level & score
    assert "Risk Level:* `HIGH`" in msg
    assert "Risk Score:* `80.0%` (Base: `65.0%`)" in msg
    # Relevant sensor information
    assert "Temperature: `48.20`" in msg
    assert "Smoke: `734.00`" in msg
    # NASA FIRMS confirmation
    assert "NASA FIRMS Corroboration:* `CONFIRMED`" in msg
    assert "4.25 km" in msg
    assert "+15%" in msg


@pytest.mark.asyncio
async def test_alert_cooldown_throttling():
    dispatcher = TelegramAlertDispatcher(cooldown_seconds=60.0, min_risk_level="HIGH")

    event_high_1 = HazardEvent(
        event_id="EV_1",
        device_id="FLOOD_001",
        hazard_type=HazardType.FLASH_FLOOD,
        latitude=17.3780,
        longitude=78.4950,
        timestamp="2026-09-27T11:00:00Z",
        detected=True,
        base_risk_score=75.0,
        final_risk_score=75.0,
        risk_level=RiskLevel.HIGH,
        sensor_data={"water_level": 230.0},
        message="Flash flood stage critical.",
    )

    # First alert should succeed
    alert1 = await dispatcher.send_event_alert(event_high_1)
    assert alert1 is not None
    assert alert1.hazard_type == HazardType.FLASH_FLOOD

    # Immediate second alert for same device should be throttled by 60s cooldown
    alert2 = await dispatcher.send_event_alert(event_high_1)
    assert alert2 is None  # Throttled

    # However, an escalation to EXTREME must bypass cooldown
    event_extreme = HazardEvent(
        event_id="EV_2",
        device_id="FLOOD_001",
        hazard_type=HazardType.FLASH_FLOOD,
        latitude=17.3780,
        longitude=78.4950,
        timestamp="2026-09-27T11:00:05Z",
        detected=True,
        base_risk_score=95.0,
        final_risk_score=95.0,
        risk_level=RiskLevel.EXTREME,
        sensor_data={"water_level": 290.0},
        message="Catastrophic flash flood dam break surge.",
    )

    alert_esc = await dispatcher.send_event_alert(event_extreme)
    assert alert_esc is not None
    assert alert_esc.risk_level == RiskLevel.EXTREME
