"""
National Flash Flood & River Basin Early Warning Network — High-Vulnerability Stations Registry
Central Water Commission (CWC) & NDMA High-Risk Corridors
"""

from typing import Dict, Any, List, Optional
import copy

FLOOD_STATIONS_DATA: List[Dict[str, Any]] = [
    {
        "id": "STN-FL01",
        "name": "Brahmaputra Basin (Majuli / Kaziranga)",
        "district": "Majuli & Golaghat",
        "state": "Assam",
        "region": "Upper Brahmaputra Valley (North-East)",
        "latitude": 26.9538,
        "longitude": 94.2037,
        "waterway": "Brahmaputra Main River Channel",
        "elevation_m": 84,
        "catchment_sqkm": 580000,
        "danger_level_m": 86.0,
        "cwc_index": "EXTREME",
        "downhill_assets": "Majuli River Island Settlements, Kaziranga Buffer & NH-715 Highway (Pop at Risk: ~168,000)",
        "safe_assembly": "Jorhat Elevated Relief Bund (Sector 2 North)",
        "is_active_iot_field_unit": True,
        "device_aliases": ["FLOOD_001", "STN-FL01", "NODE_1"],
        "historical_record": "Annual heavy monsoon cloudburst inundation with multi-meter flood surges",
    },
    {
        "id": "STN-FL02",
        "name": "Alaknanda-Mandakini Confluence",
        "district": "Rudraprayag",
        "state": "Uttarakhand",
        "region": "Garhwal Himalayas",
        "latitude": 30.2844,
        "longitude": 78.9811,
        "waterway": "Alaknanda & Mandakini River Confluence",
        "elevation_m": 610,
        "catchment_sqkm": 11000,
        "danger_level_m": 625.0,
        "cwc_index": "EXTREME",
        "downhill_assets": "Char Dham Pilgrimage Lifeline NH-107, Confluence Ghats & Bazaars (Pop at Risk: ~32,000)",
        "safe_assembly": "Belni High Ridge Stadium (1.5 km Elevated)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FLOOD_002", "STN-FL02"],
        "historical_record": "June 2013 Kedarnath Flash Surge and glacial lake breach along Mandakini",
    },
    {
        "id": "STN-FL03",
        "name": "Teesta River Gorge (Chungthang / Mangan)",
        "district": "North Sikkim",
        "state": "Sikkim",
        "region": "Eastern Himalayas",
        "latitude": 27.6042,
        "longitude": 88.6472,
        "waterway": "Teesta Hydroelectric Surge Channel",
        "elevation_m": 1540,
        "catchment_sqkm": 4200,
        "danger_level_m": 1545.0,
        "cwc_index": "EXTREME",
        "downhill_assets": "NH-10 Lifeline Highway to Gangtok & Indo-Tibetan Border Road (Pop at Risk: ~14,000)",
        "safe_assembly": "Mangan Administrative High Plateau (2.2 km South)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FLOOD_003", "STN-FL03"],
        "historical_record": "October 2023 South Lhonak Glacial Lake Outburst Flood (GLOF) surge",
    },
    {
        "id": "STN-FL04",
        "name": "Yamuna Floodplain (Old Railway Bridge)",
        "district": "Central & East Delhi",
        "state": "NCT of Delhi",
        "region": "Gangetic Floodplain",
        "latitude": 28.6633,
        "longitude": 77.2384,
        "waterway": "Yamuna River Lower Stretch",
        "elevation_m": 206,
        "catchment_sqkm": 366000,
        "danger_level_m": 205.33,
        "cwc_index": "VERY HIGH",
        "downhill_assets": "Monastery Market, Yamuna Bazaar, Ring Road Arterial Highway (Pop at Risk: ~45,000)",
        "safe_assembly": "Civil Lines Elevated Government Relief Camps",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FLOOD_004", "STN-FL04"],
        "historical_record": "July 2023 208.66m Record Inundation overflowing Hathnikund Barrage",
    },
    {
        "id": "STN-FL05",
        "name": "Periyar River Basin (Aluva / Kalady)",
        "district": "Ernakulam",
        "state": "Kerala",
        "region": "Western Ghats Coastal Plain",
        "latitude": 10.1076,
        "longitude": 76.3516,
        "waterway": "Periyar River (Cheruthoni Dam release discharge corridor)",
        "elevation_m": 12,
        "catchment_sqkm": 5398,
        "danger_level_m": 14.5,
        "cwc_index": "VERY HIGH",
        "downhill_assets": "Aluva Shiva Temple, Kochi International Airport (COK) Periphery (Pop at Risk: ~85,000)",
        "safe_assembly": "Kakkanad High Plateau Collectorate Camp",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FLOOD_005", "STN-FL05"],
        "historical_record": "August 2018 Great Kerala Floods inundated Kochi airport runway",
    },
    {
        "id": "STN-FL06",
        "name": "Ghaggar-Tangri Basin (Patiala / Ambala)",
        "district": "Ambala & Patiala",
        "state": "Haryana / Punjab",
        "region": "Northern Plains",
        "latitude": 30.3398,
        "longitude": 76.3869,
        "waterway": "Ghaggar & Tangri River Confluence",
        "elevation_m": 252,
        "catchment_sqkm": 42000,
        "danger_level_m": 254.0,
        "cwc_index": "HIGH",
        "downhill_assets": "Ambala-Patiala GT Road Corridor & Rural Agricultural Settlements (Pop at Risk: ~28,000)",
        "safe_assembly": "Rajpura Elevated Grain Terminal Complex",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FLOOD_006", "STN-FL06"],
        "historical_record": "July 2023 Embankment breach submerged major residential colonies",
    },
]


class FloodStationManager:
    """Manages high-vulnerability national flash flood river stations."""

    def __init__(self):
        self._stations: Dict[str, Dict[str, Any]] = {
            st["id"]: copy.deepcopy(st) for st in FLOOD_STATIONS_DATA
        }
        self._active_station_id = "STN-FL01"

    def get_all_stations(self) -> List[Dict[str, Any]]:
        out = []
        for sid, st in self._stations.items():
            entry = copy.deepcopy(st)
            entry["is_active_iot_field_unit"] = (sid == self._active_station_id)
            out.append(entry)
        return out

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        sid = station_id.upper().strip()
        if sid in self._stations:
            entry = copy.deepcopy(self._stations[sid])
            entry["is_active_iot_field_unit"] = (sid == self._active_station_id)
            return entry

        for st in self._stations.values():
            if sid in [a.upper() for a in st.get("device_aliases", [])]:
                entry = copy.deepcopy(st)
                entry["is_active_iot_field_unit"] = (entry["id"] == self._active_station_id)
                return entry
        return None

    def get_active_field_station(self) -> Dict[str, Any]:
        st = self._stations.get(self._active_station_id) or self._stations["STN-FL01"]
        entry = copy.deepcopy(st)
        entry["is_active_iot_field_unit"] = True
        return entry

    def set_active_station(self, station_id: str) -> bool:
        sid = station_id.upper().strip()
        if sid in self._stations:
            self._active_station_id = sid
            return True
        for st_id, st in self._stations.items():
            if sid in [a.upper() for a in st.get("device_aliases", [])]:
                self._active_station_id = st_id
                return True
        return False


flood_station_manager = FloodStationManager()
