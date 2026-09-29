"""
System Configuration & Settings
Multi-Disaster Early Warning System
"""

import os
from typing import Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


class CentralReceiverConfig(BaseModel):
    """Configuration for Central Receiver & GPS."""
    default_latitude: float = float(os.getenv("RECEIVER_LATITUDE", "17.3918"))
    default_longitude: float = float(os.getenv("RECEIVER_LONGITUDE", "78.3194"))
    device_id: str = "CENTRAL_RECEIVER_01"


class LandslideThresholds(BaseModel):
    """Configurable thresholds for Landslide detection & risk."""
    tilt_warning_deg: float = 12.0
    tilt_critical_deg: float = 25.0
    soil_moisture_warning_pct: float = 65.0
    soil_moisture_critical_pct: float = 85.0
    vibration_warning_g: float = 0.4
    vibration_critical_g: float = 0.8
    pore_pressure_warning_kpa: float = 35.0
    pore_pressure_critical_kpa: float = 60.0
    detection_score_threshold: float = 50.0


class FloodThresholds(BaseModel):
    """Configurable thresholds for Flash Flood detection & risk."""
    water_level_warning_cm: float = 120.0
    water_level_critical_cm: float = 220.0
    rate_of_rise_warning_cm_min: float = 3.0
    rate_of_rise_critical_cm_min: float = 8.0
    rainfall_warning_mm_h: float = 25.0
    rainfall_critical_mm_h: float = 60.0
    flow_warning_m_s: float = 2.0
    flow_critical_m_s: float = 4.5
    detection_score_threshold: float = 50.0


class WildfireThresholds(BaseModel):
    """Configurable thresholds for Wildfire detection & risk."""
    temperature_warning_c: float = 42.0
    temperature_critical_c: float = 55.0
    humidity_warning_low_pct: float = 25.0
    humidity_critical_low_pct: float = 15.0
    smoke_warning_ppm: float = 400.0
    smoke_critical_ppm: float = 750.0
    detection_score_threshold: float = 50.0


class FirmsConfig(BaseModel):
    """Configuration for NASA FIRMS Cross-Check."""
    map_key: str = os.getenv("NASA_FIRMS_MAP_KEY", "")
    match_radius_km: float = float(os.getenv("FIRMS_MATCH_RADIUS_KM", "25.0"))
    risk_boost_percentage_points: float = float(os.getenv("FIRMS_RISK_BOOST", "15.0"))
    mock_fallback: bool = os.getenv("FIRMS_MOCK_FALLBACK", "true").lower() == "true"
    api_base_url: str = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


class RiskThresholds(BaseModel):
    """Risk Level Classification Thresholds."""
    normal_max: float = 24.0
    low_max: float = 49.0
    medium_max: float = 69.0
    high_max: float = 84.0
    # Extreme is 85.0 - 100.0


class TelegramConfig(BaseModel):
    """Telegram Alert Dispatcher Configuration."""
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    cooldown_seconds: float = float(os.getenv("TELEGRAM_ALERT_COOLDOWN_SECONDS", "60.0"))
    min_alert_risk_level: str = os.getenv("TELEGRAM_MIN_RISK_LEVEL", "HIGH")
    api_url: str = "https://api.telegram.org/bot"


class AppSettings(BaseModel):
    """Unified application settings."""
    app_name: str = "Multi-Disaster Early Warning System"
    version: str = "1.0.0"
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8000"))
    receiver: CentralReceiverConfig = Field(default_factory=CentralReceiverConfig)
    landslide: LandslideThresholds = Field(default_factory=LandslideThresholds)
    flood: FloodThresholds = Field(default_factory=FloodThresholds)
    wildfire: WildfireThresholds = Field(default_factory=WildfireThresholds)
    firms: FirmsConfig = Field(default_factory=FirmsConfig)
    risk: RiskThresholds = Field(default_factory=RiskThresholds)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


# Global settings instance
settings = AppSettings()
