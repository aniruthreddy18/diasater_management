"""
Geographic Distance Calculations using Haversine Formula
Multi-Disaster Early Warning System
"""

import math


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in kilometers.

    :param lat1: Latitude of point 1 in decimal degrees
    :param lon1: Longitude of point 1 in decimal degrees
    :param lat2: Latitude of point 2 in decimal degrees
    :param lon2: Longitude of point 2 in decimal degrees
    :return: Distance in kilometers
    """
    # Earth's mean radius in kilometers
    R = 6371.0088

    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(R * c, 3)
