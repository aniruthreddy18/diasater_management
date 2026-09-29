"""
Supabase Cloud Database & Telemetry Persistence Manager
Multi-Disaster Early Warning System — SIH Mission Control
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from config.settings import settings
from core.models import HazardEvent, AlertRecord

logger = logging.getLogger(__name__)


class SupabaseManager:
    """
    Manages cloud database persistence, historical time-series telemetry storage,
    disaster incident audits, and active station sync on Supabase PostgreSQL.
    """

    def __init__(self):
        self.url = settings.supabase.url
        self.key = settings.supabase.key
        self.enabled = settings.supabase.enabled and bool(self.url and self.key)
        self.client = None
        self._connected = False
        self._last_sync_time: Optional[str] = None
        self._packets_logged: int = 0
        self._alerts_logged: int = 0
        self._last_error: Optional[str] = None

        if self.enabled:
            self._init_client()

    def _init_client(self):
        try:
            from supabase import create_client
            self.client = create_client(self.url, self.key)
            self._connected = True
            logger.info("Supabase Cloud Client initialized successfully (%s)", self.url)
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            logger.warning("Supabase Client initialization deferred/failed: %s", e)

    def is_configured(self) -> bool:
        """Check if Supabase credentials are configured and client is active."""
        return bool(self.enabled and self.client and self._connected)

    async def log_telemetry(self, event: HazardEvent) -> bool:
        """
        Persist an evaluated telemetry packet to the cloud `telemetry_logs` table.
        Runs asynchronously in background thread to avoid blocking core telemetry loops.
        """
        if not self.is_configured():
            return False

        try:
            payload = {
                "event_id": event.event_id,
                "device_id": event.device_id,
                "hazard_type": event.hazard_type.value,
                "latitude": float(event.latitude),
                "longitude": float(event.longitude),
                "sensor_data": event.sensor_data or {},
                "base_risk_score": float(event.base_risk_score),
                "final_risk_score": float(event.final_risk_score),
                "risk_level": event.risk_level.value,
                "detected": bool(event.detected),
                "firms_confirmed": bool(event.firms_confirmed) if event.firms_confirmed is not None else False,
                "message": event.message or "",
                "created_at": event.timestamp or datetime.now(timezone.utc).isoformat(),
            }

            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: self.client.table("telemetry_logs").insert(payload).execute()
            )
            self._packets_logged += 1
            self._last_sync_time = datetime.now(timezone.utc).isoformat()
            self._last_error = None
            return True
        except Exception as e:
            # Graceful degradation: do not break local Early Warning System if cloud table not ready
            self._last_error = str(e)
            logger.debug("Supabase telemetry logging note: %s", e)
            return False

    async def log_alert(self, alert: AlertRecord) -> bool:
        """
        Persist a dispatched disaster emergency alert to `disaster_alerts`.
        """
        if not self.is_configured():
            return False

        try:
            payload = {
                "alert_id": alert.alert_id,
                "device_id": alert.device_id,
                "hazard_type": alert.hazard_type.value,
                "risk_level": alert.risk_level.value,
                "risk_score": float(alert.risk_score),
                "latitude": float(alert.latitude),
                "longitude": float(alert.longitude),
                "message": alert.message,
                "channel": alert.channel,
                "delivered": bool(alert.delivered),
                "created_at": alert.timestamp or datetime.now(timezone.utc).isoformat(),
            }

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.table("disaster_alerts").insert(payload).execute()
            )
            self._alerts_logged += 1
            self._last_sync_time = datetime.now(timezone.utc).isoformat()
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.debug("Supabase alert logging note: %s", e)
            return False

    async def sync_active_station(self, category: str, station: Dict[str, Any]) -> bool:
        """
        Sync current active hardware station binding to `active_stations` table.
        """
        if not self.is_configured() or not station:
            return False

        try:
            payload = {
                "category": category.upper(),
                "station_id": station.get("id", "UNKNOWN"),
                "station_name": station.get("name", "Unknown Station"),
                "latitude": float(station.get("latitude", 0.0)),
                "longitude": float(station.get("longitude", 0.0)),
                "details": station,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.table("active_stations").upsert(payload).execute()
            )
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.debug("Supabase station sync note: %s", e)
            return False

    async def get_recent_telemetry(self, limit: int = 50, hazard_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch historical telemetry records from Supabase."""
        if not self.is_configured():
            return []

        try:
            loop = asyncio.get_running_loop()
            query = self.client.table("telemetry_logs").select("*").order("created_at", desc=True).limit(limit)
            if hazard_type:
                query = query.eq("hazard_type", hazard_type.upper())
            res = await loop.run_in_executor(None, lambda: query.execute())
            return res.data if res else []
        except Exception as e:
            logger.debug("Failed to query Supabase telemetry: %s", e)
            return []

    def get_cloud_status(self) -> Dict[str, Any]:
        """Get live health and sync status of the Supabase cloud connection."""
        return {
            "configured": self.is_configured(),
            "provider": "Supabase (PostgreSQL + Realtime)",
            "project_url": self.url,
            "packets_logged": self._packets_logged,
            "alerts_logged": self._alerts_logged,
            "last_sync_time": self._last_sync_time,
            "last_error": self._last_error,
            "status": "CONNECTED" if (self.is_configured() and not self._last_error) else (
                "READY_AWAITING_TABLES" if (self.is_configured() and self._last_error and "schema cache" in self._last_error) else
                ("ERROR" if self._last_error else "OFFLINE")
            ),
        }


# Global singleton instance
supabase_manager = SupabaseManager()
