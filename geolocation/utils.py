import math
import logging
from typing import Tuple, Optional, List, Dict
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GeolocationError(Exception):
    """Base exception for geolocation-related errors"""
    pass


class GeocodingError(GeolocationError):
    """Raised when geocoding fails"""
    pass


class DistanceCalculationError(GeolocationError):
    """Raised when distance calculation fails"""
    pass


class PlacesServiceError(GeolocationError):
    """Raised when Places API service fails"""
    pass


def calculate_distance_haversine(
    lat1: float, 
    lon1: float, 
    lat2: float, 
    lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points on Earth using Haversine formula
    Returns distance in kilometers
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate if coordinates are within reasonable ranges for Kenya
    """
    # Kenya approximate coordinates range
    KENYA_LAT_RANGE = (-4.9, 5.0)  # South to North
    KENYA_LON_RANGE = (33.9, 41.9)  # West to East
    
    return (KENYA_LAT_RANGE[0] <= latitude <= KENYA_LAT_RANGE[1] and 
            KENYA_LON_RANGE[0] <= longitude <= KENYA_LON_RANGE[1])


def format_coordinates(latitude: float, longitude: float) -> str:
    """
    Format coordinates as string for API requests
    """
    return f"{latitude},{longitude}"


def parse_coordinates(coord_string: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinate string into (latitude, longitude) tuple
    """
    try:
        lat_str, lon_str = coord_string.split(',')
        return float(lat_str.strip()), float(lon_str.strip())
    except (ValueError, AttributeError):
        return None


def get_bounding_box(latitude: float, longitude: float, radius_km: float = 10) -> Dict[str, float]:
    """
    Calculate bounding box for a given point and radius
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert latitude and longitude to radians
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    
    # Calculate angular distance in radians
    angular_distance = radius_km / R
    
    # Calculate bounding box
    min_lat = math.degrees(lat_rad - angular_distance)
    max_lat = math.degrees(lat_rad + angular_distance)
    
    # Longitude adjustment for latitude
    delta_lon = math.asin(math.sin(angular_distance) / math.cos(lat_rad))
    min_lon = math.degrees(lon_rad - delta_lon)
    max_lon = math.degrees(lon_rad + delta_lon)
    
    return {
        'min_latitude': min_lat,
        'max_latitude': max_lat,
        'min_longitude': min_lon,
        'max_longitude': max_lon
    }


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing (direction) between two points in degrees
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    
    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    
    initial_bearing = math.atan2(x, y)
    
    # Convert bearing from radians to degrees and normalize
    initial_bearing_deg = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing_deg + 360) % 360
    
    return compass_bearing


def calculate_midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float]:
    """
    Calculate the midpoint between two coordinates
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Calculate midpoint
    Bx = math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad)
    By = math.cos(lat2_rad) * math.sin(lon2_rad - lon1_rad)
    
    mid_lat_rad = math.atan2(
        math.sin(lat1_rad) + math.sin(lat2_rad),
        math.sqrt((math.cos(lat1_rad) + Bx) ** 2 + By ** 2)
    )
    
    mid_lon_rad = lon1_rad + math.atan2(By, math.cos(lat1_rad) + Bx)
    
    # Convert back to degrees
    mid_lat = math.degrees(mid_lat_rad)
    mid_lon = math.degrees(mid_lon_rad)
    
    return mid_lat, mid_lon


def calculate_destination_point(lat: float, lon: float, bearing: float, distance_km: float) -> Tuple[float, float]:
    """
    Calculate destination point given start point, bearing, and distance
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)
    
    # Calculate destination
    dest_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(distance_km / R) +
        math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
    )
    
    dest_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
        math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(dest_lat_rad)
    )
    
    # Convert back to degrees
    dest_lat = math.degrees(dest_lat_rad)
    dest_lon = math.degrees(dest_lon_rad)
    
    return dest_lat, dest_lon


def is_point_in_bounding_box(
    point_lat: float, 
    point_lon: float, 
    min_lat: float, 
    max_lat: float, 
    min_lon: float, 
    max_lon: float
) -> bool:
    """
    Check if a point is within a bounding box
    """
    return (min_lat <= point_lat <= max_lat and 
            min_lon <= point_lon <= max_lon)


def calculate_speed(distance_km: float, time_hours: float) -> float:
    """
    Calculate speed in km/h given distance and time
    """
    if time_hours <= 0:
        return 0.0
    return distance_km / time_hours


def calculate_travel_time(distance_km: float, speed_kmh: float) -> float:
    """
    Calculate travel time in hours given distance and speed
    """
    if speed_kmh <= 0:
        return float('inf')
    return distance_km / speed_kmh


def meters_to_kilometers(meters: float) -> float:
    """Convert meters to kilometers"""
    return meters / 1000.0


def kilometers_to_meters(km: float) -> float:
    """Convert kilometers to meters"""
    return km * 1000.0


def format_distance(meters: float) -> str:
    """
    Format distance in a human-readable way
    """
    if meters < 1000:
        return f"{int(meters)}m"
    else:
        km = meters / 1000.0
        return f"{km:.1f}km"


def format_duration(seconds: float) -> str:
    """
    Format duration in a human-readable way
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{int(minutes)}min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def calculate_area_center(points: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """
    Calculate the center point of multiple coordinates (centroid)
    """
    if not points:
        return None
    
    total_lat = 0.0
    total_lon = 0.0
    count = len(points)
    
    for lat, lon in points:
        total_lat += lat
        total_lon += lon
    
    return total_lat / count, total_lon / count


def is_coordinate_valid(latitude: float, longitude: float) -> bool:
    """
    Comprehensive coordinate validation
    """
    try:
        # Check numeric ranges
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return False
        
        # Check for obviously invalid coordinates
        if latitude == 0 and longitude == 0:
            return False
        
        # Check Kenya-specific bounds
        return validate_coordinates(latitude, longitude)
        
    except (TypeError, ValueError):
        return False


def calculate_route_efficiency(straight_line_distance: float, actual_route_distance: float) -> float:
    """
    Calculate route efficiency as a percentage
    Returns efficiency percentage (0-100)
    """
    if straight_line_distance <= 0 or actual_route_distance <= 0:
        return 0.0
    
    efficiency = (straight_line_distance / actual_route_distance) * 100
    return min(efficiency, 100.0)


def get_cardinal_direction(bearing: float) -> str:
    """
    Convert bearing in degrees to cardinal direction
    """
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(bearing / 45) % 8
    return directions[index]