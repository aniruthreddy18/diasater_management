"""
National Landslide Early Warning Network — High-Vulnerability Stations Registry
Multi-Disaster Early Warning System (SIH Edition)
Geological Survey of India (GSI) & ISRO Landslide Atlas Corroborated Hotspots
"""

from typing import Dict, Any, List, Optional
import copy

LANDSLIDE_STATIONS_DATA: List[Dict[str, Any]] = [
    {
        "id": "STN-NE01",
        "name": "Haflong Slope",
        "district": "Dima Hasao",
        "state": "Assam",
        "region": "North-East (Barail Range)",
        "latitude": 25.1837,
        "longitude": 93.0189,
        "elevation_m": 810,
        "slope_deg": 44,
        "geology": "Weathered Tertiary Shale & Sandstone Regolith",
        "gsi_susceptibility": "VERY HIGH",
        "downhill_assets": "Lumding–Badarpur Hill Railway Line & NH-27 Corridor (Pop at Risk: ~18,500)",
        "safe_assembly": "Upper Haflong High Ground (1.8 km North)",
        "is_active_iot_field_unit": True,
        "device_aliases": ["LANDSLIDE_001", "STN-NE01", "NODE_2"],
        "historical_record": "2022 Monsoon Landslide breached railway bridges and isolated valley for 2 months",
    },
    {
        "id": "STN-WG02",
        "name": "Chooralmala / Meppadi",
        "district": "Wayanad",
        "state": "Kerala",
        "region": "Western Ghats",
        "latitude": 11.5332,
        "longitude": 76.1320,
        "elevation_m": 940,
        "slope_deg": 52,
        "geology": "Precambrian Charnockite & Weathered Laterite Overburden",
        "gsi_susceptibility": "EXTREME",
        "downhill_assets": "Chooralmala Village, Tea Plantation Housing & Iruvazhinji River (Pop at Risk: ~12,200)",
        "safe_assembly": "Meppadi Poly-Clinic Ridge (2.4 km South)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["LANDSLIDE_002", "STN-WG02"],
        "historical_record": "July 2024 Catastrophic Debris Flow triggered by 572mm 48-hr rainfall",
    },
    {
        "id": "STN-HIM03",
        "name": "Sinking Subsidence Corridor",
        "district": "Chamoli (Joshimath)",
        "state": "Uttarakhand",
        "region": "Garhwal Himalayas",
        "latitude": 30.5566,
        "longitude": 79.5664,
        "elevation_m": 1890,
        "slope_deg": 48,
        "geology": "Vaikrita Crystalline Schist & Morainic Glacial Overburden",
        "gsi_susceptibility": "VERY HIGH",
        "downhill_assets": "Badrinath Lifeline Highway NH-07 & Alaknanda River Basin (Pop at Risk: ~21,000)",
        "safe_assembly": "Auli Helipad Safe Plateau (3.2 km Up-slope)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["LANDSLIDE_003", "STN-HIM03"],
        "historical_record": "Active tectonic toe-erosion and subsurface seepage causing structural subsidence",
    },
    {
        "id": "STN-HP04",
        "name": "Sanjauli-Dhalli Ridge",
        "district": "Shimla",
        "state": "Himachal Pradesh",
        "region": "Lesser Himalayas",
        "latitude": 31.1048,
        "longitude": 77.1734,
        "elevation_m": 2205,
        "slope_deg": 46,
        "geology": "Jutogh Metamorphic Phyllite with High Urban Surcharge",
        "gsi_susceptibility": "HIGH",
        "downhill_assets": "Circular Road Bypass, Dhalli Tunnel & Dense Settlements (Pop at Risk: ~35,000)",
        "safe_assembly": "Sanjauli College High Ground (1.1 km)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["LANDSLIDE_004", "STN-HP04"],
        "historical_record": "August 2023 Monsoon Surge triggered multiple slope failures across urban Shimla",
    },
    {
        "id": "STN-SK05",
        "name": "Teesta River Corridor",
        "district": "East Sikkim (Gangtok)",
        "state": "Sikkim",
        "region": "Eastern Himalayas",
        "latitude": 27.3389,
        "longitude": 88.6065,
        "elevation_m": 1650,
        "slope_deg": 50,
        "geology": "Daling Series Chlorite Schist & Granitic Gneiss",
        "gsi_susceptibility": "EXTREME",
        "downhill_assets": "NH-10 National Highway Lifeline to Siliguri & Army Convoy Route",
        "safe_assembly": "Tadong Army Cantonment Plateau (2.8 km)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["LANDSLIDE_005", "STN-SK05"],
        "historical_record": "October 2023 GLOF & Flash Flood undercutting high slopes along Teesta",
    },
    {
        "id": "STN-MZ06",
        "name": "Laipuitlang Slope",
        "district": "Aizawl",
        "state": "Mizoram",
        "region": "Lushai Hills (North-East)",
        "latitude": 23.7271,
        "longitude": 92.7176,
        "elevation_m": 1132,
        "slope_deg": 49,
        "geology": "Surma Group Folded Siltstone & Clay Bedding Planes",
        "gsi_susceptibility": "VERY HIGH",
        "downhill_assets": "Aizawl City Bypass & Ramhlun Residential Sector (Pop at Risk: ~16,000)",
        "safe_assembly": "Zemabawk Ridge Sports Complex (2.0 km)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["LANDSLIDE_006", "STN-MZ06"],
        "historical_record": "Cyclone Remal (May 2024) stone quarry and ridge collapses across Aizawl",
    },
    {
        "id": "STN-WB07",
        "name": "Paglajhora / Kurseong Corridor",
        "district": "Darjeeling",
        "state": "West Bengal",
        "region": "Sub-Himalayan Hill Range",
        "latitude": 26.8815,
        "longitude": 88.2783,
        "elevation_m": 1458,
        "slope_deg": 47,
        "geology": "Darjeeling Gneiss & Golden Phyllite Weathered Regolith",
        "gsi_susceptibility": "VERY HIGH",
        "downhill_assets": "Hill Cart Road (NH-55) & Darjeeling Himalayan Toy Train UNESCO Line",
        "safe_assembly": "Kurseong Tourist Lodge Ridge (1.9 km)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["LANDSLIDE_007", "STN-WB07"],
        "historical_record": "Chronically active subsidence sinking zone on NH-55 since 1998",
    },
]


class LandslideStationManager:
    """Manages high-vulnerability national landslide stations and active hardware bindings."""

    def __init__(self):
        self._stations: Dict[str, Dict[str, Any]] = {
            st["id"]: copy.deepcopy(st) for st in LANDSLIDE_STATIONS_DATA
        }
        self._active_station_id = "STN-NE01"

    def get_all_stations(self) -> List[Dict[str, Any]]:
        """Return list of all registered vulnerable stations with active flag."""
        out = []
        for sid, st in self._stations.items():
            entry = copy.deepcopy(st)
            entry["is_active_iot_field_unit"] = (sid == self._active_station_id)
            out.append(entry)
        return out

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Lookup by station ID or device alias."""
        sid = station_id.upper().strip()
        if sid in self._stations:
            entry = copy.deepcopy(self._stations[sid])
            entry["is_active_iot_field_unit"] = (sid == self._active_station_id)
            return entry

        # Check aliases
        for st in self._stations.values():
            if sid in [a.upper() for a in st.get("device_aliases", [])]:
                entry = copy.deepcopy(st)
                entry["is_active_iot_field_unit"] = (entry["id"] == self._active_station_id)
                return entry
        return None

    def get_active_field_station(self) -> Dict[str, Any]:
        """Return the station currently mapped to the active physical IoT field hardware."""
        st = self._stations.get(self._active_station_id) or self._stations["STN-NE01"]
        entry = copy.deepcopy(st)
        entry["is_active_iot_field_unit"] = True
        return entry

    def set_active_station(self, station_id: str) -> bool:
        """Bind physical hardware to a specific vulnerable station."""
        sid = station_id.upper().strip()
        if sid in self._stations:
            self._active_station_id = sid
            return True
        for st_id, st in self._stations.items():
            if sid in [a.upper() for a in st.get("device_aliases", [])]:
                self._active_station_id = st_id
                return True
        return False


landslide_station_manager = LandslideStationManager()
