import googlemaps
import logging
from django.conf import settings
from django.core.cache import cache
from typing import List, Dict, Any, Optional
from googlemaps.exceptions import GeocodingError, GoogleMapsServiceError

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Service class for Google Maps API interactions"""
    
    def __init__(self):
        self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        self.cache_timeout = getattr(settings, 'GOOGLE_MAPS_CACHE_TIMEOUT', 3600)  # 1 hour
    
    def geocode(self, address: str, components: Dict = None) -> Dict[str, Any]:
        """
        Convert address to coordinates
        """
        cache_key = f"geocode_{hash(address)}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            result = self.client.geocode(
                address=address,
                components=components,
                region='ke'  #Kenya focus
            )
            
            if result:
                cache.set(cache_key, result[0], self.cache_timeout)
                return result[0]
            else:
                raise GeocodingError("No results found for the given address")
                
        except Exception as e:
            logger.error(f"Geocoding error for address {address}: {str(e)}")
            raise GoogleMapsServiceError(f"Geocoding failed: {str(e)}")
    
    def reverse_geocode(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        Convert coordinates to address
        """
        cache_key = f"reverse_geocode_{lat}_{lng}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            result = self.client.reverse_geocode((lat, lng))
            
            if result:
                cache.set(cache_key, result[0], self.cache_timeout)
                return result[0]
            else:
                raise GeocodingError("No address found for the given coordinates")
                
        except Exception as e:
            logger.error(f"Reverse geocoding error for ({lat}, {lng}): {str(e)}")
            raise GoogleMapsServiceError(f"Reverse geocoding failed: {str(e)}")
    
    def get_distance_matrix(self, origins: List[Dict], destinations: List[Dict], 
                          mode: str = 'driving') -> Dict[str, Any]:
        """
        Calculate distance and time between multiple points
        """
        try:
            # Convert dict points to string format
            origins_str = [f"{point['lat']},{point['lng']}" for point in origins]
            destinations_str = [f"{point['lat']},{point['lng']}" for point in destinations]
            
            result = self.client.distance_matrix(
                origins=origins_str,
                destinations=destinations_str,
                mode=mode,
                region='ke',
                units='metric'
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Distance matrix error: {str(e)}")
            raise GoogleMapsServiceError(f"Distance calculation failed: {str(e)}")
    
    def find_nearby_places(self, location: Dict, radius: int, 
                          place_type: str = None, keyword: str = None) -> List[Dict]:
        """
        Find nearby places using Google Places API
        """
        try:
            result = self.client.places_nearby(
                location=location,
                radius=radius,
                type=place_type,
                keyword=keyword
            )
            
            return result.get('results', [])
            
        except Exception as e:
            logger.error(f"Nearby places search error: {str(e)}")
            raise GoogleMapsServiceError(f"Nearby places search failed: {str(e)}")
    
    def get_route_directions(self, origin: Dict, destination: Dict, 
                           mode: str = 'driving') -> Dict[str, Any]:
        """
        Get detailed route directions
        """
        try:
            origin_str = f"{origin['lat']},{origin['lng']}"
            destination_str = f"{destination['lat']},{destination['lng']}"
            
            result = self.client.directions(
                origin=origin_str,
                destination=destination_str,
                mode=mode,
                alternatives=True,
                region='ke'
            )
            
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Route directions error: {str(e)}")
            raise GoogleMapsServiceError(f"Route calculation failed: {str(e)}")
    
    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a place
        """
        cache_key = f"place_details_{place_id}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            result = self.client.place(place_id)
            
            if result:
                cache.set(cache_key, result, self.cache_timeout)
                return result
            else:
                raise GoogleMapsServiceError("Place not found")
                
        except Exception as e:
            logger.error(f"Place details error for {place_id}: {str(e)}")
            raise GoogleMapsServiceError(f"Place details retrieval failed: {str(e)}")