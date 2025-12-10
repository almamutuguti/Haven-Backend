from datetime import timezone
import json
import logging
from rest_framework import generics, status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q


from accounts import serializers
from accounts.permissions import IsSystemAdmin


from .models import Hospital, HospitalRating, HospitalCapacity
from .serializers import (
    HospitalCreateSerializer, HospitalDetailSerializer, HospitalRatingSerializer, HospitalSerializer,
    NearbyHospitalsRequestSerializer, HospitalSearchRequestSerializer,
    EmergencyMatchingRequestSerializer, HospitalAvailabilityResponseSerializer,
    CommunicationRequestSerializer, EmergencyResponseSerializer
)
from .services import DiscoveryService, MatchingService, CommunicationService

logger = logging.getLogger(__name__)


class DiscoverNearbyHospitalsAPIView(APIView):
    """
    Discover hospitals near a location
    POST hospitals/nearby/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
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


class SearchHospitalsAPIView(APIView):
    """
    Search hospitals by name, specialty, or location
    POST hospitals/search/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
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


class HospitalDetailAPIView(APIView):
    """
    Get detailed information about a hospital
    GET hospitals/{id}/
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, hospital_id):
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


class CheckHospitalAvailabilityAPIView(APIView):
    """
    Check real-time hospital availability and capacity
    POST /api/hospitals/{id}/availability/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, hospital_id):
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


class HospitalCapabilitiesAPIView(APIView):
    """
    Get hospital specialties and capabilities
    GET /api/hospitals/{id}/capabilities/
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, hospital_id):
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


class MatchHospitalsForEmergencyAPIView(APIView):
    """
    Find best hospitals for a specific emergency
    POST hospitals/matching/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
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


class SendHospitalAlertAPIView(APIView):
    """
    Send emergency notification to hospital
    POST hospitals/{id}/alert/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, hospital_id):
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


class GetCommunicationStatusAPIView(APIView):
    """
    Get communication status for an emergency alert
    GETh ospitals/comms/status/{alert_id}/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, alert_id):
        try:
            status_info = CommunicationService.get_communication_status(alert_id)
            return Response(status_info)
            
        except Exception as e:
            logger.error(f"Failed to get communication status: {str(e)}")
            return Response(
                {'error': 'Failed to get communication status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActivateFallbackCommunicationAPIView(APIView):
    """
    Activate fallback communication channels
    POST /api/hospitals/comms/fallback/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
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


class HospitalRatingListCreateAPIView(generics.ListCreateAPIView):
    """
    Get or create hospital ratings
    GET /api/hospitals/ratings/ - Get all ratings
    POST /api/hospitals/ratings/ - Create rating (requires hospital_id in data)
    """
    serializer_class = HospitalRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return HospitalRating.objects.filter(is_approved=True).select_related('user', 'hospital')
    
    def perform_create(self, serializer):
        hospital_id = self.request.data.get('hospital_id')
        if not hospital_id:
            raise serializers.ValidationError({'hospital_id': 'This field is required.'})
        
        hospital = get_object_or_404(Hospital, id=hospital_id)
        
        # Check if user has already rated this hospital
        existing_rating = HospitalRating.objects.filter(
            hospital=hospital,
            user=self.request.user
        ).first()
        
        if existing_rating:
            raise serializers.ValidationError({'error': 'You have already rated this hospital'})
        
        serializer.save(hospital=hospital, user=self.request.user)


class HospitalRatingDetailAPIView(generics.ListAPIView):
    """
    Get hospital ratings for a specific hospital
    GET /api/hospitals/{hospital_id}/ratings/
    """
    serializer_class = HospitalRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        hospital_id = self.kwargs['hospital_id']
        return HospitalRating.objects.filter(
            hospital_id=hospital_id, 
            is_approved=True
        ).select_related('user').order_by('-created_at')


class HospitalStatisticsAPIView(APIView):
    """
    Get hospital statistics and performance metrics
    GET /api/hospitals/{id}/statistics/
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, hospital_id):
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
                emergency_ratings_count=Count('id', filter=Q(was_emergency=True))
            )
            
            # Calculate response statistics - avoid division by zero
            response_aggregation = hospital.emergency_responses.aggregate(
                average_response_time=Avg('response_time'),
                total_responses=Count('id'),
                accepted_responses=Count('id', filter=Q(accepted_patient=True))
            )
            
            total_responses = response_aggregation['total_responses'] or 0
            accepted_responses = response_aggregation['accepted_responses'] or 0
            
            # Calculate acceptance rate safely
            if total_responses > 0:
                acceptance_rate = round((accepted_responses / total_responses) * 100, 1)
            else:
                acceptance_rate = 0.0
            
            # Get capacity information safely
            capacity_info = None
            if hasattr(hospital, 'capacity'):
                capacity_info = {
                    'bed_occupancy_rate': hospital.capacity.bed_occupancy_rate or 0,
                    'emergency_occupancy_rate': hospital.capacity.emergency_occupancy_rate or 0,
                    'available_beds': hospital.capacity.available_beds or 0,
                    'available_emergency_beds': hospital.capacity.available_beds or 0,
                }
            
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
                    'average_response_time': round(response_aggregation['average_response_time'] or 0, 1),
                    'total_responses': total_responses,
                    'accepted_responses': accepted_responses,
                    'acceptance_rate': acceptance_rate,
                },
                'capacity': capacity_info
            }
            
            return Response(statistics)
            
        except Exception as e:
            logger.error(f"Failed to get hospital statistics: {str(e)}")
            return Response(
                {'error': 'Failed to get hospital statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class GetFallbackHospitalsAPIView(APIView):
    """
    Get fallback hospitals in case primary hospital cannot accept patient
    GET /api/hospitals/{id}/fallbacks/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, hospital_id):
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
        
class HospitalListCreateAPIView(generics.ListCreateAPIView):
    """List all hospitals or create a new hospital"""
    queryset = Hospital.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.HospitalSerializer
        return HospitalDetailSerializer

    def perform_create(self, serializer):
        # Create location if provided
        location_data = self.request.data.get('location')
        if location_data:
            # You'll need to create location logic here
            pass
        serializer.save()

class HospitalRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a hospital"""
    queryset = Hospital.objects.all()
    serializer_class = serializers.HospitalSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return serializers.HospitalSerializer
        return HospitalDetailSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

class HospitalStatusUpdateAPIView(generics.UpdateAPIView):
    """Update hospital operational status"""
    queryset = Hospital.objects.all()
    serializer_class = serializers.HospitalSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_operational = not instance.is_operational
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    


class HospitalListCreateAPIView(generics.ListCreateAPIView):
    """List active hospitals or create a new hospital"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return HospitalCreateSerializer  # Use create serializer for POST
        return HospitalSerializer
    
    def get_queryset(self):
        # For normal users, only show active hospitals
        # For superusers, show all hospitals (including inactive)
        if self.request.user.is_superuser or self.request.user.role == 'admin' or self.request.user.role == 'system_admin':
            return Hospital.objects.all().order_by('-created_at')
        return Hospital.objects.filter(is_active=True).order_by('-created_at')
    
    def perform_create(self, serializer):
        try:
            hospital = serializer.save()
            if hospital.is_verified and not hospital.verified_at:
                hospital.verified_at = timezone.now()
                hospital.save()
        except Exception as e:
            # Re-raise with proper error message
            raise serializers.ValidationError({
                'non_field_errors': [f'Failed to create hospital: {str(e)}']
            })

class HospitalAllListView(generics.ListAPIView):
    """List ALL hospitals (including inactive) - Superuser only"""
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get_queryset(self):
        return Hospital.objects.all().order_by('-created_at')

class HospitalRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a hospital"""
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return HospitalDetailSerializer
        return HospitalSerializer
    
    def perform_update(self, serializer):
        instance = serializer.save()
        # Update verified_at timestamp if verification status changed
        if 'is_verified' in serializer.validated_data:
            if instance.is_verified and not instance.verified_at:
                instance.verified_at = timezone.now()
            elif not instance.is_verified:
                instance.verified_at = None
            instance.save()
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete - set is_active to False"""
        instance = self.get_object()
        instance.is_active = False
        instance.deactivated_at = timezone.now()
        instance.save()
        return Response({'message': 'Hospital deactivated successfully'}, status=status.HTTP_200_OK)

class HospitalHardDeleteAPIView(generics.DestroyAPIView):
    """Hard delete hospital - Superuser only"""
    queryset = Hospital.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    lookup_field = 'id'
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        hospital_name = instance.name
        instance.delete()
        return Response(
            {'message': f'Hospital "{hospital_name}" permanently deleted'},
            status=status.HTTP_200_OK
        )

class HospitalToggleStatusAPIView(generics.UpdateAPIView):
    """Toggle hospital operational status"""
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    lookup_field = 'id'
    
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_operational = not instance.is_operational
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class HospitalToggleActiveAPIView(generics.UpdateAPIView):
    """Toggle hospital active status (deactivate/reactivate)"""
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    lookup_field = 'id'
    
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        
        if not instance.is_active:
            instance.deactivated_at = timezone.now()
        else:
            instance.deactivated_at = None
            
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class HospitalReactivateAPIView(generics.UpdateAPIView):
    """Reactivate a deactivated hospital - Superuser only"""
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    lookup_field = 'id'
    
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if instance.is_active:
            return Response(
                {'error': 'Hospital is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.is_active = True
        instance.deactivated_at = None
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class HospitalVerifyAPIView(generics.UpdateAPIView):
    """Verify/Unverify a hospital"""
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    lookup_field = 'id'
    
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Toggle verification status
        instance.is_verified = not instance.is_verified
        
        if instance.is_verified and not instance.verified_at:
            instance.verified_at = timezone.now()
        elif not instance.is_verified:
            instance.verified_at = None
            
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class HospitalSearchAPIView(generics.ListAPIView):
    """Search hospitals by name, address, or MFL code"""
    serializer_class = HospitalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return Hospital.objects.filter(is_active=True).order_by('-created_at')
        
        # Search in multiple fields
        return Hospital.objects.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query) |
            Q(mfl_code__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        ).filter(is_active=True).order_by('-created_at')

class HospitalStatisticsAPIView(APIView):
    """Get hospital statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        total = Hospital.objects.count()
        operational = Hospital.objects.filter(is_operational=True).count()
        verified = Hospital.objects.filter(is_verified=True).count()
        active = Hospital.objects.filter(is_active=True).count()
        
        return Response({
            'total': total,
            'operational': operational,
            'verified': verified,
            'active': active,
            'inactive': total - active
        })

class HospitalExportAPIView(APIView):
    """Export all hospital data"""
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        hospitals = Hospital.objects.all().order_by('name')
        
        # Prepare export data
        export_data = []
        for hospital in hospitals:
            hospital_data = {
                'id': hospital.id,
                'name': hospital.name,
                'hospital_type': hospital.hospital_type,
                'level': hospital.level,
                'phone': hospital.phone,
                'emergency_phone': hospital.emergency_phone,
                'email': hospital.email,
                'website': hospital.website,
                'address': hospital.address,
                'latitude': float(hospital.latitude) if hospital.latitude else None,
                'longitude': float(hospital.longitude) if hospital.longitude else None,
                'mfl_code': hospital.mfl_code,
                'is_operational': hospital.is_operational,
                'is_verified': hospital.is_verified,
                'accepts_emergencies': hospital.accepts_emergencies,
                'is_active': hospital.is_active,
                'created_at': hospital.created_at.isoformat() if hospital.created_at else None,
                'updated_at': hospital.updated_at.isoformat() if hospital.updated_at else None,
                'verified_at': hospital.verified_at.isoformat() if hospital.verified_at else None,
                'deactivated_at': hospital.deactivated_at.isoformat() if hospital.deactivated_at else None
            }
            export_data.append(hospital_data)
        
        return Response(export_data)

class HospitalImportAPIView(APIView):
    """Import hospital data"""
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request):
        try:
            data = request.data
            imported_count = 0
            updated_count = 0
            
            if isinstance(data, str):
                data = json.loads(data)
            
            for hospital_data in data:
                # Check if hospital exists by name or MFL code
                existing_hospital = None
                
                if hospital_data.get('mfl_code'):
                    existing_hospital = Hospital.objects.filter(
                        mfl_code=hospital_data['mfl_code']
                    ).first()
                
                if not existing_hospital and hospital_data.get('name'):
                    existing_hospital = Hospital.objects.filter(
                        name__iexact=hospital_data['name']
                    ).first()
                
                if existing_hospital:
                    # Update existing hospital
                    for key, value in hospital_data.items():
                        if hasattr(existing_hospital, key) and key not in ['id', 'created_at']:
                            setattr(existing_hospital, key, value)
                    existing_hospital.save()
                    updated_count += 1
                else:
                    # Create new hospital
                    Hospital.objects.create(**hospital_data)
                    imported_count += 1
            
            return Response({
                'message': 'Import completed successfully',
                'imported': imported_count,
                'updated': updated_count
            })
            
        except Exception as e:
            return Response(
                {'error': f'Import failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )