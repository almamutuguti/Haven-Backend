import requests
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Service for handling Google Maps Geocoding API interactions
    """
    
    @staticmethod
    def geocode_address(address: str) -> Optional[Dict]:
        """
        Convert address to coordinates using Google Geocoding API
        """
        try:
            # Check cache first
            cache_key = f"geocode_{address.lower().replace(' ', '_')}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            params = {
                'address': address,
                'key': settings.GOOGLE_MAPS_API_KEY,
                'region': 'ke'  # Bias results to Kenya
            }
            
            response = requests.get(
                settings.GOOGLE_MAPS_GEOCODING_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK':
                    result = data['results'][0]
                    
                    # Cache successful result for 24 hours
                    cache.set(cache_key, result, 86400)
                    return result
                else:
                    logger.warning(f"Geocoding failed for address {address}: {data['status']}")
                    return None
            else:
                logger.error(f"Geocoding API error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in geocoding: {str(e)}")
            return None
    
    @staticmethod
    def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict]:
        """
        Convert coordinates to address using Google Reverse Geocoding API
        """
        try:
            # Check cache first
            cache_key = f"reverse_geocode_{latitude}_{longitude}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            params = {
                'latlng': f"{latitude},{longitude}",
                'key': settings.GOOGLE_MAPS_API_KEY,
                'result_type': 'street_address|premise'
            }
            
            response = requests.get(
                settings.GOOGLE_MAPS_GEOCODING_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK':
                    result = data['results'][0]
                    
                    # Cache successful result for 24 hours
                    cache.set(cache_key, result, 86400)
                    return result
                else:
                    logger.warning(f"Reverse geocoding failed for {latitude},{longitude}: {data['status']}")
                    return None
            else:
                logger.error(f"Reverse geocoding API error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Reverse geocoding request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in reverse geocoding: {str(e)}")
            return None
    
    @staticmethod
    def extract_address_components(geocoding_result: Dict) -> Dict:
        """
        Extract structured address components from geocoding result
        """
        address_components = {
            'formatted_address': geocoding_result.get('formatted_address', ''),
            'street': '',
            'city': '',
            'county': '',
            'country': '',
            'postal_code': ''
        }
        
        for component in geocoding_result.get('address_components', []):
            types = component.get('types', [])
            
            if 'street_number' in types or 'route' in types:
                address_components['street'] = component.get('long_name', '')
            elif 'locality' in types or 'sublocality' in types:
                address_components['city'] = component.get('long_name', '')
            elif 'administrative_area_level_1' in types:
                address_components['county'] = component.get('long_name', '')
            elif 'country' in types:
                address_components['country'] = component.get('long_name', '')
            elif 'postal_code' in types:
                address_components['postal_code'] = component.get('long_name', '')
        
        return address_components