import requests
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class DistanceService:
    """
    Service for handling Google Maps Distance Matrix API interactions
    """
    
    @staticmethod
    def calculate_distance_matrix(
        origins: List[Tuple[float, float]], 
        destinations: List[Tuple[float, float]],
        mode: str = 'driving'
    ) -> Optional[Dict]:
        """
        Calculate distance and time between multiple origins and destinations
        """
        try:
            # Create cache key
            origins_str = '|'.join([f"{lat},{lng}" for lat, lng in origins])
            destinations_str = '|'.join([f"{lat},{lng}" for lat, lng in destinations])
            cache_key = f"distance_matrix_{origins_str}_{destinations_str}_{mode}"
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Prepare origins and destinations strings
            origins_str = '|'.join([f"{lat},{lng}" for lat, lng in origins])
            destinations_str = '|'.join([f"{lat},{lng}" for lat, lng in destinations])
            
            params = {
                'origins': origins_str,
                'destinations': destinations_str,
                'mode': mode,
                'key': settings.GOOGLE_MAPS_API_KEY,
                'departure_time': 'now'  # Real-time traffic consideration
            }
            
            response = requests.get(
                settings.GOOGLE_MAPS_DISTANCE_MATRIX_URL,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK':
                    # Cache successful result for 5 minutes (traffic data changes frequently)
                    cache.set(cache_key, data, 300)
                    return data
                else:
                    logger.warning(f"Distance matrix failed: {data['status']}")
                    return None
            else:
                logger.error(f"Distance matrix API error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Distance matrix request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in distance matrix: {str(e)}")
            return None
    
    @staticmethod
    def get_eta_and_distance(
        origin_lat: float, 
        origin_lng: float, 
        dest_lat: float, 
        dest_lng: float,
        mode: str = 'driving'
    ) -> Optional[Dict]:
        """
        Get ETA and distance between two points
        Returns: { 'distance_meters': int, 'distance_text': str, 'duration_seconds': int, 'duration_text': str }
        """
        result = DistanceService.calculate_distance_matrix(
            [(origin_lat, origin_lng)],
            [(dest_lat, dest_lng)],
            mode
        )
        
        if result and result['rows']:
            element = result['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                return {
                    'distance_meters': element['distance']['value'],
                    'distance_text': element['distance']['text'],
                    'duration_seconds': element['duration']['value'],
                    'duration_text': element['duration']['text']
                }
        
        return None
    
    @staticmethod
    def find_nearest_location(
        origin_lat: float,
        origin_lng: float,
        destinations: List[Tuple[float, float, any]],  # (lat, lng, identifier)
        mode: str = 'driving'
    ) -> Optional[Tuple[any, Dict]]:
        """
        Find the nearest destination from origin with ETA and distance
        Returns: (identifier, distance_info)
        """
        if not destinations:
            return None
            
        origins = [(origin_lat, origin_lng)]
        dest_coords = [(lat, lng) for lat, lng, _ in destinations]
        
        result = DistanceService.calculate_distance_matrix(origins, dest_coords, mode)
        
        if not result or not result['rows']:
            return None
            
        elements = result['rows'][0]['elements']
        nearest_index = None
        min_duration = float('inf')
        
        for i, element in enumerate(elements):
            if element['status'] == 'OK' and element['duration']['value'] < min_duration:
                min_duration = element['duration']['value']
                nearest_index = i
        
        if nearest_index is not None:
            nearest_identifier = destinations[nearest_index][2]
            distance_info = {
                'distance_meters': elements[nearest_index]['distance']['value'],
                'distance_text': elements[nearest_index]['distance']['text'],
                'duration_seconds': elements[nearest_index]['duration']['value'],
                'duration_text': elements[nearest_index]['duration']['text']
            }
            return (nearest_identifier, distance_info)
        
        return None