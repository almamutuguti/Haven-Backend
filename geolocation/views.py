import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

from .models import Location
from .serializers import (
    LocationSerializer, GeocodingRequestSerializer, GeocodingResponseSerializer,
    DistanceRequestSerializer, DistanceResponseSerializer,
    NearbyHospitalsRequestSerializer, HospitalSearchResultSerializer
)
from .services import GeocodingService, DistanceService, PlacesService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def geocode_address(request):
    """
    Convert address to coordinates or coordinates to address
    """
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_distance(request):
    """
    Calculate distance and ETA between two points
    """
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def find_nearby_hospitals(request):
    """
    Find hospitals near a given location
    """
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


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_locations(request, location_id=None):
    """
    Manage user's saved locations
    """
    if request.method == 'GET':
        # Get user's locations
        locations = Location.objects.filter(user=request.user)
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Create new location
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                # If setting as primary, remove primary from other locations
                if serializer.validated_data.get('is_primary'):
                    Location.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
                
                location = serializer.save(user=request.user)
            
            return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'PUT':
        # Update existing location
        if not location_id:
            return Response(
                {'error': 'Location ID is required for update'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            location = Location.objects.get(id=location_id, user=request.user)
        except Location.DoesNotExist:
            return Response(
                {'error': 'Location not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = LocationSerializer(location, data=request.data, partial=True)
        if serializer.is_valid():
            with transaction.atomic():
                # If setting as primary, remove primary from other locations
                if serializer.validated_data.get('is_primary'):
                    Location.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
                
                location = serializer.save()
            
            return Response(LocationSerializer(location).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Delete location
        if not location_id:
            return Response(
                {'error': 'Location ID is required for deletion'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            location = Location.objects.get(id=location_id, user=request.user)
            location.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Location.DoesNotExist:
            return Response(
                {'error': 'Location not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_primary_location(request, location_id):
    """
    Set a location as user's primary location
    """
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