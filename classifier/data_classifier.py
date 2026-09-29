"""
Hardware Identification & Hazard Classification Engine
Multi-Disaster Early Warning System
"""

import logging
from typing import Dict, Any, Optional

from core.models import (
    StandardPacket,
    HazardType,
    HazardEvent,
)
from engines.landslide_engine import landslide_engine, LandslideEngine
from engines.flood_engine import flood_engine, FloodEngine
from engines.wildfire_engine import wildfire_engine, WildfireEngine

logger = logging.getLogger(__name__)


class DataClassifier:
    """
    Classifies incoming telemetry packets from the Central Receiver
    and routes them to the appropriate independent disaster pipeline.
    """

    def __init__(
        self,
        ls_engine: Optional[LandslideEngine] = None,
        fl_engine: Optional[FloodEngine] = None,
        wf_engine: Optional[WildfireEngine] = None,
    ):
        self.landslide_engine = ls_engine or landslide_engine
        self.flood_engine = fl_engine or flood_engine
        self.wildfire_engine = wf_engine or wildfire_engine

    def identify_hazard_type(self, device_id: str, explicit_type: Optional[Any] = None) -> HazardType:
        """
        Identify hazard type from device_id prefix and/or explicit hazard_type attribute.
        """
        # 1. If explicit valid type provided, respect it
        if explicit_type:
            if isinstance(explicit_type, HazardType):
                return explicit_type
            if isinstance(explicit_type, str):
                norm = explicit_type.upper().strip().replace("-", "_").replace(" ", "_")
                if norm in ("WILDFIRE", "FIRE", "WILD_FIRE"):
                    return HazardType.WILDFIRE
                if norm in ("FLASH_FLOOD", "FLOOD", "FLASHFLOOD"):
                    return HazardType.FLASH_FLOOD
                if norm in ("LANDSLIDE", "SLOPE"):
                    return HazardType.LANDSLIDE

        # 2. Derive from device_id prefix convention
        dev_upper = device_id.upper().strip()
        if dev_upper.startswith(("FIRE", "WILDFIRE", "PYRO")):
            return HazardType.WILDFIRE
        elif dev_upper.startswith(("FLOOD", "FLASH_FLOOD", "HYDRO", "WATER")):
            return HazardType.FLASH_FLOOD
        elif dev_upper.startswith(("LANDSLIDE", "SLOPE", "GEO", "SEISMIC", "STN", "NODE_2", "NODE2")):
            return HazardType.LANDSLIDE

        # Default fallback
        logger.warning("Could not definitively classify device '%s'. Defaulting to WILDFIRE.", device_id)
        return HazardType.WILDFIRE

    async def route_and_process(self, packet: StandardPacket) -> HazardEvent:
        """
        Route packet to its dedicated processing engine and return the evaluated HazardEvent.
        """
        hazard_type = packet.hazard_type or self.identify_hazard_type(packet.device_id)

        if hazard_type == HazardType.LANDSLIDE:
            logger.debug("Routing packet [%s] to Landslide Engine", packet.device_id)
            return await self.landslide_engine.process_packet(packet)

        elif hazard_type == HazardType.FLASH_FLOOD:
            logger.debug("Routing packet [%s] to Flash Flood Engine", packet.device_id)
            return await self.flood_engine.process_packet(packet)

        elif hazard_type == HazardType.WILDFIRE:
            logger.debug("Routing packet [%s] to Wildfire Engine", packet.device_id)
            return await self.wildfire_engine.process_packet(packet)

        else:
            raise ValueError(f"Unsupported hazard type: {hazard_type}")


# Global classifier instance
data_classifier = DataClassifier()
