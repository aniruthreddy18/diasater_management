"""
Base Hazard Processing Engine Interface
Multi-Disaster Early Warning System
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from core.models import StandardPacket, HazardEvent, HazardType


class BaseHazardEngine(ABC):
    """
    Abstract interface for independent disaster processing engines.
    Each engine encapsulates the domain logic for analyzing raw telemetry
    from its respective dedicated hardware system.
    """

    def __init__(self, hazard_type: HazardType):
        self.hazard_type = hazard_type

    @abstractmethod
    async def process_packet(self, packet: StandardPacket) -> HazardEvent:
        """
        Process a normalized telemetry packet from the dedicated hardware system,
        perform domain-specific detection & risk calculations, and return a HazardEvent.
        """
        pass
