"""
Alert Message Formatter
Multi-Disaster Early Warning System
"""

from typing import Dict, Any
from core.models import HazardEvent, HazardType, RiskLevel
from risk.risk_engine import risk_engine

DISASTER_EMOJIS = {
    HazardType.WILDFIRE: "🔥",
    HazardType.FLASH_FLOOD: "🌊",
    HazardType.LANDSLIDE: "⛰️",
}

RISK_ICONS = {
    RiskLevel.NORMAL: "🟢",
    RiskLevel.LOW: "🟡",
    RiskLevel.MEDIUM: "🟠",
    RiskLevel.HIGH: "🔴",
    RiskLevel.EXTREME: "🚨",
}


def format_telegram_alert(event: HazardEvent) -> str:
    """
    Format a standardized, high-urgency Telegram alert markdown message
    as specified in Section 16 of the project brief.
    """
    emoji = DISASTER_EMOJIS.get(event.hazard_type, "⚠️")
    risk_icon = RISK_ICONS.get(event.risk_level, "⚠️")
    type_display = event.hazard_type.value.replace("_", " ")

    lines = [
        f"{emoji} *{type_display} EARLY WARNING ALERT* {emoji}",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"*{risk_icon} Risk Level:* `{event.risk_level.value}`",
        f"*📊 Risk Score:* `{event.final_risk_score:.1f}%` (Base: `{event.base_risk_score:.1f}%`)",
        f"*📡 Device ID:* `{event.device_id}`",
        f"*📍 Location (GPS):* `{event.latitude:.4f}, {event.longitude:.4f}`",
        f"[🗺️ Open in Google Maps](https://www.google.com/maps?q={event.latitude},{event.longitude})",
        "",
        "*📈 Sensor Telemetry:*",
    ]

    # Format sensor fields cleanly
    for key, val in (event.sensor_data or {}).items():
        key_label = key.replace("_", " ").title()
        if isinstance(val, float):
            lines.append(f"  • {key_label}: `{val:.2f}`")
        elif isinstance(val, bool):
            lines.append(f"  • {key_label}: `{'YES' if val else 'NO'}`")
        else:
            lines.append(f"  • {key_label}: `{val}`")

    # Add NASA FIRMS confirmation if Wildfire
    if event.hazard_type == HazardType.WILDFIRE:
        lines.append("")
        if event.firms_confirmed:
            lines.append(
                f"*🛰️ NASA FIRMS Corroboration:* `CONFIRMED` ✅\n"
                f"  • Satellite Hotspot: `{event.nearest_firms_distance_km:.2f} km` away\n"
                f"  • Risk Adjustment: `+{event.firms_adjustment:.0f}%`"
            )
        elif event.nearest_firms_distance_km is not None:
            lines.append(
                f"*🛰️ NASA FIRMS Corroboration:* `UNCONFIRMED` ⚠️\n"
                f"  • Nearest Hotspot: `{event.nearest_firms_distance_km:.2f} km` away (exceeds threshold)"
            )
        else:
            lines.append("*🛰️ NASA FIRMS Corroboration:* `No satellite thermal anomalies detected`")

    # Locality Risk Radius Classification
    radii = risk_engine.calculate_risk_radii_km(event.hazard_type.value, event.final_risk_score)
    lines.extend([
        "",
        "*🎯 Locality Risk Radius Classification:*",
        f"  • 🔴 *VERY DANGER (Mandatory Evac):* `< {radii['very_danger_km']:.2f} km`",
        f"  • 🟠 *DANGER (High Warning):* `< {radii['danger_km']:.2f} km`",
        f"  • 🟡 *MODERATE DANGER (Advisory):* `< {radii['moderate_danger_km']:.2f} km`",
    ])

    lines.extend([
        "",
        f"*🕒 Timestamp:* `{event.timestamp}`",
        f"*📝 Assessment:* _{event.message}_",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"_Automated Alert from Multi-Disaster Central Receiver System_"
    ])

    return "\n".join(lines)
