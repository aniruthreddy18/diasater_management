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

        # 5. Formulate status message with real river basin station context
        from core.flood_stations import flood_station_manager
        st = flood_station_manager.get_station(packet.device_id) or flood_station_manager.get_active_field_station()

        event_lat = packet.latitude
        event_lon = packet.longitude
        if st and abs(packet.latitude - 17.3918) < 0.001:
            event_lat = st["latitude"]
            event_lon = st["longitude"]

        st_loc = f"{st['name']} ({st['district']}, {st['state']})" if st else "River Corridor"

        if critical_breach:
            msg = (
                f"FLASH FLOOD SURGE IMMINENT at {st_loc}: Stage {water_level:.1f} cm (crit: {self.thresholds.water_level_critical_cm} cm), "
                f"Rising at {rate_of_rise:.1f} cm/min. Inundation risk for: {st.get('downhill_assets', 'Downhill riverine tracts')}."
            )
        elif detected:
            msg = (
                f"FLOOD WARNING DETECTED at {st_loc}: Stage {water_level:.1f} cm, Rainfall {rainfall_rate:.1f} mm/h."
            )
        else:
            msg = f"Waterway levels normal at {st_loc}. Stage {water_level:.1f} cm, Monitoring active."

        event = HazardEvent(
            event_id=f"FF_{uuid.uuid4().hex[:8]}",
            device_id=packet.device_id,
            hazard_type=HazardType.FLASH_FLOOD,
            latitude=event_lat,
            longitude=event_lon,
            timestamp=packet.timestamp or datetime.now(timezone.utc).isoformat(),
            detected=detected,
            base_risk_score=base_risk,
            firms_confirmed=None,  # Not applicable to Flash Flood
            nearest_firms_distance_km=None,
            firms_adjustment=0.0,
            final_risk_score=final_risk,
            risk_level=risk_level,
            sensor_data={
                "station_id": st["id"] if st else packet.device_id,
                "station_name": st["name"] if st else "River Basin",
                "district": st.get("district", "Field District") if st else "",
                "state": st.get("state", "Field State") if st else "",
                "waterway": st.get("waterway", "River Channel") if st else "",
                "elevation_m": st.get("elevation_m", 84) if st else 84,
                "danger_level_m": st.get("danger_level_m", 86.0) if st else 86.0,
                "cwc_index": st.get("cwc_index", "EXTREME") if st else "EXTREME",
                "downhill_assets": st.get("downhill_assets", "Downstream Villages") if st else "",
                "safe_assembly": st.get("safe_assembly", "Elevated Relief Camps") if st else "",
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
