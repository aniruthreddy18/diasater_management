"""
NASA FIRMS (Fire Information for Resource Management System) Client
Multi-Disaster Early Warning System
"""

import csv
import io
import logging
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel
import httpx

from config.settings import settings
from .distance import haversine_distance_km

logger = logging.getLogger(__name__)


class FirmsHotspot(BaseModel):
    """Represents a thermal anomaly detected by MODIS/VIIRS satellites."""
    latitude: float
    longitude: float
    brightness: float = 320.0
    confidence: str = "nominal"  # low, nominal, high
    satellite: str = "VIIRS_SNPP_NRT"
    acq_date: str = ""
    acq_time: str = ""
    frp: float = 12.5  # Fire Radiative Power (MW)


class FirmsCheckResult(BaseModel):
    """Result of cross-checking a wildfire detection against NASA FIRMS."""
    confirmed: bool
    nearest_distance_km: Optional[float] = None
    hotspots_count: int = 0
    nearest_hotspot: Optional[Dict[str, Any]] = None
    risk_adjustment: float = 0.0
    status_message: str = ""


class FirmsClient:
    """
    Client for querying NASA FIRMS active fire hotspots and corroborating
    wildfire events detected by the dedicated wildfire hardware.
    """

    def __init__(
        self,
        map_key: Optional[str] = None,
        match_radius_km: Optional[float] = None,
        risk_boost: Optional[float] = None,
    ):
        self.map_key = map_key if map_key is not None else settings.firms.map_key
        self.match_radius_km = (
            match_radius_km if match_radius_km is not None else settings.firms.match_radius_km
        )
        self.risk_boost = (
            risk_boost if risk_boost is not None else settings.firms.risk_boost_percentage_points
        )
        # In-memory simulated/cached hotspots (used for local development, demos, or testing)
        self._simulated_hotspots: List[FirmsHotspot] = [
            # Default mock hotspot near default coordinates (17.3850, 78.4867) ~ 4.2 km away
            FirmsHotspot(
                latitude=17.4100,
                longitude=78.5100,
                brightness=345.2,
                confidence="high",
                satellite="VIIRS_SNPP_NRT",
                acq_date="2026-09-27",
                acq_time="11:00",
                frp=28.4,
            ),
            # Distant hotspot ~ 120 km away
            FirmsHotspot(
                latitude=18.4500,
                longitude=78.9000,
                brightness=312.0,
                confidence="nominal",
                satellite="MODIS",
                acq_date="2026-09-27",
                acq_time="10:30",
                frp=10.1,
            ),
        ]

    def add_simulated_hotspot(self, hotspot: FirmsHotspot) -> None:
        """Inject a simulated hotspot for test scenarios."""
        self._simulated_hotspots.append(hotspot)
        logger.info("Added simulated FIRMS hotspot at (%f, %f)", hotspot.latitude, hotspot.longitude)

    def clear_simulated_hotspots(self) -> None:
        """Clear all simulated hotspots."""
        self._simulated_hotspots.clear()

    async def fetch_live_firms_hotspots(
        self,
        lat: float,
        lon: float,
        bbox_degrees: float = 0.5,
    ) -> List[FirmsHotspot]:
        """
        Query the live NASA FIRMS API for active fire hotspots in a bounding box.
        """
        if not self.map_key:
            logger.debug("NASA FIRMS MAP_KEY not configured. Falling back to local/simulated hotspots.")
            return []

        # Construct bounding box: min_lon, min_lat, max_lon, max_lat
        w = round(lon - bbox_degrees, 4)
        s = round(lat - bbox_degrees, 4)
        e = round(lon + bbox_degrees, 4)
        n = round(lat + bbox_degrees, 4)
        area_coords = f"{w},{s},{e},{n}"

        # Default source: VIIRS_SNPP_NRT, 1 day
        url = f"{settings.firms.api_base_url}/{self.map_key}/VIIRS_SNPP_NRT/{area_coords}/1"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.warning("NASA FIRMS API returned status %d: %s", response.status_code, response.text)
                    return []

                reader = csv.DictReader(io.StringIO(response.text))
                hotspots = []
                for row in reader:
                    try:
                        hotspots.append(
                            FirmsHotspot(
                                latitude=float(row["latitude"]),
                                longitude=float(row["longitude"]),
                                brightness=float(row.get("bright_ti4", row.get("brightness", 300))),
                                confidence=row.get("confidence", "nominal"),
                                satellite=row.get("satellite", "VIIRS"),
                                acq_date=row.get("acq_date", ""),
                                acq_time=row.get("acq_time", ""),
                                frp=float(row.get("frp", 0.0)),
                            )
                        )
                    except (KeyError, ValueError) as err:
                        logger.debug("Failed parsing FIRMS row: %s", err)
                return hotspots

        except Exception as e:
            logger.error("Error communicating with NASA FIRMS API: %s", e)
            return []

    async def cross_check(
        self,
        latitude: float,
        longitude: float,
        custom_radius_km: Optional[float] = None,
    ) -> FirmsCheckResult:
        """
        Cross-check a location against NASA FIRMS active fire hotspots.

        Returns FirmsCheckResult with confirmation flag, nearest distance, and +15% risk bonus if matched.
        """
        radius = custom_radius_km if custom_radius_km is not None else self.match_radius_km

        # 1. Attempt live query if API key is present
        hotspots = await self.fetch_live_firms_hotspots(latitude, longitude)

        # 2. If live query empty or not configured, incorporate simulated/cached hotspots
        if not hotspots and (settings.firms.mock_fallback or not self.map_key):
            hotspots = list(self._simulated_hotspots)

        if not hotspots:
            return FirmsCheckResult(
                confirmed=False,
                nearest_distance_km=None,
                hotspots_count=0,
                nearest_hotspot=None,
                risk_adjustment=0.0,
                status_message="No NASA FIRMS hotspots found in monitoring area.",
            )

        # 3. Find distance to nearest hotspot
        nearest_distance = float("inf")
        nearest_hs: Optional[FirmsHotspot] = None

        for hs in hotspots:
            dist = haversine_distance_km(latitude, longitude, hs.latitude, hs.longitude)
            if dist < nearest_distance:
                nearest_distance = dist
                nearest_hs = hs

        # 4. Check if within configured matching radius
        if nearest_distance <= radius and nearest_hs is not None:
            return FirmsCheckResult(
                confirmed=True,
                nearest_distance_km=nearest_distance,
                hotspots_count=len(hotspots),
                nearest_hotspot=nearest_hs.model_dump(),
                risk_adjustment=self.risk_boost,
                status_message=(
                    f"NASA FIRMS hotspot verified {nearest_distance:.2f} km away "
                    f"(satellite: {nearest_hs.satellite}, brightness: {nearest_hs.brightness}K). "
                    f"+{self.risk_boost}% corroboration applied."
                ),
            )
        else:
            return FirmsCheckResult(
                confirmed=False,
                nearest_distance_km=nearest_distance if nearest_hs else None,
                hotspots_count=len(hotspots),
                nearest_hotspot=nearest_hs.model_dump() if nearest_hs else None,
                risk_adjustment=0.0,
                status_message=(
                    f"Nearest NASA FIRMS hotspot is {nearest_distance:.2f} km away "
                    f"(exceeds {radius:.1f} km matching threshold). No corroboration adjustment."
                ),
            )


# Global singleton client
firms_client = FirmsClient()
