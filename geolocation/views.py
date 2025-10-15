import logging
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404

from geolocation.services.distance_service import DistanceService
from geolocation.services.geocoding_services import GeocodingService
from geolocation.services.places_service import PlacesService

from .models import Location
from .serializers import (
    LocationSerializer, GeocodingRequestSerializer, GeocodingResponseSerializer,
    DistanceRequestSerializer, DistanceResponseSerializer,
    NearbyHospitalsRequestSerializer, HospitalSearchResultSerializer
)

logger = logging.getLogger(__name__)


class GeocodeAddressAPIView(APIView):
    """
    Convert address to coordinates or coordinates to address
    POST geolocation/geocode/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = GeocodingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            if data.get('address'):
                # Forward geocoding: address to coordinates
                result = GeocodingService.geocode_address(data['address'])
                if not result:
                    return Response(
                        {'error': 'Could not geocode the provided address'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                address_components = GeocodingService.extract_address_components(result)
                geometry = result['geometry']['location']
                
                response_data = {
                    'latitude': geometry['lat'],
                    'longitude': geometry['lng'],
                    **address_components
                }
                
            else:
                # Reverse geocoding: coordinates to address
                result = GeocodingService.reverse_geocode(data['latitude'], data['longitude'])
                if not result:
                    return Response(
                        {'error': 'Could not reverse geocode the provided coordinates'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                address_components = GeocodingService.extract_address_components(result)
                
                response_data = {
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    **address_components
                }
            
            response_serializer = GeocodingResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(response_serializer.validated_data)
            else:
                return Response(
                    response_serializer.errors, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
            return Response(
                {'error': 'Internal server error during geocoding'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CalculateDistanceAPIView(APIView):
    """
    Calculate distance and ETA between two points
    POST geolocation/distance/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = DistanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            result = DistanceService.get_eta_and_distance(
                data['origin_latitude'],
                data['origin_longitude'],
                data['destination_latitude'],
                data['destination_longitude'],
                data['mode']
            )
            
            if not result:
                return Response(
                    {'error': 'Could not calculate distance between the provided points'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            response_serializer = DistanceResponseSerializer(result)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Distance calculation error: {str(e)}")
            return Response(
                {'error': 'Internal server error during distance calculation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FindNearbyHospitalsAPIView(APIView):
    """
    Find hospitals near a given location
    POST /api/geolocation/hospitals/nearby/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = NearbyHospitalsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            hospitals = PlacesService.find_nearby_hospitals(
                data['latitude'],
                data['longitude'],
                data['radius'],
                data.get('keyword', 'hospital')
            )
            
            if hospitals is None:
                return Response(
                    {'error': 'Could not find nearby hospitals'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            response_serializer = HospitalSearchResultSerializer(hospitals, many=True)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Nearby hospitals search error: {str(e)}")
            return Response(
                {'error': 'Internal server error during hospital search'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LocationListCreateAPIView(generics.ListCreateAPIView):
    """
    Get user's saved locations or create new location
    GET /api/geolocation/locations/ - List locations
    POST /api/geolocation/locations/ - Create location
    """
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Location.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        with transaction.atomic():
            # If setting as primary, remove primary from other locations
            if serializer.validated_data.get('is_primary'):
                Location.objects.filter(user=self.request.user, is_primary=True).update(is_primary=False)
            
            serializer.save(user=self.request.user)


class LocationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a location
    GET /api/geolocation/locations/{id}/ - Get location
    PUT /api/geolocation/locations/{id}/ - Update location
    DELETE /api/geolocation/locations/{id}/ - Delete location
    """
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Location.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        with transaction.atomic():
            # If setting as primary, remove primary from other locations
            if serializer.validated_data.get('is_primary'):
                Location.objects.filter(user=self.request.user, is_primary=True).update(is_primary=False)
            
            serializer.save()


class SetPrimaryLocationAPIView(APIView):
    """
    Set a location as user's primary location
    POST /api/geolocation/locations/{location_id}/primary/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, location_id):
        try:
            with transaction.atomic():
                # Remove primary from all user locations
                Location.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
                
                # Set new primary
                location = Location.objects.get(id=location_id, user=request.user)
                location.is_primary = True
                location.save()
            
            return Response({'message': 'Primary location updated successfully'})
            
        except Location.DoesNotExist:
            return Response(
                {'error': 'Location not found'},
                status=status.HTTP_404_NOT_FOUND
            )