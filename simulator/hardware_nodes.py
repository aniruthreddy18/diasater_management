"""
Independent Hardware Node Simulators
Multi-Disaster Early Warning System
"""

import random
from datetime import datetime, timezone
from typing import Dict, Any, List

from core.models import HazardType


class LandslideHardwareNode:
    """
    Dedicated Hardware System 1 — Landslide Monitoring Node
    Sensors: Inclinometer/Tilt, Soil Moisture Sensor, Geophone/Vibration, Pore Pressure.
    """

    def __init__(self, device_id: str = "LANDSLIDE_001", latitude: float = 17.3920, longitude: float = 78.4720):
        self.device_id = device_id
        self.latitude = latitude
        self.longitude = longitude

    def generate_packet(self, condition: str = "normal") -> Dict[str, Any]:
        """Generate sensor packet for given environmental condition."""
        if condition == "critical":
            tilt = round(random.uniform(26.0, 34.0), 1)
            moist = round(random.uniform(86.0, 96.0), 1)
            vib = round(random.uniform(0.82, 1.40), 2)
            pore = round(random.uniform(62.0, 80.0), 1)
        elif condition == "warning":
            tilt = round(random.uniform(13.0, 18.0), 1)
            moist = round(random.uniform(67.0, 78.0), 1)
            vib = round(random.uniform(0.35, 0.55), 2)
            pore = round(random.uniform(36.0, 48.0), 1)
        else:  # normal
            tilt = round(random.uniform(1.0, 4.0), 1)
            moist = round(random.uniform(20.0, 35.0), 1)
            vib = round(random.uniform(0.01, 0.08), 2)
            pore = round(random.uniform(5.0, 15.0), 1)

        return {
            "device_id": self.device_id,
            "hazard_type": "LANDSLIDE",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor_data": {
                "tilt_angle": tilt,
                "soil_moisture": moist,
                "vibration_intensity": vib,
                "pore_pressure": pore,
            },
        }


class FloodHardwareNode:
    """
    Dedicated Hardware System 2 — Flash Flood Monitoring Node
    Sensors: Ultrasonic Water Depth, Rate of Rise, Rain Gauge, Flow Velocity.
    """

    def __init__(self, device_id: str = "FLOOD_001", latitude: float = 17.3780, longitude: float = 78.4950):
        self.device_id = device_id
        self.latitude = latitude
        self.longitude = longitude

    def generate_packet(self, condition: str = "normal") -> Dict[str, Any]:
        """Generate sensor packet for given environmental condition."""
        if condition == "critical":
            level = round(random.uniform(225.0, 290.0), 1)
            rise = round(random.uniform(8.5, 14.0), 1)
            rain = round(random.uniform(65.0, 110.0), 1)
            flow = round(random.uniform(4.6, 6.2), 1)
        elif condition == "warning":
            level = round(random.uniform(125.0, 160.0), 1)
            rise = round(random.uniform(3.2, 5.0), 1)
            rain = round(random.uniform(28.0, 45.0), 1)
            flow = round(random.uniform(2.1, 3.2), 1)
        else:  # normal
            level = round(random.uniform(25.0, 50.0), 1)
            rise = round(random.uniform(0.0, 0.5), 1)
            rain = round(random.uniform(0.0, 5.0), 1)
            flow = round(random.uniform(0.2, 0.8), 1)

        return {
            "device_id": self.device_id,
            "hazard_type": "FLASH_FLOOD",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor_data": {
                "water_level": level,
                "rate_of_rise": rise,
                "rainfall_rate": rain,
                "water_flow": flow,
            },
        }


class WildfireHardwareNode:
    """
    Dedicated Hardware System 3 — Wildfire Monitoring Node
    Sensors: High-Temp Thermistor, Relative Humidity, MQ-2 Gas/Smoke, Optical Flame.
    """

    def __init__(self, device_id: str = "FIRE_001", latitude: float = 17.4050, longitude: float = 78.5020):
        self.device_id = device_id
        self.latitude = latitude
        self.longitude = longitude

    def generate_packet(self, condition: str = "normal") -> Dict[str, Any]:
        """Generate sensor packet for given environmental condition."""
        if condition == "critical":
            temp = round(random.uniform(56.0, 72.0), 1)
            hum = round(random.uniform(8.0, 14.0), 1)
            smoke = round(random.uniform(760.0, 950.0), 0)
            flame = True
        elif condition == "warning":
            temp = round(random.uniform(43.0, 49.0), 1)
            hum = round(random.uniform(18.0, 24.0), 1)
            smoke = round(random.uniform(420.0, 580.0), 0)
            flame = False
        else:  # normal
            temp = round(random.uniform(24.0, 32.0), 1)
            hum = round(random.uniform(45.0, 65.0), 1)
            smoke = round(random.uniform(40.0, 110.0), 0)
            flame = False

        return {
            "device_id": self.device_id,
            "hazard_type": "WILDFIRE",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor_data": {
                "temperature": temp,
                "humidity": hum,
                "smoke": smoke,
                "flame_detected": flame,
            },
        }
