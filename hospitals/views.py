import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count

from emergencies import models

from .models import Hospital, HospitalRating, HospitalCapacity
from .serializers import (
    HospitalSerializer, HospitalDetailSerializer, HospitalRatingSerializer,
    NearbyHospitalsRequestSerializer, HospitalSearchRequestSerializer,
    EmergencyMatchingRequestSerializer, HospitalAvailabilityResponseSerializer,
    CommunicationRequestSerializer, EmergencyResponseSerializer
)
from .services import DiscoveryService, MatchingService, CommunicationService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def discover_nearby_hospitals(request):
    """
    Discover hospitals near a location
    POST /api/v1/hospitals/nearby
    """
    serializer = NearbyHospitalsRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        hospitals = DiscoveryService.find_nearby_hospitals(
            latitude=data['latitude'],
            longitude=data['longitude'],
            radius_km=data['radius_km'],
            emergency_type=data.get('emergency_type'),
            specialties=data.get('specialties', []),
            hospital_level=data.get('hospital_level'),
            max_results=data['max_results']
        )
        
        return Response(hospitals)
        
    except Exception as e:
        logger.error(f"Nearby hospitals discovery failed: {str(e)}")
        return Response(
            {'error': 'Failed to discover nearby hospitals'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_hospitals(request):
    """
    Search hospitals by name, specialty, or location
    POST /api/v1/hospitals/search
    """
    serializer = HospitalSearchRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        hospitals = DiscoveryService.search_hospitals(
            query=data['query'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            max_results=data['max_results']
        )
        
        return Response(hospitals)
        
    except Exception as e:
        logger.error(f"Hospital search failed: {str(e)}")
        return Response(
            {'error': 'Failed to search hospitals'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_hospital_details(request, hospital_id):
    """
    Get detailed information about a hospital
    GET /api/v1/hospitals/{id}
    """
    try:
        hospital = get_object_or_404(Hospital, id=hospital_id)
        serializer = HospitalDetailSerializer(hospital)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Failed to get hospital details: {str(e)}")
        return Response(
            {'error': 'Failed to get hospital details'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_hospital_availability(request, hospital_id):
    """
    Check real-time hospital availability and capacity
    POST /api/v1/hospitals/{id}/availability
    """
    try:
        availability = DiscoveryService.check_hospital_availability(hospital_id)
        
        if not availability:
            return Response(
                {'error': 'Hospital availability information not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = HospitalAvailabilityResponseSerializer(availability)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Availability check failed: {str(e)}")
        return Response(
            {'error': 'Failed to check hospital availability'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_hospital_capabilities(request, hospital_id):
    """
    Get hospital specialties and capabilities
    GET /api/v1/hospitals/{id}/capabilities
    """
    try:
        hospital = get_object_or_404(Hospital, id=hospital_id)
        
        capabilities = {
            'hospital_id': hospital.id,
            'hospital_name': hospital.name,
            'specialties': [
                {
                    'specialty': spec.specialty,
                    'specialty_display': spec.get_specialty_display(),
                    'capability_level': spec.capability_level,
                    'capability_display': spec.get_capability_level_display(),
                    'is_available': spec.is_available,
                    'notes': spec.notes
                }
                for spec in hospital.specialties.all()
            ],
            'hospital_level': hospital.level,
            'level_display': hospital.get_level_display(),
            'accepts_emergencies': hospital.accepts_emergencies,
            'is_operational': hospital.is_operational
        }
        
        return Response(capabilities)
        
    except Exception as e:
        logger.error(f"Failed to get hospital capabilities: {str(e)}")
        return Response(
            {'error': 'Failed to get hospital capabilities'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def match_hospitals_for_emergency(request):
    """
    Find best hospitals for a specific emergency
    POST /api/v1/hospitals/matching
    """
    serializer = EmergencyMatchingRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        matched_hospitals = MatchingService.find_best_hospitals_for_emergency(
            emergency_lat=data['latitude'],
            emergency_lon=data['longitude'],
            emergency_type=data['emergency_type'],
            required_specialties=data.get('required_specialties', []),
            max_distance_km=data['max_distance_km'],
            max_results=data['max_results']
        )
        
        return Response(matched_hospitals)
        
    except Exception as e:
        logger.error(f"Hospital matching failed: {str(e)}")
        return Response(
            {'error': 'Failed to match hospitals for emergency'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_hospital_alert(request, hospital_id):
    """
    Send emergency notification to hospital
    POST /api/v1/hospitals/{id}/alert
    """
    serializer = CommunicationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        # Verify hospital exists and accepts emergencies
        hospital = get_object_or_404(
            Hospital, 
            id=hospital_id, 
            is_operational=True,
            accepts_emergencies=True
        )
        
        communication_results = CommunicationService.send_emergency_alert_to_hospital(
            hospital_id=hospital_id,
            emergency_data=data['emergency_data'],
            communication_channels=data['communication_channels']
        )
        
        return Response({
            'hospital_id': hospital_id,
            'hospital_name': hospital.name,
            'communication_results': communication_results
        })
        
    except Exception as e:
        logger.error(f"Hospital alert failed: {str(e)}")
        return Response(
            {'error': 'Failed to send hospital alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_communication_status(request, alert_id):
    """
    Get communication status for an emergency alert
    GET /api/v1/hospital/comms/status/{alert_id}
    """
    try:
        status_info = CommunicationService.get_communication_status(alert_id)
        return Response(status_info)
        
    except Exception as e:
        logger.error(f"Failed to get communication status: {str(e)}")
        return Response(
            {'error': 'Failed to get communication status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activate_fallback_communication(request):
    """
    Activate fallback communication channels
    POST /api/v1/hospital/comms/fallback
    """
    try:
        # This would implement fallback communication logic
        # For now, return a mock response
        
        return Response({
            'message': 'Fallback communication activated',
            'channels_activated': ['sms', 'voice_call'],
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Fallback communication failed: {str(e)}")
        return Response(
            {'error': 'Failed to activate fallback communication'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def hospital_ratings(request, hospital_id=None):
    """
    Get or create hospital ratings
    GET /api/v1/hospitals/{id}/ratings - Get hospital ratings
    POST /api/v1/hospitals/{id}/ratings - Create hospital rating
    """
    if request.method == 'GET':
        try:
            if hospital_id:
                ratings = HospitalRating.objects.filter(
                    hospital_id=hospital_id, 
                    is_approved=True
                ).select_related('user').order_by('-created_at')[:50]
            else:
                ratings = HospitalRating.objects.filter(
                    is_approved=True
                ).select_related('user', 'hospital').order_by('-created_at')[:50]
            
            serializer = HospitalRatingSerializer(ratings, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to get hospital ratings: {str(e)}")
            return Response(
                {'error': 'Failed to get hospital ratings'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        if not hospital_id:
            return Response(
                {'error': 'Hospital ID is required for rating'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            hospital = get_object_or_404(Hospital, id=hospital_id)
            
            # Check if user has already rated this hospital
            existing_rating = HospitalRating.objects.filter(
                hospital=hospital,
                user=request.user
            ).first()
            
            if existing_rating:
                return Response(
                    {'error': 'You have already rated this hospital'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = HospitalRatingSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            rating = serializer.save(
                hospital=hospital,
                user=request.user
            )
            
            return Response(
                HospitalRatingSerializer(rating).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Failed to create hospital rating: {str(e)}")
            return Response(
                {'error': 'Failed to create hospital rating'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_hospital_statistics(request, hospital_id):
    """
    Get hospital statistics and performance metrics
    GET /api/v1/hospitals/{id}/statistics
    """
    try:
        hospital = get_object_or_404(Hospital, id=hospital_id)
        
        # Calculate rating statistics
        rating_stats = HospitalRating.objects.filter(
            hospital=hospital,
            is_approved=True
        ).aggregate(
            average_rating=Avg('overall_rating'),
            total_ratings=Count('id'),
            average_emergency_rating=Avg('emergency_care_rating'),
            emergency_ratings_count=Count('id', filter=models.Q(was_emergency=True))
        )
        
        # Calculate response statistics
        response_stats = hospital.emergency_responses.aggregate(
            average_response_time=Avg('response_time'),
            total_responses=Count('id'),
            acceptance_rate=Count('id', filter=models.Q(accepted_patient=True)) / Count('id') * 100
        )
        
        statistics = {
            'hospital_id': hospital.id,
            'hospital_name': hospital.name,
            'ratings': {
                'average_rating': round(rating_stats['average_rating'] or 0, 1),
                'total_ratings': rating_stats['total_ratings'] or 0,
                'average_emergency_rating': round(rating_stats['average_emergency_rating'] or 0, 1),
                'emergency_ratings_count': rating_stats['emergency_ratings_count'] or 0,
            },
            'responses': {
                'average_response_time': round(response_stats['average_response_time'] or 0, 1),
                'total_responses': response_stats['total_responses'] or 0,
                'acceptance_rate': round(response_stats['acceptance_rate'] or 0, 1),
            },
            'capacity': {
                'bed_occupancy_rate': hospital.capacity.bed_occupancy_rate if hasattr(hospital, 'capacity') else 0,
                'emergency_occupancy_rate': hospital.capacity.emergency_occupancy_rate if hasattr(hospital, 'capacity') else 0,
            } if hasattr(hospital, 'capacity') else None
        }
        
        return Response(statistics)
        
    except Exception as e:
        logger.error(f"Failed to get hospital statistics: {str(e)}")
        return Response(
            {'error': 'Failed to get hospital statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fallback_hospitals(request, hospital_id):
    """
    Get fallback hospitals in case primary hospital cannot accept patient
    GET /api/v1/hospitals/{id}/fallbacks
    """
    try:
        primary_hospital = get_object_or_404(Hospital, id=hospital_id)
        
        # Get emergency coordinates from query params
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        
        if not latitude or not longitude:
            return Response(
                {'error': 'Latitude and longitude parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fallback_hospitals = MatchingService.get_fallback_hospitals(
            primary_hospital_id=hospital_id,
            emergency_lat=float(latitude),
            emergency_lon=float(longitude),
            max_results=3
        )
        
        return Response({
            'primary_hospital': {
                'id': primary_hospital.id,
                'name': primary_hospital.name,
            },
            'fallback_hospitals': fallback_hospitals
        })
        
    except Exception as e:
        logger.error(f"Failed to get fallback hospitals: {str(e)}")
        return Response(
            {'error': 'Failed to get fallback hospitals'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )