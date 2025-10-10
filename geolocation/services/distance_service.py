from typing import List, Dict, Any
from geolocation.services.google_maps_services import GoogleMapsService
from geopy.distance import geodesic


class DistanceService:
    """Service for distance and travel time calculations"""
    
    def __init__(self):
        self.google_maps = GoogleMapsService()
    
    def calculate_straight_line_distance(self, point1: Dict, point2: Dict) -> float:
        """
        Calculate straight-line distance between two points in meters
        """
        coord1 = (point1['lat'], point1['lng'])
        coord2 = (point2['lat'], point2['lng'])
        return geodesic(coord1, coord2).meters
    
    def calculate_travel_distance_matrix(self, origins: List[Dict], 
                                      destinations: List[Dict], 
                                      mode: str = 'driving') -> List[List[Dict]]:
        """
        Calculate travel distance and time between multiple points
        """
        result = self.google_maps.get_distance_matrix(origins, destinations, mode)
        
        matrix = []
        for i, origin in enumerate(result['rows']):
            row = []
            for j, element in enumerate(origin['elements']):
                if element['status'] == 'OK':
                    row.append({
                        'distance': element['distance'],
                        'duration': element['duration'],
                        'status': 'OK'
                    })
                else:
                    row.append({
                        'status': element['status'],
                        'distance': None,
                        'duration': None
                    })
            matrix.append(row)
        
        return matrix
    
    def find_nearest_points(self, origin: Dict, points: List[Dict], 
                          max_distance: float = None, max_results: int = 5) -> List[Dict]:
        """
        Find nearest points to origin within specified distance
        """
        distances = []
        
        for point in points:
            distance = self.calculate_straight_line_distance(origin, point)
            
            if max_distance is None or distance <= max_distance:
                distances.append({
                    'point': point,
                    'distance': distance,
                    'distance_km': round(distance / 1000, 2)
                })
        
        # Sort by distance and limit results
        distances.sort(key=lambda x: x['distance'])
        return distances[:max_results]
    
    def calculate_route_eta(self, origin: Dict, destination: Dict, 
                          mode: str = 'driving') -> Dict[str, Any]:
        """
        Calculate ETA and route details between two points
        """
        route = self.google_maps.get_route_directions(origin, destination, mode)
        
        if not route:
            return {
                'status': 'ERROR',
                'message': 'No route found'
            }
        
        leg = route['legs'][0]
        
        return {
            'status': 'OK',
            'distance': leg['distance'],
            'duration': leg['duration'],
            'start_address': leg['start_address'],
            'end_address': leg['end_address'],
            'steps': leg['steps'],
            'polyline': route['overview_polyline']['points']
        }