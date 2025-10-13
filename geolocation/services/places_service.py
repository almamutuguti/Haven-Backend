import requests
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class PlacesService:
    """
    Service for handling Google Places API interactions
    """
    
    @staticmethod
    def find_nearby_hospitals(
        latitude: float, 
        longitude: float, 
        radius: int = 5000,  # 5km default radius
        keyword: str = 'hospital'
    ) -> Optional[List[Dict]]:
        """
        Find nearby hospitals using Google Places API
        """
        try:
            cache_key = f"nearby_hospitals_{latitude}_{longitude}_{radius}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            params = {
                'location': f"{latitude},{longitude}",
                'radius': radius,
                'type': 'hospital',
                'keyword': keyword,
                'key': settings.GOOGLE_MAPS_API_KEY
            }
            
            response = requests.get(
                settings.GOOGLE_MAPS_NEARBY_SEARCH_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK':
                    hospitals = []
                    
                    for place in data['results']:
                        hospital_data = {
                            'place_id': place.get('place_id'),
                            'name': place.get('name'),
                            'latitude': place['geometry']['location']['lat'],
                            'longitude': place['geometry']['location']['lng'],
                            'address': place.get('vicinity', ''),
                            'rating': place.get('rating'),
                            'user_ratings_total': place.get('user_ratings_total', 0),
                            'types': place.get('types', []),
                            'business_status': place.get('business_status'),
                            'permanently_closed': place.get('permanently_closed', False)
                        }
                        hospitals.append(hospital_data)
                    
                    # Cache for 1 hour (hospital data doesn't change frequently)
                    cache.set(cache_key, hospitals, 3600)
                    return hospitals
                else:
                    logger.warning(f"Nearby hospitals search failed: {data['status']}")
                    return None
            else:
                logger.error(f"Places API error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Places API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in places search: {str(e)}")
            return None
    
    @staticmethod
    def get_place_details(place_id: str) -> Optional[Dict]:
        """
        Get detailed information about a place
        """
        try:
            cache_key = f"place_details_{place_id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            url = 'https://maps.googleapis.com/maps/api/place/details/json'
            params = {
                'place_id': place_id,
                'fields': 'name,formatted_address,geometry,rating,user_ratings_total,formatted_phone,website,opening_hours,types',
                'key': settings.GOOGLE_MAPS_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK':
                    result = data['result']
                    
                    # Cache for 24 hours
                    cache.set(cache_key, result, 86400)
                    return result
                else:
                    logger.warning(f"Place details failed for {place_id}: {data['status']}")
                    return None
            else:
                logger.error(f"Place details API error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Place details request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in place details: {str(e)}")
            return None