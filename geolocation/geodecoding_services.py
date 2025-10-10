from typing import Dict, Any, Optional
from google_maps_services import GoogleMapsService
from .models import Location
from django.contrib.gis.geos import Point


class GeocodingService:
    """High-level geocoding service"""
    
    def __init__(self):
        self.google_maps = GoogleMapsService()
    
    def address_to_coordinates(self, address: str, city: str = None, 
                             county: str = None, country: str = 'Kenya') -> Dict[str, Any]:
        """
        Convert full address to coordinates
        """
        full_address = self._build_full_address(address, city, county, country)
        result = self.google_maps.geocode(full_address)
        
        return {
            'latitude': result['geometry']['location']['lat'],
            'longitude': result['geometry']['location']['lng'],
            'formatted_address': result['formatted_address'],
            'address_components': self._parse_address_components(result['address_components'])
        }
    
    def coordinates_to_address(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Convert coordinates to human-readable address
        """
        result = self.google_maps.reverse_geocode(latitude, longitude)
        
        return {
            'address': result['formatted_address'],
            'address_components': self._parse_address_components(result['address_components']),
            'location_type': result['geometry']['location_type']
        }
    
    def create_location_from_coordinates(self, latitude: float, longitude: float, 
                                       user=None, source='gps') -> Location:
        """
        Create a Location model instance from coordinates
        """
        address_data = self.coordinates_to_address(latitude, longitude)
        
        location = Location.objects.create(
            user=user,
            coordinates=Point(longitude, latitude),
            address=address_data['address'],
            city=address_data['address_components'].get('city', ''),
            county=address_data['address_components'].get('county', ''),
            country=address_data['address_components'].get('country', 'Kenya'),
            source=source
        )
        
        return location
    
    def _build_full_address(self, address: str, city: str, county: str, country: str) -> str:
        """Build full address string"""
        parts = [address]
        if city:
            parts.append(city)
        if county:
            parts.append(county)
        if country:
            parts.append(country)
        return ', '.join(parts)
    
    def _parse_address_components(self, components: List[Dict]) -> Dict[str, str]:
        """Parse Google Maps address components"""
        parsed = {}
        
        for component in components:
            component_type = component['types'][0]
            if component_type == 'locality':
                parsed['city'] = component['long_name']
            elif component_type == 'administrative_area_level_1':
                parsed['county'] = component['long_name']
            elif component_type == 'country':
                parsed['country'] = component['long_name']
            elif component_type == 'route':
                parsed['street'] = component['long_name']
            elif component_type == 'street_number':
                parsed['street_number'] = component['long_name']
        
        return parsed