import logging
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
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


class TriggerEmergencyAlertAPIView(APIView):
    """
    Trigger a new emergency alert
    POST emergency/alert/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
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


class AlertStatusAPIView(APIView):
    """
    Get emergency alert status
    GET emergency/{alert_id}/status/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, alert_id):
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


class UpdateAlertLocationAPIView(APIView):
    """
    Update emergency alert location
    PUT emergencies/{alert_id}/location/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request, alert_id):
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


class CancelEmergencyAlertAPIView(APIView):
    """
    Cancel emergency alert
    POST emergencies/{alert_id}/cancel/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, alert_id):
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


class EmergencyHistoryAPIView(APIView):
    """
    Get user's emergency history
    GET emergency/history/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
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


class EmergencyUpdatesAPIView(APIView):
    """
    Get updates for a specific emergency alert
    GET emergencies/{alert_id}/updates/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, alert_id):
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


class VerifyEmergencyAlertAPIView(APIView):
    """
    Verify emergency alert with code
    POST emergencies/{alert_id}/verify/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, alert_id):
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


class ActiveEmergenciesAPIView(APIView):
    """
    Get all active emergencies (for hospital/admin use)
    GET emergencies/active/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            # Check if user has permission to view all active emergencies
            if not request.user.role in ['system_admin', 'hospital_staff', 'first_aider']:
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