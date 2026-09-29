"""
Landslide Processing Engine
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
    LandslideSensorData,
)
from risk.risk_engine import risk_engine
from .base_engine import BaseHazardEngine

logger = logging.getLogger(__name__)


class LandslideEngine(BaseHazardEngine):
    """
    Dedicated engine for Landslide detection and risk analysis.
    Evaluates slope tilt, soil moisture saturation, ground vibration, and pore water pressure.
    """

    def __init__(self, thresholds=None):
        super().__init__(HazardType.LANDSLIDE)
        self.thresholds = thresholds or settings.landslide

    async def process_packet(self, packet: StandardPacket) -> HazardEvent:
        """
        Analyze landslide sensor telemetry and compute risk score.
        """
        # Parse or default sensor parameters
        data = packet.sensor_data or {}
        tilt = float(data.get("tilt_angle", 0.0))
        moisture = float(data.get("soil_moisture", data.get("soil_pct", 0.0)))
        vibration = float(data.get("vibration_intensity", 0.0))
        pore_pressure = float(data.get("pore_pressure", 0.0))
        pressure_raw = data.get("pressure_raw")
        rain_pct = float(data.get("rain_pct", 0.0))
        battery_v = float(data.get("battery_v", data.get("battery", 0.0)))
        solar_v = float(data.get("solar_v", data.get("solar", 0.0)))
        alarm_level = int(data.get("alarm_level", 0))

        # 1. Compute sub-scores (0.0 to 100.0)
        s_tilt = min(100.0, max(0.0, (tilt / self.thresholds.tilt_critical_deg) * 100.0))
        s_moist = min(100.0, max(0.0, (moisture / self.thresholds.soil_moisture_critical_pct) * 100.0))
        s_vib = min(100.0, max(0.0, (vibration / self.thresholds.vibration_critical_g) * 100.0))
        s_pore = min(100.0, max(0.0, (pore_pressure / self.thresholds.pore_pressure_critical_kpa) * 100.0))

        # 2. Weighted multi-parameter risk composite
        base_risk = (0.35 * s_tilt) + (0.35 * s_moist) + (0.20 * s_vib) + (0.10 * s_pore)

        # Re-derive receiver-aligned level (matches physical receiver TFT banner)
        # Receiver logic: Soil >= 80% or Rain >= 85% -> ALARM; Soil >= 56% or Rain >= 59.5% -> WARN
        if moisture >= 80.0 or rain_pct >= 85.0:
            receiver_level = 2
        elif moisture >= 56.0 or rain_pct >= 59.5:
            receiver_level = 1
        else:
            receiver_level = 0

        if receiver_level >= 2:
            base_risk = max(base_risk, 88.0)
        elif receiver_level == 1:
            base_risk = max(base_risk, 65.0)

        base_risk = risk_engine.clamp_score(base_risk)

        # 3. Detection determination ("Was a dangerous condition detected?")
        critical_breach = (
            tilt >= self.thresholds.tilt_critical_deg
            or moisture >= self.thresholds.soil_moisture_critical_pct
            or vibration >= self.thresholds.vibration_critical_g
            or receiver_level >= 2
        )
        warning_breach = (
            (
                tilt >= self.thresholds.tilt_warning_deg
                and moisture >= self.thresholds.soil_moisture_warning_pct
            )
            or receiver_level == 1
        )
        score_breach = base_risk >= self.thresholds.detection_score_threshold

        detected = bool(critical_breach or warning_breach or score_breach)

        # 4. Final risk classification
        final_risk = base_risk
        risk_level = risk_engine.classify_risk_score(final_risk)

        # 5. Formulate status message with real geographical station context
        from core.landslide_stations import landslide_station_manager
        st = landslide_station_manager.get_station(packet.device_id) or landslide_station_manager.get_active_field_station()

        # If packet uses default indoor GPS, map to the active vulnerable station GPS
        event_lat = packet.latitude
        event_lon = packet.longitude
        if st and abs(packet.latitude - 17.3918) < 0.001:
            event_lat = st["latitude"]
            event_lon = st["longitude"]

        st_loc = f"{st['name']} ({st['district']}, {st['state']})" if st else "Slope Sector"

        if critical_breach or receiver_level >= 2:
            msg = (
                f"CRITICAL SLOPE INSTABILITY at {st_loc}: "
                f"Soil moisture {moisture:.1f}%, Rain {rain_pct:.1f}%. Downhill assets at immediate risk: {st.get('downhill_assets', 'Valley settlements')}."
            )
        elif detected or receiver_level == 1:
            msg = (
                f"LANDSLIDE WARNING at {st_loc}: "
                f"Soil {moisture:.1f}%, Rain {rain_pct:.1f}%."
            )
        else:
            msg = f"Slope conditions stable at {st_loc}. Monitoring active."

        seq_num = data.get("sequence", data.get("packet_seq", data.get("seq", None)))

        event = HazardEvent(
            event_id=f"LS_{uuid.uuid4().hex[:8]}",
            device_id=packet.device_id,
            hazard_type=HazardType.LANDSLIDE,
            latitude=event_lat,
            longitude=event_lon,
            timestamp=packet.timestamp or datetime.now(timezone.utc).isoformat(),
            detected=detected,
            base_risk_score=base_risk,
            firms_confirmed=None,  # Not applicable to Landslide
            nearest_firms_distance_km=None,
            firms_adjustment=0.0,
            final_risk_score=final_risk,
            risk_level=risk_level,
            sensor_data={
                "station_id": st["id"] if st else packet.device_id,
                "station_name": st["name"] if st else "Field Slope",
                "district": st.get("district", "Field District") if st else "",
                "state": st.get("state", "Field State") if st else "",
                "elevation_m": st.get("elevation_m", 810) if st else 810,
                "slope_deg": st.get("slope_deg", 44) if st else 44,
                "geology": st.get("geology", "Weathered Strata") if st else "",
                "downhill_assets": st.get("downhill_assets", "Lifeline Road") if st else "",
                "safe_assembly": st.get("safe_assembly", "High Ground") if st else "",
                "tilt_angle": tilt,
                "soil_moisture": moisture,
                "soil_pct": float(data.get("soil_pct", moisture)),
                "vibration_intensity": vibration,
                "pore_pressure": pore_pressure,
                "pressure_raw": int(pressure_raw) if pressure_raw is not None else None,
                "rain_pct": rain_pct,
                "battery_v": battery_v,
                "solar_v": solar_v,
                "alarm_level": receiver_level,
                "sequence": seq_num,
            },
            message=msg,
        )

        logger.info("Processed Landslide Packet [%s]: detected=%s, risk=%.1f%% (%s)",
                    packet.device_id, detected, final_risk, risk_level)
        return event


# Global engine instance
landslide_engine = LandslideEngine()
