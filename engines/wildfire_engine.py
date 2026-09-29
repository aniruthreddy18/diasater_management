"""
Wildfire Processing Engine with NASA FIRMS Corroboration
Multi-Disaster Early Warning System
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from config.settings import settings
from core.models import (
    HazardType,
    StandardPacket,
    HazardEvent,
    WildfireSensorData,
)
from firms.client import firms_client, FirmsClient
from risk.risk_engine import risk_engine
from .base_engine import BaseHazardEngine

logger = logging.getLogger(__name__)


class WildfireEngine(BaseHazardEngine):
    """
    Dedicated engine for Wildfire detection and risk analysis.
    Evaluates ambient temperature, relative humidity depression, smoke density,
    and optical flame triggers.
    Cross-checks active fire conditions against NASA FIRMS satellite observations.
    """

    def __init__(self, thresholds=None, firms: Optional[FirmsClient] = None):
        super().__init__(HazardType.WILDFIRE)
        self.thresholds = thresholds or settings.wildfire
        self.firms = firms or firms_client

    async def process_packet(self, packet: StandardPacket) -> HazardEvent:
        """
        Analyze wildfire telemetry, execute NASA FIRMS satellite corroboration,
        and calculate final risk score.
        """
        data = packet.sensor_data or {}
        temperature = float(data.get("temperature", data.get("bme_temp", 25.0)))
        humidity = float(data.get("humidity", data.get("bme_humidity", 50.0)))
        smoke = float(data.get("smoke", 0.0))
        flame_raw = data.get("flame_raw")
        flame_detected = bool(data.get("flame_detected", (flame_raw is not None and float(flame_raw) <= 1500)))

        mq2_v = float(data.get("mq2_v", 0.0))
        mq135_v = float(data.get("mq135_v", 0.0))
        mq7_v = float(data.get("mq7_v", 0.0))
        dust_ugm3 = float(data.get("dust_ugm3", 0.0))
        battery_v = float(data.get("battery_v", data.get("battery", 0.0)))
        bme_pressure = float(data.get("bme_pressure", 0.0))
        seq_num = data.get("sequence", data.get("packet_seq", data.get("seq", None)))

        # 1. Receiver-aligned alarm level evaluation (matches physical Receiver TFT logic)
        # Receiver logic:
        # level 2: flame_raw <= 1500 or any MQ >= 2.5V or dust >= 150 ug/m3
        # level 1: any MQ >= 1.75V or dust >= 105 ug/m3
        receiver_level = 0
        if flame_detected or mq2_v >= 2.5 or mq135_v >= 2.5 or mq7_v >= 2.5 or dust_ugm3 >= 150.0:
            receiver_level = 2
        elif (mq2_v >= 1.75 or mq135_v >= 1.75 or mq7_v >= 1.75 or dust_ugm3 >= 105.0):
            receiver_level = 1

        # 2. Compute sub-scores (0.0 to 100.0)
        # Temperature baseline ~ 25°C, critical ~ 55°C
        s_temp = min(100.0, max(0.0, ((temperature - 25.0) / (self.thresholds.temperature_critical_c - 25.0)) * 100.0))

        # Low humidity index (inverse: drier air = higher danger, 45% -> 15%)
        s_hum = min(100.0, max(0.0, ((45.0 - humidity) / (45.0 - self.thresholds.humidity_critical_low_pct)) * 100.0))

        # Smoke concentration (0 to critical PPM or MQ-2 voltage)
        smoke_effective = smoke if smoke > 0 else (mq2_v / 2.5 * self.thresholds.smoke_critical_ppm)
        s_smoke = min(100.0, max(0.0, (smoke_effective / self.thresholds.smoke_critical_ppm) * 100.0))

        # Direct optical flame sensor
        s_flame = 100.0 if flame_detected else 0.0

        # Base risk composite calculation
        base_risk = (0.30 * s_temp) + (0.25 * s_hum) + (0.30 * s_smoke) + (0.15 * s_flame)

        if receiver_level >= 2:
            base_risk = max(base_risk, 85.0)
        elif receiver_level == 1:
            base_risk = max(base_risk, 60.0)

        base_risk = risk_engine.clamp_score(base_risk)

        # 3. Detection determination ("Was a dangerous condition detected?")
        critical_breach = (
            flame_detected
            or temperature >= self.thresholds.temperature_critical_c
            or smoke >= self.thresholds.smoke_critical_ppm
            or receiver_level >= 2
        )
        warning_breach = (
            (temperature >= self.thresholds.temperature_warning_c and smoke >= self.thresholds.smoke_warning_ppm)
            or receiver_level == 1
        )
        score_breach = base_risk >= self.thresholds.detection_score_threshold

        detected = bool(critical_breach or warning_breach or score_breach)

        # 4. Resolve high-vulnerability wildfire / chemical gas station
        from core.wildfire_stations import wildfire_station_manager
        st = wildfire_station_manager.get_station(packet.device_id) or wildfire_station_manager.get_active_field_station()

        event_lat = packet.latitude
        event_lon = packet.longitude
        if st and abs(packet.latitude - 17.3918) < 0.001:
            event_lat = st["latitude"]
            event_lon = st["longitude"]

        # NASA FIRMS Corroboration Cross-Check (Section 10 & 11)
        firms_confirmed: Optional[bool] = None
        nearest_firms_distance_km: Optional[float] = None
        firms_adjustment: float = 0.0

        if detected or base_risk >= 40.0:
            firms_result = await self.firms.cross_check(event_lat, event_lon)
            firms_confirmed = firms_result.confirmed
            nearest_firms_distance_km = firms_result.nearest_distance_km

            if firms_confirmed:
                firms_adjustment = firms_result.risk_adjustment  # +15.0 percentage points
                logger.info(
                    "NASA FIRMS MATCH: Hotspot within %.2f km of (%f, %f). Adding +%.1f%% risk bonus.",
                    nearest_firms_distance_km or 0.0, event_lat, event_lon, firms_adjustment
                )
            else:
                logger.info(
                    "NASA FIRMS: No hotspot within configured radius of (%f, %f). Nearest is %s km.",
                    event_lat, event_lon,
                    f"{nearest_firms_distance_km:.2f}" if nearest_firms_distance_km is not None else "None"
                )

        # 5. Final Risk Score Calculation (Capped at 100.0)
        final_risk = risk_engine.clamp_score(base_risk + firms_adjustment)
        risk_level = risk_engine.classify_risk_score(final_risk)

        # 6. Formulate detailed status message with real forest/biome station context
        firms_text = ""
        if firms_confirmed:
            firms_text = f" | [NASA FIRMS CONFIRMED: Hotspot {nearest_firms_distance_km:.1f} km away, +{firms_adjustment:.0f}% risk boost]"
        elif nearest_firms_distance_km is not None:
            firms_text = f" | [NASA FIRMS: Nearest hotspot {nearest_firms_distance_km:.1f} km away (unconfirmed)]"

        st_loc = f"{st['name']} ({st['district']}, {st['state']})" if st else "Forest Sector"

        if critical_breach or receiver_level >= 2:
            msg = (
                f"WILDFIRE EMERGENCY at {st_loc}: Flame={'DETECTED' if flame_detected else 'None'}, "
                f"MQ2 {mq2_v:.2f}V, Temp {temperature:.1f}°C{firms_text}. Threat perimeter: {st.get('downhill_assets', 'Surrounding hamlets')}."
            )
        elif detected or receiver_level == 1:
            msg = (
                f"WILDFIRE DANGER DETECTED at {st_loc}: MQ2 {mq2_v:.2f}V, Temp {temperature:.1f}°C, "
                f"Humidity {humidity:.1f}%{firms_text}."
            )
        else:
            msg = f"Thermal & gas levels normal at {st_loc}. MQ2 {mq2_v:.2f}V, Monitoring active."

        event = HazardEvent(
            event_id=f"WF_{uuid.uuid4().hex[:8]}",
            device_id=packet.device_id,
            hazard_type=HazardType.WILDFIRE,
            latitude=event_lat,
            longitude=event_lon,
            timestamp=packet.timestamp or datetime.now(timezone.utc).isoformat(),
            detected=detected,
            base_risk_score=base_risk,
            firms_confirmed=firms_confirmed,
            nearest_firms_distance_km=nearest_firms_distance_km,
            firms_adjustment=firms_adjustment,
            final_risk_score=final_risk,
            risk_level=risk_level,
            sensor_data={
                "station_id": st["id"] if st else packet.device_id,
                "station_name": st["name"] if st else "Forest Sector",
                "district": st.get("district", "Field District") if st else "",
                "state": st.get("state", "Field State") if st else "",
                "biome": st.get("biome", "Deciduous Forest") if st else "",
                "canopy_fuel": st.get("canopy_fuel", "Dry Leaf Litter") if st else "",
                "elevation_m": st.get("elevation_m", 560) if st else 560,
                "fsi_hazard_class": st.get("fsi_hazard_class", "EXTREME") if st else "EXTREME",
                "downhill_assets": st.get("downhill_assets", "Perimeter Settlements") if st else "",
                "safe_assembly": st.get("safe_assembly", "Forest HQ Clear Buffer") if st else "",
                "temperature": temperature,
                "humidity": humidity,
                "smoke": smoke,
                "flame_detected": flame_detected,
                "mq2_v": mq2_v,
                "mq135_v": mq135_v,
                "mq7_v": mq7_v,
                "dust_ugm3": dust_ugm3,
                "flame_raw": flame_raw,
                "bme_temp": temperature,
                "bme_humidity": humidity,
                "bme_pressure": bme_pressure,
                "battery_v": battery_v,
                "alarm_level": receiver_level,
                "sequence": seq_num,
            },
            message=msg,
        )

        logger.info(
            "Processed Wildfire Packet [%s]: detected=%s, base=%.1f%%, firms_boost=+%.1f%%, final=%.1f%% (%s)",
            packet.device_id, detected, base_risk, firms_adjustment, final_risk, risk_level
        )
        return event


# Global engine instance
wildfire_engine = WildfireEngine()
