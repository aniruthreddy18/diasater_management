"""
Flash Flood Processing Engine
Multi-Disaster Early Warning System
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from config.settings import settings
from core.models import (
    HazardType,
    StandardPacket,
    HazardEvent,
    FloodSensorData,
)
from risk.risk_engine import risk_engine
from .base_engine import BaseHazardEngine

logger = logging.getLogger(__name__)


class FloodEngine(BaseHazardEngine):
    """
    Dedicated engine for Flash Flood detection and risk analysis.
    Evaluates water level stage, rate of rise, rainfall intensity, and surface flow velocity.
    """

    def __init__(self, thresholds=None):
        super().__init__(HazardType.FLASH_FLOOD)
        self.thresholds = thresholds or settings.flood

    async def process_packet(self, packet: StandardPacket) -> HazardEvent:
        """
        Analyze flash flood sensor telemetry and compute risk score.
        """
        data = packet.sensor_data or {}
        dist = float(data.get("distance_cm", data.get("distance", -1.0)))
        water_level = float(data.get("water_level", data.get("stage_cm", 0.0)))
        if water_level == 0.0 and dist >= 0:
            water_level = max(0.0, 200.0 - dist)

        rate_of_rise = float(data.get("rate_of_rise", 0.0))
        rainfall_rate = float(data.get("rainfall_rate", data.get("rain_pct", 0.0)))
        water_flow = float(data.get("water_flow", data.get("flow_lpm", 0.0)))
        temp_c = float(data.get("temp_c", data.get("temperature", 0.0)))
        humidity_pct = float(data.get("humidity_pct", data.get("humidity", 0.0)))
        battery_v = float(data.get("battery_v", data.get("battery", 0.0)))

        # 1. Compute sub-scores (0.0 to 100.0)
        s_level = min(100.0, max(0.0, (water_level / self.thresholds.water_level_critical_cm) * 100.0))
        s_rise = min(100.0, max(0.0, (rate_of_rise / self.thresholds.rate_of_rise_critical_cm_min) * 100.0))
        s_rain = min(100.0, max(0.0, (rainfall_rate / self.thresholds.rainfall_critical_mm_h) * 100.0))
        s_flow = min(100.0, max(0.0, (water_flow / self.thresholds.flow_critical_m_s) * 100.0))

        # 2. Weighted multi-parameter risk composite
        # Water stage and rapid surge rate are primary indicators of flash flooding
        base_risk = (0.40 * s_level) + (0.30 * s_rise) + (0.20 * s_rain) + (0.10 * s_flow)
        
        # Respect direct hardware alarm level trigger if present (0=clear, 1=warn, 2=alarm)
        alarm_level = int(data.get("alarm_level", 0))
        if alarm_level >= 2:
            base_risk = max(base_risk, 88.0)
        elif alarm_level == 1:
            base_risk = max(base_risk, 65.0)

        base_risk = risk_engine.clamp_score(base_risk)

        # 3. Detection determination
        critical_breach = (
            water_level >= self.thresholds.water_level_critical_cm
            or rate_of_rise >= self.thresholds.rate_of_rise_critical_cm_min
            or alarm_level >= 2
        )
        warning_breach = (
            water_level >= self.thresholds.water_level_warning_cm
            and rainfall_rate >= self.thresholds.rainfall_warning_mm_h
        ) or alarm_level == 1
        score_breach = base_risk >= self.thresholds.detection_score_threshold

        detected = bool(critical_breach or warning_breach or score_breach)

        # 4. Final risk classification
        final_risk = base_risk
        risk_level = risk_engine.classify_risk_score(final_risk)

        # 5. Formulate status message
        if critical_breach:
            msg = (
                f"FLASH FLOOD IMMINENT: Stage {water_level:.1f} cm (crit: {self.thresholds.water_level_critical_cm} cm), "
                f"Rising at {rate_of_rise:.1f} cm/min, Rainfall {rainfall_rate:.1f} mm/h."
            )
        elif detected:
            msg = (
                f"FLOOD WARNING DETECTED: Stage {water_level:.1f} cm, Rainfall {rainfall_rate:.1f} mm/h, "
                f"Flow {water_flow:.1f} m/s."
            )
        else:
            msg = f"Waterways normal. Stage {water_level:.1f} cm, Rainfall {rainfall_rate:.1f} mm/h."

        event = HazardEvent(
            event_id=f"FF_{uuid.uuid4().hex[:8]}",
            device_id=packet.device_id,
            hazard_type=HazardType.FLASH_FLOOD,
            latitude=packet.latitude,
            longitude=packet.longitude,
            timestamp=packet.timestamp or datetime.now(timezone.utc).isoformat(),
            detected=detected,
            base_risk_score=base_risk,
            firms_confirmed=None,  # Not applicable to Flash Flood
            nearest_firms_distance_km=None,
            firms_adjustment=0.0,
            final_risk_score=final_risk,
            risk_level=risk_level,
            sensor_data={
                "distance_cm": dist,
                "water_level": water_level,
                "flow_lpm": water_flow,
                "rain_pct": rainfall_rate,
                "temp_c": temp_c,
                "humidity_pct": humidity_pct,
                "battery_v": battery_v,
                "rate_of_rise": rate_of_rise,
                "rainfall_rate": rainfall_rate,
                "water_flow": water_flow,
            },
            message=msg,
        )

        logger.info("Processed Flood Packet [%s]: detected=%s, risk=%.1f%% (%s)",
                    packet.device_id, detected, final_risk, risk_level)
        return event


# Global engine instance
flood_engine = FloodEngine()
