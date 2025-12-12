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
    Get and update emergency alert status
    GET emergency/{alert_id}/status/
    POST emergency/{alert_id}/status/
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
        
    def post(self, request, alert_id):
        """
        Update emergency alert status
        POST emergency/{alert_id}/status/
        """
        try:
            # Get the alert
            alert = get_object_or_404(EmergencyAlert, alert_id=alert_id)
            
            # Validate the request data
            serializer = AlertStatusSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            
            # Update the alert status directly
            alert.status = data['status']
            
            # Add details/notes if provided
            if 'details' in data:
                # You might want to save this in a separate field or model
                alert.notes = data['details']
            
            alert.save()
            
            # Log the status update
            logger.info(f"Alert {alert_id} status updated to {data['status']} by user {request.user.id}")
            
            return Response({
                'message': 'Alert status updated successfully',
                'alert_id': alert_id,
                'status': alert.status
            })
            
        except EmergencyAlert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Alert status update failed: {str(e)}")
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
            if not request.user.role in ['system_admin', 'hospital_staff', 'first_aider', 'hospital_admin']:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            alerts = EmergencyAlert.objects.filter(
                is_active=True
            ).exclude(
                status__in=['cancelled', 'completed', 'expired']
            ).order_by('-created_at')
            
            # For hospital staff/admins, only show emergencies relevant to their hospital
            if request.user.role in ['hospital_admin', 'hospital_staff']:
                # Filter by hospital area (based on location proximity)
                # For now, return all active emergencies
                # In production, you would filter by hospital location radius
                pass
            
            serializer = EmergencyAlertSerializer(alerts, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to get active emergencies: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HospitalAssignedEmergenciesAPIView(APIView):
    """
    Get emergencies that should be handled by a specific hospital
    GET emergencies/hospital/<int:hospital_id>/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, hospital_id):
        try:
            # Check if user has permission to view hospital emergencies
            if not request.user.role in ['system_admin', 'hospital_admin', 'hospital_staff']:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # For hospital staff/admins, ensure they can only see their hospital's emergencies
            if request.user.role in ['hospital_admin', 'hospital_staff']:
                user_hospital_id = request.user.hospital_id or (request.user.hospital.id if request.user.hospital else None)
                if user_hospital_id != int(hospital_id):
                    return Response(
                        {'error': 'You can only view emergencies for your assigned hospital'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Get active emergencies
            emergencies = EmergencyAlert.objects.filter(
                is_active=True
            ).exclude(
                status__in=['cancelled', 'completed', 'expired']
            ).order_by('-created_at')
            
            # In a real implementation, you would:
            # 1. Get hospital location from hospitals app
            # 2. Filter emergencies by proximity to hospital
            # 3. Consider hospital specialties and capacity
            
            # For demonstration, let's return all active emergencies
            # with a note about hospital assignment logic
            serializer = EmergencyAlertSerializer(emergencies, many=True)
            
            return Response({
                'hospital_id': hospital_id,
                'emergencies_count': len(serializer.data),
                'emergencies': serializer.data,
                'note': 'This endpoint shows all active emergencies. To filter by hospital, implement location-based proximity matching.'
            })
            
        except Exception as e:
            logger.error(f"Failed to get hospital emergencies: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecentEmergenciesAPIView(APIView):
    """
    Get recent emergencies (last 24 hours)
    GET emergencies/recent/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Check if user has permission to view recent emergencies
            if not request.user.role in ['system_admin', 'hospital_admin', 'hospital_staff', 'first_aider']:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get emergencies from last 24 hours
            twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
            
            emergencies = EmergencyAlert.objects.filter(
                created_at__gte=twenty_four_hours_ago,
                is_active=True
            ).exclude(
                status__in=['cancelled', 'completed', 'expired']
            ).order_by('-created_at')[:50]  # Limit to 50 most recent
            
            serializer = EmergencyAlertSerializer(emergencies, many=True)
            
            return Response({
                'timeframe': 'last 24 hours',
                'emergencies_count': len(serializer.data),
                'emergencies': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Failed to get recent emergencies: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmergencyStatisticsAPIView(APIView):
    """
    Get emergency statistics
    GET emergencies/statistics/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            # Check if user has permission to view statistics
            if not request.user.role in ['system_admin', 'hospital_admin']:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            from django.utils import timezone
            from datetime import timedelta
            
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Calculate statistics
            total_emergencies = EmergencyAlert.objects.count()
            active_emergencies = EmergencyAlert.objects.filter(
                is_active=True
            ).exclude(
                status__in=['cancelled', 'completed', 'expired']
            ).count()
            
            today_emergencies = EmergencyAlert.objects.filter(
                created_at__gte=today_start
            ).count()
            
            week_emergencies = EmergencyAlert.objects.filter(
                created_at__gte=week_ago
            ).count()
            
            month_emergencies = EmergencyAlert.objects.filter(
                created_at__gte=month_ago
            ).count()
            
            # Emergency types breakdown
            emergency_types = EmergencyAlert.objects.values('emergency_type').annotate(
                count=models.Count('id')
            ).order_by('-count')
            
            # Status breakdown
            status_breakdown = EmergencyAlert.objects.values('status').annotate(
                count=models.Count('id')
            ).order_by('-count')
            
            statistics = {
                'overview': {
                    'total_emergencies': total_emergencies,
                    'active_emergencies': active_emergencies,
                    'today_emergencies': today_emergencies,
                    'week_emergencies': week_emergencies,
                    'month_emergencies': month_emergencies,
                },
                'emergency_types': list(emergency_types),
                'status_breakdown': list(status_breakdown),
                'timestamp': now.isoformat()
            }
            
            return Response(statistics)
            
        except Exception as e:
            logger.error(f"Failed to get emergency statistics: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmergencyDetailAPIView(APIView):
    """
    Get detailed information about a specific emergency
    GET emergencies/<str:alert_id>/detail/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, alert_id):
        try:
            # Get the emergency alert
            emergency = get_object_or_404(EmergencyAlert, alert_id=alert_id)
            
            # Check permissions
            # System admins can see all emergencies
            # Hospital staff can see emergencies in their area
            # First aiders can see emergencies they're responding to
            # Regular users can only see their own emergencies
            
            if request.user.role == 'first_aider':
                # First aiders can see all emergencies (for response purposes)
                pass
            elif request.user.role in ['hospital_admin', 'hospital_staff']:
                # Hospital staff can see emergencies in their hospital area
                # In production, add location-based filtering
                pass
            elif request.user.role == 'system_admin':
                # System admins can see everything
                pass
            else:
                # Regular users can only see their own emergencies
                if emergency.user != request.user:
                    return Response(
                        {'error': 'Permission denied'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Serialize emergency data
            emergency_serializer = EmergencyAlertSerializer(emergency)
            
            # Get updates for this emergency
            updates = EmergencyUpdate.objects.filter(alert=emergency).order_by('-created_at')
            updates_serializer = EmergencyUpdateSerializer(updates, many=True)
            
            # Prepare response
            response_data = {
                'emergency': emergency_serializer.data,
                'updates': updates_serializer.data,
                'updates_count': len(updates_serializer.data),
                'is_own_emergency': emergency.user == request.user,
                'can_respond': request.user.role in ['first_aider', 'hospital_staff', 'hospital_admin']
            }
            
            return Response(response_data)
            
        except EmergencyAlert.DoesNotExist:
            return Response(
                {'error': 'Emergency not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to get emergency detail: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )