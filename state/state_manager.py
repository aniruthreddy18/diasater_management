"""
Simultaneous Multi-Disaster State Management
Multi-Disaster Early Warning System
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.models import (
    HazardType,
    RiskLevel,
    HazardEvent,
    DisasterState,
    MultiDisasterStatus,
)

logger = logging.getLogger(__name__)


class StateManager:
    """
    Thread-safe state manager that maintains independent real-time status
    for all three disaster types simultaneously.
    Guarantees that detection of one disaster never overwrites or clears
    the state of another disaster.
    """

    def __init__(self):
        self._lock = asyncio.Lock()

        # Initialize independent state for each disaster
        self._states: Dict[HazardType, DisasterState] = {
            HazardType.LANDSLIDE: DisasterState(
                hazard_type=HazardType.LANDSLIDE,
                status_label="NORMAL",
                detected=False,
                risk_score=0.0,
                risk_level=RiskLevel.NORMAL,
                message="Slope conditions normal. Monitoring active.",
            ),
            HazardType.FLASH_FLOOD: DisasterState(
                hazard_type=HazardType.FLASH_FLOOD,
                status_label="NORMAL",
                detected=False,
                risk_score=0.0,
                risk_level=RiskLevel.NORMAL,
                message="Waterway levels normal. Monitoring active.",
            ),
            HazardType.WILDFIRE: DisasterState(
                hazard_type=HazardType.WILDFIRE,
                status_label="NORMAL",
                detected=False,
                risk_score=0.0,
                risk_level=RiskLevel.NORMAL,
                message="Thermal and smoke levels normal. Monitoring active.",
            ),
        }

        # Event log history (capped at 100)
        self._event_history: List[HazardEvent] = []

    async def update_hazard_state(self, event: HazardEvent) -> DisasterState:
        """
        Update the state of the specific hazard type corresponding to the incoming event.
        Other hazard states remain completely unchanged.
        """
        async with self._lock:
            ht = event.hazard_type
            prev_state = self._states[ht]

            new_status_label = "DETECTED" if event.detected else "NORMAL"
            now_iso = datetime.now(timezone.utc).isoformat()
            last_det_time = now_iso if event.detected else prev_state.last_detection_time

            updated_state = DisasterState(
                hazard_type=ht,
                device_id=event.device_id,
                detected=event.detected,
                status_label=new_status_label,
                risk_score=event.final_risk_score,
                risk_level=event.risk_level,
                latitude=event.latitude,
                longitude=event.longitude,
                last_updated=now_iso,
                last_detection_time=last_det_time,
                sensor_data=event.sensor_data,
                firms_confirmed=event.firms_confirmed,
                nearest_firms_distance_km=event.nearest_firms_distance_km,
                message=event.message,
            )

            # Store update for ONLY this hazard type
            self._states[ht] = updated_state

            # Append to history
            self._event_history.insert(0, event)
            if len(self._event_history) > 100:
                self._event_history.pop()

            logger.info(
                "State updated for %s: %s (Risk: %.1f%%, %s). Active hazards: %d",
                ht.value, new_status_label, event.final_risk_score, event.risk_level.value,
                sum(1 for s in self._states.values() if s.detected)
            )

            return updated_state

    async def get_multi_disaster_status(self) -> MultiDisasterStatus:
        """
        Get snapshot of all three disaster states simultaneously.
        """
        async with self._lock:
            active_count = sum(1 for s in self._states.values() if s.detected)
            return MultiDisasterStatus(
                landslide=self._states[HazardType.LANDSLIDE].model_copy(),
                flash_flood=self._states[HazardType.FLASH_FLOOD].model_copy(),
                wildfire=self._states[HazardType.WILDFIRE].model_copy(),
                active_hazard_count=active_count,
            )

    async def get_hazard_state(self, hazard_type: HazardType) -> DisasterState:
        """Get state of a single hazard."""
        async with self._lock:
            return self._states[hazard_type].model_copy()

    async def get_recent_events(self, limit: int = 50) -> List[HazardEvent]:
        """Return recent hazard events."""
        async with self._lock:
            return list(self._event_history[:limit])

    async def reset_all_states(self) -> None:
        """Reset all three disaster states to NORMAL."""
        async with self._lock:
            for ht in self._states:
                self._states[ht] = DisasterState(
                    hazard_type=ht,
                    status_label="NORMAL",
                    detected=False,
                    risk_score=0.0,
                    risk_level=RiskLevel.NORMAL,
                    message="Reset to normal monitoring state.",
                )
            logger.info("All disaster states reset to NORMAL.")


# Global state manager instance
state_manager = StateManager()
