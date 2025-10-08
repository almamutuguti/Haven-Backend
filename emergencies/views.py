from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import EmergencyAlert, EmergencyStatusUpdate, EmergencyLocationUpdate
from .serializers import (
    EmergencyAlertSerializer, 
    EmergencyAlertCreateSerializer,
    EmergencyStatusUpdateSerializer,
    EmergencyLocationUpdateSerializer,
    EmergencyAlertStatusSerializer,
    EmergencyLocationSerializer
)
# FIX: Update the import path
from .alert_service import AlertService
from accounts.permissions import IsFirstAider

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsFirstAider])
def create_emergency_alert(request):
    """Create a new emergency alert"""
    serializer = EmergencyAlertCreateSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        alert_service = AlertService()
        
        try:
            emergency = alert_service.create_emergency_alert(
                request.user,
                serializer.validated_data
            )
            
            response_serializer = EmergencyAlertSerializer(emergency)
            
            return Response({
                'message': 'Emergency alert created successfully',
                'emergency': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create emergency alert: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_emergency_details(request, emergency_id):
    """Get details of a specific emergency"""
    emergency = get_object_or_404(EmergencyAlert, id=emergency_id)
    
    alert_service = AlertService()
    if not alert_service.can_user_access_emergency(request.user, emergency):
        return Response(
            {'error': 'You do not have permission to view this emergency'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = EmergencyAlertSerializer(emergency)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_emergency_status(request, emergency_id):
    """Update emergency status"""
    emergency = get_object_or_404(EmergencyAlert, id=emergency_id)
    
    alert_service = AlertService()
    if not alert_service.can_user_access_emergency(request.user, emergency):
        return Response(
            {'error': 'You do not have permission to update this emergency'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = EmergencyAlertStatusSerializer(
        emergency, 
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            alert_service.update_emergency_status(
                emergency,
                serializer.validated_data['status'],
                request.user,
                serializer.validated_data.get('notes', '')
            )
            
            return Response({
                'message': 'Emergency status updated successfully',
                'status': serializer.validated_data['status']
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to update status: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsFirstAider])
def update_emergency_location(request, emergency_id):
    """Update emergency location for real-time tracking"""
    emergency = get_object_or_404(EmergencyAlert, id=emergency_id)
    
    if request.user != emergency.first_aider:
        return Response(
            {'error': 'You can only update locations for your own emergencies'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = EmergencyLocationSerializer(
        data=request.data,
        context={'request': request, 'emergency_id': emergency_id}
    )
    
    if serializer.is_valid():
        alert_service = AlertService()
        
        try:
            location_update = alert_service.update_emergency_location(
                emergency,
                serializer.validated_data['latitude'],
                serializer.validated_data['longitude']
            )
            
            return Response({
                'message': 'Location updated successfully',
                'location_id': str(location_update.id)
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to update location: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_emergency_history(request):
    """Get user's emergency history"""
    alert_service = AlertService()
    
    try:
        emergencies = alert_service.get_emergency_history(request.user)
        serializer = EmergencyAlertSerializer(emergencies, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': f'Failed to get emergency history: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsFirstAider])
def cancel_emergency_alert(request, emergency_id):
    """Cancel an emergency alert"""
    emergency = get_object_or_404(EmergencyAlert, id=emergency_id)
    
    if request.user != emergency.first_aider:
        return Response(
            {'error': 'You can only cancel your own emergencies'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if emergency.status in ['completed', 'cancelled']:
        return Response(
            {'error': 'Cannot cancel a completed or already cancelled emergency'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    alert_service = AlertService()
    
    try:
        alert_service.update_emergency_status(
            emergency,
            'cancelled',
            request.user,
            'Emergency cancelled by first aider'
        )
        
        return Response({
            'message': 'Emergency cancelled successfully'
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to cancel emergency: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_emergency_status_updates(request, emergency_id):
    """Get status updates for a specific emergency"""
    emergency = get_object_or_404(EmergencyAlert, id=emergency_id)
    
    alert_service = AlertService()
    if not alert_service.can_user_access_emergency(request.user, emergency):
        return Response(
            {'error': 'You do not have permission to view this emergency'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    status_updates = emergency.status_updates.all()
    serializer = EmergencyStatusUpdateSerializer(status_updates, many=True)
    return Response(serializer.data)