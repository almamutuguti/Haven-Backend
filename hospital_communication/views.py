from rest_framework import viewsets, status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone

from emergencies import serializers
from .models import (
    EmergencyHospitalCommunication, 
    CommunicationLog,
    HospitalPreparationChecklist,
    FirstAiderAssessment
)
from .serializers import (
    EmergencyHospitalCommunicationCreateSerializer,
    EmergencyHospitalCommunicationListSerializer,
    EmergencyHospitalCommunicationDetailSerializer,
    HospitalAcknowledgmentSerializer,
    HospitalPreparationUpdateSerializer,
    CommunicationStatusUpdateSerializer,
    FirstAiderAssessmentCreateSerializer,
    FirstAiderAssessmentSerializer,
    CommunicationLogSerializer
)
from .services import HospitalCommunicationService, HospitalResponseService
# Update permissions import to use correct path
from accounts.permissions import IsFirstAider, IsHospitalStaff, IsSystemAdmin




class EmergencyHospitalCommunicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing emergency hospital communications
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = EmergencyHospitalCommunication.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EmergencyHospitalCommunicationCreateSerializer
        elif self.action == 'list':
            return EmergencyHospitalCommunicationListSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return EmergencyHospitalCommunicationDetailSerializer
        return EmergencyHospitalCommunicationListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter based on user type (using role instead of role)
        if user.role == 'first_aider':
            queryset = queryset.filter(first_aider=user)
        elif user.role == 'hospital_admin':
            queryset = queryset.filter(hospital__admins=user)
        
        # Additional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        return queryset.select_related('hospital', 'first_aider')
    
    def perform_create(self, serializer):
        # Ensure first_aider is set to the current user
        communication = serializer.save(first_aider=self.request.user)
        
        # Send emergency alert to hospital
        communication_service = HospitalCommunicationService(communication)
        communication_service.send_emergency_alert()
    
    @action(detail=True, methods=['post'], permission_classes=[IsHospitalStaff])
    def acknowledge(self, request, pk=None):
        """
        Hospital acknowledges receipt of emergency alert
        """
        communication = self.get_object()
        serializer = HospitalAcknowledgmentSerializer(data=request.data)
        
        if serializer.is_valid():
            response_service = HospitalResponseService(communication)
            success = response_service.acknowledge_emergency(
                acknowledged_by=serializer.validated_data['acknowledged_by'],
                preparation_notes=serializer.validated_data.get('preparation_notes', '')
            )
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Emergency acknowledged successfully',
                    'communication_status': communication.status
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to acknowledge emergency'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsHospitalStaff])
    def update_preparation(self, request, pk=None):
        """
        Update hospital preparation status
        """
        communication = self.get_object()
        serializer = HospitalPreparationUpdateSerializer(
            communication, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            response_service = HospitalResponseService(communication)
            success = response_service.update_preparation_status(
                serializer.validated_data
            )
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Preparation status updated successfully',
                    'communication_status': communication.status
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to update preparation status'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsFirstAider])
    def add_assessment(self, request, pk=None):
        """
        Add detailed first aider assessment
        """
        communication = self.get_object()
        
        # Check if assessment already exists
        if hasattr(communication, 'first_aider_assessment'):
            return Response({
                'status': 'error',
                'message': 'Assessment already exists for this communication'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = FirstAiderAssessmentCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            assessment = serializer.save(communication=communication)
            
            # Update communication with assessment data if needed
            if assessment.triage_category:
                communication.priority = self._map_triage_to_priority(assessment.triage_category)
                communication.save()
            
            return Response(
                FirstAiderAssessmentSerializer(assessment).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update communication status (generic status update)
        """
        communication = self.get_object()
        serializer = CommunicationStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            communication.status = new_status
            
            # Set timestamps based on status
            if new_status == 'en_route':
                communication.estimated_arrival_time = timezone.now() + timezone.timedelta(
                    minutes=communication.estimated_arrival_minutes
                )
            elif new_status == 'arrived':
                communication.patient_arrived_at = timezone.now()
            
            communication.save()
            
            # Log status change
            CommunicationLog.objects.create(
                communication=communication,
                channel='in_app',
                direction='outgoing',
                message_type='status_update',
                message_content=f"Status updated to {new_status}",
                message_data={'new_status': new_status, 'notes': serializer.validated_data.get('notes', '')},
                is_successful=True
            )
            
            return Response({
                'status': 'success',
                'message': f'Communication status updated to {new_status}',
                'communication_status': communication.status
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        Get communication logs for a specific emergency communication
        """
        communication = self.get_object()
        logs = communication.logs.all()
        serializer = CommunicationLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsHospitalStaff])
    def hospital_pending(self, request):
        """
        Get pending communications for hospital
        """
        pending_comms = self.get_queryset().filter(
            status__in=['sent', 'acknowledged']
        ).order_by('-priority', 'created_at')
        
        page = self.paginate_queryset(pending_comms)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending_comms, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsFirstAider])
    def first_aider_active(self, request):
        """
        Get active communications for first aider
        """
        active_comms = self.get_queryset().filter(
            status__in=['sent', 'acknowledged', 'preparing', 'ready', 'en_route']
        ).order_by('-created_at')
        
        page = self.paginate_queryset(active_comms)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_comms, many=True)
        return Response(serializer.data)
    
    def _map_triage_to_priority(self, triage_category):
        """
        Map triage category to communication priority
        """
        mapping = {
            'immediate': 'critical',
            'delayed': 'high',
            'minor': 'medium',
            'expectant': 'low'
        }
        return mapping.get(triage_category, 'high')


class CommunicationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing communication logs
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommunicationLogSerializer
    queryset = CommunicationLog.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Use role instead of role
        if user.role == 'first_aider':
            queryset = queryset.filter(communication__first_aider=user)
        elif user.role == 'hospital_admin':
            queryset = queryset.filter(communication__hospital__admins=user)
        
        return queryset.select_related('communication')


class FirstAiderAssessmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing first aider assessments
    """
    permission_classes = [permissions.IsAuthenticated & IsFirstAider]
    serializer_class = FirstAiderAssessmentSerializer
    queryset = FirstAiderAssessment.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Use role instead of role
        if user.role == 'first_aider':
            queryset = queryset.filter(communication__first_aider=user)
        
        return queryset.select_related('communication')


# Additional Class-Based Views for Custom Endpoints
class HospitalPendingCommunicationsAPIView(generics.ListAPIView):
    """
    Get pending communications for hospital
    GET /api/hospital-comms/communications/hospital-pending/
    """
    permission_classes = [permissions.IsAuthenticated & IsHospitalStaff]
    serializer_class = EmergencyHospitalCommunicationListSerializer
    
    def get_queryset(self):
        return EmergencyHospitalCommunication.objects.filter(
            status__in=['sent', 'acknowledged']
        ).order_by('-priority', 'created_at')


class FirstAiderActiveCommunicationsAPIView(generics.ListAPIView):
    """
    Get active communications for first aider
    GET /api/hospital-comms/communications/first-aider-active/
    """
    permission_classes = [permissions.IsAuthenticated & IsFirstAider]
    serializer_class = EmergencyHospitalCommunicationListSerializer
    
    def get_queryset(self):
        return EmergencyHospitalCommunication.objects.filter(
            first_aider=self.request.user,
            status__in=['sent', 'acknowledged', 'preparing', 'ready', 'en_route']
        ).order_by('-created_at')


class AcknowledgeCommunicationAPIView(APIView):
    """
    Hospital acknowledges receipt of emergency alert
    POST /api/hospital-comms/communications/{pk}/acknowledge/
    """
    permission_classes = [permissions.IsAuthenticated & IsHospitalStaff]
    
    def post(self, request, pk):
        communication = get_object_or_404(EmergencyHospitalCommunication, pk=pk)
        serializer = HospitalAcknowledgmentSerializer(data=request.data)
        
        if serializer.is_valid():
            response_service = HospitalResponseService(communication)
            success = response_service.acknowledge_emergency(
                acknowledged_by=serializer.validated_data['acknowledged_by'],
                preparation_notes=serializer.validated_data.get('preparation_notes', '')
            )
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Emergency acknowledged successfully',
                    'communication_status': communication.status
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to acknowledge emergency'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdatePreparationAPIView(APIView):
    """
    Update hospital preparation status
    POST /api/hospital-comms/communications/{pk}/update-preparation/
    """
    permission_classes = [permissions.IsAuthenticated & IsHospitalStaff]
    
    def post(self, request, pk):
        communication = get_object_or_404(EmergencyHospitalCommunication, pk=pk)
        serializer = HospitalPreparationUpdateSerializer(
            communication, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            response_service = HospitalResponseService(communication)
            success = response_service.update_preparation_status(
                serializer.validated_data
            )
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Preparation status updated successfully',
                    'communication_status': communication.status
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to update preparation status'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddAssessmentAPIView(APIView):
    """
    Add detailed first aider assessment
    POST /api/hospital-comms/communications/{pk}/add-assessment/
    """
    permission_classes = [permissions.IsAuthenticated & IsFirstAider]
    
    def post(self, request, pk):
        communication = get_object_or_404(EmergencyHospitalCommunication, pk=pk)
        
        # Check if assessment already exists
        if hasattr(communication, 'first_aider_assessment'):
            return Response({
                'status': 'error',
                'message': 'Assessment already exists for this communication'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = FirstAiderAssessmentCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            assessment = serializer.save(communication=communication)
            
            # Update communication with assessment data if needed
            if assessment.triage_category:
                communication.priority = self._map_triage_to_priority(assessment.triage_category)
                communication.save()
            
            return Response(
                FirstAiderAssessmentSerializer(assessment).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _map_triage_to_priority(self, triage_category):
        """
        Map triage category to communication priority
        """
        mapping = {
            'immediate': 'critical',
            'delayed': 'high',
            'minor': 'medium',
            'expectant': 'low'
        }
        return mapping.get(triage_category, 'high')


class UpdateStatusAPIView(APIView):
    """
    Update communication status (generic status update)
    POST /api/hospital-comms/communications/{pk}/update-status/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        communication = get_object_or_404(EmergencyHospitalCommunication, pk=pk)
        serializer = CommunicationStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            communication.status = new_status
            
            # Set timestamps based on status
            if new_status == 'en_route':
                communication.estimated_arrival_time = timezone.now() + timezone.timedelta(
                    minutes=communication.estimated_arrival_minutes
                )
            elif new_status == 'arrived':
                communication.patient_arrived_at = timezone.now()
            
            communication.save()
            
            # Log status change
            CommunicationLog.objects.create(
                communication=communication,
                channel='in_app',
                direction='outgoing',
                message_type='status_update',
                message_content=f"Status updated to {new_status}",
                message_data={'new_status': new_status, 'notes': serializer.validated_data.get('notes', '')},
                is_successful=True
            )
            
            return Response({
                'status': 'success',
                'message': f'Communication status updated to {new_status}',
                'communication_status': communication.status
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommunicationLogsAPIView(generics.ListAPIView):
    """
    Get communication logs for a specific emergency communication
    GET /api/hospital-comms/communications/{pk}/logs/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommunicationLogSerializer
    
    def get_queryset(self):
        communication_id = self.kwargs['pk']
        return CommunicationLog.objects.filter(communication_id=communication_id)