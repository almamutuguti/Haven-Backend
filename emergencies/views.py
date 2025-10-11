import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import EmergencyAlert, EmergencyUpdate
from .serializers import (
    EmergencyAlertSerializer, EmergencyAlertCreateSerializer,
    LocationUpdateSerializer, AlertStatusSerializer,
    EmergencyUpdateSerializer, VerificationCodeSerializer,
    CancelEmergencySerializer
)
from .services import AlertService, EmergencyOrchestrator, VerificationService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_emergency_alert(request):
    """
    Trigger a new emergency alert
    POST /api/v1/emergency/alert
    """
    serializer = EmergencyAlertCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        # Create emergency alert
        alert = AlertService.create_emergency_alert(
            user=request.user,
            emergency_type=data['emergency_type'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            description=data.get('description', ''),
            address=data.get('address', ''),
            location_id=data.get('location_id')
        )
        
        if not alert:
            return Response(
                {'error': 'Failed to create emergency alert'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Process the emergency asynchronously (in production, use Celery)
        EmergencyOrchestrator.process_emergency_alert(alert.alert_id)
        
        # Return alert data
        alert_serializer = EmergencyAlertSerializer(alert)
        return Response(alert_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Emergency alert trigger failed: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_alert_status(request, alert_id):
    """
    Get emergency alert status
    GET /api/v1/emergency/{alert_id}/status
    """
    try:
        alert = get_object_or_404(EmergencyAlert, alert_id=alert_id, user=request.user)
        serializer = EmergencyAlertSerializer(alert)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Failed to get alert status: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_alert_location(request, alert_id):
    """
    Update emergency alert location
    PUT /api/v1/emergency/{alert_id}/location
    """
    serializer = LocationUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        success = AlertService.update_alert_location(
            alert_id=alert_id,
            latitude=data['latitude'],
            longitude=data['longitude'],
            address=data.get('address', '')
        )
        
        if not success:
            return Response(
                {'error': 'Failed to update alert location'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': 'Location updated successfully'})
        
    except Exception as e:
        logger.error(f"Location update failed: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_emergency_alert(request, alert_id):
    """
    Cancel emergency alert
    POST /api/v1/emergency/{alert_id}/cancel
    """
    serializer = CancelEmergencySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        success = AlertService.cancel_emergency_alert(
            alert_id=alert_id,
            user=request.user,
            reason=data.get('reason', '')
        )
        
        if not success:
            return Response(
                {'error': 'Failed to cancel emergency alert'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': 'Emergency alert cancelled successfully'})
        
    except Exception as e:
        logger.error(f"Emergency cancellation failed: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emergency_history(request):
    """
    Get user's emergency history
    GET /api/v1/emergency/history
    """
    try:
        limit = int(request.GET.get('limit', 50))
        alerts = AlertService.get_user_emergency_history(request.user, limit)
        
        serializer = EmergencyAlertSerializer(alerts, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Failed to get emergency history: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emergency_updates(request, alert_id):
    """
    Get updates for a specific emergency alert
    """
    try:
        alert = get_object_or_404(EmergencyAlert, alert_id=alert_id, user=request.user)
        updates = EmergencyUpdate.objects.filter(alert=alert).order_by('-created_at')
        
        serializer = EmergencyUpdateSerializer(updates, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Failed to get emergency updates: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_emergency_alert(request, alert_id):
    """
    Verify emergency alert with code
    """
    serializer = VerificationCodeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        data = serializer.validated_data
        
        success = VerificationService.verify_code(alert_id, data['verification_code'])
        
        if not success:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': 'Emergency alert verified successfully'})
        
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_emergencies(request):
    """
    Get all active emergencies (for hospital/admin use)
    """
    try:
        # In production, add proper role-based permissions
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        alerts = AlertService.get_active_emergencies()
        serializer = EmergencyAlertSerializer(alerts, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Failed to get active emergencies: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )