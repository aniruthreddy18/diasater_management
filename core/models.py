"""
Core Data Models
Multi-Disaster Early Warning System
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class HazardType(str, Enum):
    """Supported disaster hazard types."""
    LANDSLIDE = "LANDSLIDE"
    FLASH_FLOOD = "FLASH_FLOOD"
    WILDFIRE = "WILDFIRE"


class RiskLevel(str, Enum):
    """Categorized risk severity levels."""
    NORMAL = "NORMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class LandslideSensorData(BaseModel):
    """Sensor readings specific to landslide monitoring hardware."""
    tilt_angle: float = Field(..., description="Slope tilt angle in degrees")
    soil_moisture: float = Field(..., description="Volumetric soil water content percentage (0-100%)")
    vibration_intensity: float = Field(default=0.0, description="Seismic/ground vibration in g-force")
    pore_pressure: Optional[float] = Field(default=0.0, description="Soil pore water pressure in kPa")


class FloodSensorData(BaseModel):
    """Sensor readings specific to flash flood monitoring hardware."""
    water_level: float = Field(..., description="Water depth/stage in centimeters")
    rate_of_rise: float = Field(default=0.0, description="Rate of water level increase in cm/min")
    rainfall_rate: float = Field(default=0.0, description="Precipitation rate in mm/hour")
    water_flow: Optional[float] = Field(default=0.0, description="Surface flow velocity in m/s")


class WildfireSensorData(BaseModel):
    """Sensor readings specific to wildfire monitoring hardware."""
    temperature: float = Field(..., description="Ambient air temperature in Celsius")
    humidity: float = Field(..., description="Relative humidity percentage (0-100%)")
    smoke: float = Field(..., description="Smoke/gas sensor reading in PPM or raw ADC")
    flame_detected: Optional[bool] = Field(default=False, description="IR flame sensor binary trigger")


class StandardPacket(BaseModel):
    """
    Standardized telemetry packet format defined in Section 6 of project brief.
    Every hardware system or receiver emits this uniform data structure.
    """
    device_id: str = Field(..., description="Unique hardware identifier, e.g. FIRE_001, FLOOD_001, LANDSLIDE_001")
    hazard_type: HazardType = Field(..., description="Associated hazard category")
    latitude: float = Field(..., description="Geographic latitude coordinate")
    longitude: float = Field(..., description="Geographic longitude coordinate")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of reading"
    )
    sensor_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hazard-specific sensor fields"
    )

    @field_validator("hazard_type", mode="before")
    @classmethod
    def normalize_hazard_type(cls, v: Any) -> HazardType:
        if isinstance(v, str):
            v_upper = v.upper().replace("-", "_").replace(" ", "_")
            if v_upper in ("FLOOD", "FLASHFLOOD"):
                return HazardType.FLASH_FLOOD
            if v_upper in ("FIRE", "WILD_FIRE"):
                return HazardType.WILDFIRE
            return HazardType(v_upper)
        return v


class RawIngestPacket(BaseModel):
    """Flexible incoming packet structure for physical hardware ingestion."""
    device_id: str
    hazard_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[str] = None
    sensor_data: Dict[str, Any] = Field(default_factory=dict)
    use_receiver_gps: bool = False


class HazardEvent(BaseModel):
    """
    Evaluated hazard event output by an independent disaster processing engine.
    """
    event_id: str = Field(..., description="Unique identifier for the evaluation event")
    device_id: str = Field(..., description="Originating hardware node")
    hazard_type: HazardType = Field(..., description="Disaster type")
    latitude: float = Field(..., description="GPS Latitude")
    longitude: float = Field(..., description="GPS Longitude")
    timestamp: str = Field(..., description="Timestamp of evaluation")
    detected: bool = Field(..., description="True if dangerous conditions detected")
    base_risk_score: float = Field(..., description="Raw risk score 0.0 - 100.0 from sensor analysis")
    firms_confirmed: Optional[bool] = Field(
        default=None,
        description="True if NASA FIRMS satellite hotspot corroborated the wildfire"
    )
    nearest_firms_distance_km: Optional[float] = Field(
        default=None,
        description="Distance to nearest NASA FIRMS hotspot in km (for wildfire)"
    )
    firms_adjustment: float = Field(
        default=0.0,
        description="Score adjustment added from NASA FIRMS corroboration"
    )
    final_risk_score: float = Field(..., description="Final risk score capped at 100.0")
    risk_level: RiskLevel = Field(..., description="Qualitative risk classification")
    sensor_data: Dict[str, Any] = Field(default_factory=dict)
    message: str = Field(default="", description="Human-readable assessment summary")


class DisasterState(BaseModel):
    """
    Current independent status of a single disaster type.
    Maintained independently to guarantee simultaneous tracking.
    """
    hazard_type: HazardType
    device_id: Optional[str] = None
    detected: bool = False
    status_label: str = "NORMAL"
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.NORMAL
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_updated: Optional[str] = None
    last_detection_time: Optional[str] = None
    sensor_data: Dict[str, Any] = Field(default_factory=dict)
    firms_confirmed: Optional[bool] = None
    nearest_firms_distance_km: Optional[float] = None
    message: str = "System normal. No hazards detected."


class MultiDisasterStatus(BaseModel):
    """
    Unified multi-disaster system status snapshot.
    Reflects all three independent disaster states simultaneously.
    """
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    landslide: DisasterState
    flash_flood: DisasterState
    wildfire: DisasterState
    active_hazard_count: int = 0
    receiver_coordinates: Dict[str, Any] = Field(default_factory=dict)


class AlertRecord(BaseModel):
    """Record of an emitted alert."""
    alert_id: str
    hazard_type: HazardType
    device_id: str
    risk_level: RiskLevel
    risk_score: float
    latitude: float
    longitude: float
    timestamp: str
    message: str
    channel: str = "TELEGRAM"
    delivered: bool = False
    error: Optional[str] = None
