from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point

from .models import Location, GeoFence
from .serializers import (
    LocationSerializer, GeoFenceSerializer, ReverseGeocodeSerializer,
    GeocodeSerializer, DistanceMatrixSerializer, NearbySearchSerializer
)
from .services import GeocodingService, DistanceService, GoogleMapsService

# 
class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user locations
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def current(self, request):
        """
        Save current user location
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create location with current user
        location = serializer.save(user=request.user)
        
        return Response(
            LocationSerializer(location).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Get user's location history
        """
        locations = self.get_queryset()
        page = self.paginate_queryset(locations)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)


class GeocodingViewSet(viewsets.ViewSet):
    """
    ViewSet for geocoding operations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def geocode(self, request):
        """
        Convert address to coordinates
        """
        serializer = GeocodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        geocoding_service = GeocodingService()
        
        try:
            result = geocoding_service.address_to_coordinates(
                address=serializer.validated_data['address'],
                city=serializer.validated_data.get('city'),
                county=serializer.validated_data.get('county'),
                country=serializer.validated_data.get('country', 'Kenya')
            )
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def reverse_geocode(self, request):
        """
        Convert coordinates to address
        """
        serializer = ReverseGeocodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        geocoding_service = GeocodingService()
        
        try:
            result = geocoding_service.coordinates_to_address(
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude']
            )
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DistanceViewSet(viewsets.ViewSet):
    """
    ViewSet for distance calculations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def matrix(self, request):
        """
        Calculate distance matrix between multiple points
        """
        serializer = DistanceMatrixSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        distance_service = DistanceService()
        
        try:
            result = distance_service.calculate_travel_distance_matrix(
                origins=serializer.validated_data['origins'],
                destinations=serializer.validated_data['destinations'],
                mode=serializer.validated_data.get('mode', 'driving')
            )
            
            return Response({'matrix': result})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def eta(self, request):
        """
        Calculate ETA between two points
        """
        origin = request.data.get('origin')
        destination = request.data.get('destination')
        mode = request.data.get('mode', 'driving')
        
        if not origin or not destination:
            return Response(
                {'error': 'Origin and destination are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        distance_service = DistanceService()
        
        try:
            result = distance_service.calculate_route_eta(origin, destination, mode)
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class NearbyViewSet(viewsets.ViewSet):
    """
    ViewSet for nearby place searches
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Search for nearby places
        """
        serializer = NearbySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        google_maps_service = GoogleMapsService()
        
        try:
            results = google_maps_service.find_nearby_places(
                location={
                    'lat': serializer.validated_data['latitude'],
                    'lng': serializer.validated_data['longitude']
                },
                radius=serializer.validated_data['radius'],
                place_type=serializer.validated_data.get('type'),
                keyword=serializer.validated_data.get('keyword')
            )
            
            return Response({'results': results})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def hospitals(self, request):
        """
        Find nearby hospitals (specialized endpoint)
        """
        serializer = NearbySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        google_maps_service = GoogleMapsService()
        
        try:
            results = google_maps_service.find_nearby_places(
                location={
                    'lat': serializer.validated_data['latitude'],
                    'lng': serializer.validated_data['longitude']
                },
                radius=serializer.validated_data['radius'],
                place_type='hospital',
                keyword=serializer.validated_data.get('keyword')
            )
            
            # Filter and enhance hospital data
            enhanced_results = self._enhance_hospital_data(results)
            
            return Response({'hospitals': enhanced_results})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _enhance_hospital_data(self, hospitals):
        """Enhance hospital data with additional information"""
        enhanced = []
        
        for hospital in hospitals:
            enhanced_hospital = {
                'place_id': hospital.get('place_id'),
                'name': hospital.get('name'),
                'address': hospital.get('vicinity'),
                'location': hospital.get('geometry', {}).get('location'),
                'rating': hospital.get('rating'),
                'user_ratings_total': hospital.get('user_ratings_total'),
                'types': hospital.get('types', []),
                'open_now': hospital.get('opening_hours', {}).get('open_now', False)
            }
            enhanced.append(enhanced_hospital)
        
        return enhanced