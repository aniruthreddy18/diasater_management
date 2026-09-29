"""
National Wildfire & Industrial Gas Early Warning Network — High-Vulnerability Stations Registry
Forest Survey of India (FSI) & NASA FIRMS Corroborated Extreme Hazard Corridors
"""

from typing import Dict, Any, List, Optional
import copy

WILDFIRE_STATIONS_DATA: List[Dict[str, Any]] = [
    {
        "id": "STN-WF01",
        "name": "Similipal Biosphere Reserve",
        "district": "Mayurbhanj",
        "state": "Odisha",
        "region": "Eastern Ghats Moist Deciduous Belt",
        "latitude": 21.8600,
        "longitude": 86.3800,
        "biome": "Tropical Moist Deciduous (Shorea robusta)",
        "canopy_fuel": "Dry Sal Leaf Litter & Heavy Combustible Regolith",
        "elevation_m": 560,
        "fsi_hazard_class": "EXTREME",
        "downhill_assets": "Core Tiger Reserve Perimeter, Mankidia & Santhal Hamlets (Pop at Risk: ~19,200)",
        "safe_assembly": "Jashipur Forest Headquarters Emergency Buffer (4.5 km Perimeter)",
        "is_active_iot_field_unit": True,
        "device_aliases": ["FIRE_001", "WILDFIRE_001", "STN-WF01", "NODE_3"],
        "historical_record": "March 2021 Catastrophic Forest Fire raging across 8 ranges for over two weeks",
    },
    {
        "id": "STN-WF02",
        "name": "Bandipur-Nagarahole Tiger Corridor",
        "district": "Chamarajanagar & Mysuru",
        "state": "Karnataka",
        "region": "Nilgiri Biosphere Transition Belt",
        "latitude": 11.6664,
        "longitude": 76.6291,
        "biome": "Dry Deciduous Scrub & Flammable Thicket",
        "canopy_fuel": "Invasive Dry Lantana camara & Teak Undergrowth",
        "elevation_m": 820,
        "fsi_hazard_class": "EXTREME",
        "downhill_assets": "Maddur Wildlife Range, NH-766 Mysore-Ooty Lifeline Highway & Tribal Settlements (Pop at Risk: ~11,500)",
        "safe_assembly": "Gundlupet Agricultural Safe Buffer (5.2 km North)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FIRE_002", "WILDFIRE_002", "STN-WF02"],
        "historical_record": "February 2019 Massive Wildfire gutted over 10,000 acres of prime forest",
    },
    {
        "id": "STN-WF03",
        "name": "Bageshwar-Almora Pine Forest Belt",
        "district": "Almora & Bageshwar",
        "state": "Uttarakhand",
        "region": "Kumaon Lesser Himalayas",
        "latitude": 29.8398,
        "longitude": 79.7714,
        "biome": "Sub-tropical Himalayan Pine Forest",
        "canopy_fuel": "Pinus roxburghii (Chir Pine) Highly Inflammable Resin Needles",
        "elevation_m": 1640,
        "fsi_hazard_class": "VERY HIGH",
        "downhill_assets": "Almora-Pithoragarh Highway Corridor & Hillside Villages (Pop at Risk: ~24,000)",
        "safe_assembly": "Hawalbagh Open Terraces Buffer (2.8 km Valley)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FIRE_003", "WILDFIRE_003", "STN-WF03"],
        "historical_record": "Summer 2024 Persistent forest fire clusters engulfing Kumaon ridges",
    },
    {
        "id": "STN-WF04",
        "name": "Melghat Tiger Reserve & Satpura Range",
        "district": "Amravati",
        "state": "Maharashtra",
        "region": "Satpura Southern Deciduous Belt",
        "latitude": 21.4988,
        "longitude": 77.1688,
        "biome": "Southern Tropical Dry Deciduous Teak",
        "canopy_fuel": "Tectona grandis Dry Shed Canopy & Bamboo Brakes",
        "elevation_m": 710,
        "fsi_hazard_class": "HIGH",
        "downhill_assets": "Korku Tribal Hamlets & Semadoh Tourism Hub (Pop at Risk: ~14,000)",
        "safe_assembly": "Dharni Sub-divisional Ground Complex",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FIRE_004", "WILDFIRE_004", "STN-WF04"],
        "historical_record": "Annual pre-monsoon dry season high-velocity flame leaps across Satpura ridges",
    },
    {
        "id": "STN-WF05",
        "name": "Sariska & Aravalli Dry Scrub Belt",
        "district": "Alwar",
        "state": "Rajasthan",
        "region": "Aravalli Range",
        "latitude": 27.3242,
        "longitude": 76.4389,
        "biome": "Arid Deciduous Scrub (Anogeissus pendula)",
        "canopy_fuel": "Dhok Combustible Biomass & Extreme Summer Ambient Heat (>45°C)",
        "elevation_m": 430,
        "fsi_hazard_class": "HIGH",
        "downhill_assets": "Perimeter Dairy Settlements & Jaipur-Alwar State Highway (Pop at Risk: ~16,500)",
        "safe_assembly": "Tehla Open Sports Ground (3.0 km)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FIRE_005", "WILDFIRE_005", "STN-WF05"],
        "historical_record": "March 2022 Wildfire required Indian Air Force Mi-17V5 Bambi bucket operations",
    },
    {
        "id": "STN-WF06",
        "name": "Visakhapatnam Petrochemical Corridor",
        "district": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "region": "Coastal Industrial & Port Zone",
        "latitude": 17.7285,
        "longitude": 83.2201,
        "biome": "Heavy Chemical & Hydrocarbon Storage Sector",
        "canopy_fuel": "Volatile Organic Compounds (VOCs), Styrene Monomer & CO/Gas Flare Leakage",
        "elevation_m": 18,
        "fsi_hazard_class": "CRITICAL GAS HAZARD",
        "downhill_assets": "RR Venkatapuram, Gopalapatnam Residential Wards & Port Highway (Pop at Risk: ~65,000)",
        "safe_assembly": "Simhachalam Hill High Ground Emergency Shelter (4.0 km Upwind)",
        "is_active_iot_field_unit": False,
        "device_aliases": ["FIRE_006", "WILDFIRE_006", "STN-WF06"],
        "historical_record": "May 2020 Polymer Gas Leak disaster affecting over 1,000 residents in surrounding perimeter",
    },
]


class WildfireStationManager:
    """Manages high-vulnerability national wildfire and chemical gas monitoring stations."""

    def __init__(self):
        self._stations: Dict[str, Dict[str, Any]] = {
            st["id"]: copy.deepcopy(st) for st in WILDFIRE_STATIONS_DATA
        }
        self._active_station_id = "STN-WF01"

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
        st = self._stations.get(self._active_station_id) or self._stations["STN-WF01"]
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


wildfire_station_manager = WildfireStationManager()
