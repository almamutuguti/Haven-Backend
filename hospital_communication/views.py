from datetime import datetime, timedelta
from venv import logger
from django.http import HttpResponse
from rest_framework import viewsets, status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone

from emergencies import serializers
from hospital_communication.utils import ReportGenerator
from hospitals.models import Hospital
from .models import (
    EmergencyHospitalCommunication, 
    CommunicationLog,
    HospitalPreparationChecklist,
    FirstAiderAssessment,
    HospitalReport,
    PatientAssessment
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
    CommunicationLogSerializer,
    HospitalReportSerializer,
    PatientAssessmentCreateSerializer,
    PatientAssessmentSerializer,
    ReportRequestSerializer
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

    def get_permissions(self):
        """
        Override get_permissions to apply different permissions for different actions
        """
        if self.action in ['create', 'add_assessment', 'first_aider_active']:
            permission_classes = [permissions.IsAuthenticated & IsFirstAider]
        elif self.action in ['acknowledge', 'update_preparation', 'hospital_pending']:
            permission_classes = [permissions.IsAuthenticated & (IsHospitalStaff | IsFirstAider)]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
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
        
        # Debug information
        print(f"DEBUG - User: {user.username}, Role: {user.role}")
        print(f"DEBUG - User hospital: {getattr(user, 'hospital', None)}")
        
        # Filter based on user type
        if user.role == 'first_aider':
            queryset = queryset.filter(first_aider=user)
        elif user.role == 'hospital_staff':
            # FIX: Use the user's hospital directly instead of hospital__admins
            if hasattr(user, 'hospital') and user.hospital:
                queryset = queryset.filter(hospital=user.hospital)
                print(f"DEBUG - Filtering for hospital: {user.hospital.name}")
            else:
                # If hospital staff has no hospital assigned, return empty queryset
                print("DEBUG - Hospital staff has no hospital assigned")
                return EmergencyHospitalCommunication.objects.none()
        
        # Additional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
            
        # Hospital ID filter from query params (for frontend filtering)
        hospital_id = self.request.query_params.get('hospital')
        if hospital_id and user.role == 'hospital_staff':
            # Only allow filtering by hospital if it matches the user's hospital
            if hasattr(user, 'hospital') and user.hospital and str(user.hospital.id) == hospital_id:
                queryset = queryset.filter(hospital_id=hospital_id)
        
        return queryset.select_related('hospital', 'first_aider')
    
    def perform_create(self, serializer):
        # Ensure first_aider is set to the current user
        communication = serializer.save(first_aider=self.request.user)
        
        # Send emergency alert to hospital
        communication_service = HospitalCommunicationService(communication)
        communication_service.send_emergency_alert()
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """
        Hospital acknowledges receipt of emergency alert
        """
        communication = self.get_object()
        
        # Check if user has permission to acknowledge for this hospital
        if request.user.role == 'hospital_staff' and hasattr(request.user, 'hospital'):
            if communication.hospital != request.user.hospital:
                return Response({
                    'status': 'error',
                    'message': 'You can only acknowledge communications for your hospital'
                }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = HospitalAcknowledgmentSerializer(data=request.data)
        
        if serializer.is_valid():
            # Use current user as acknowledged_by if not provided
            acknowledged_by = serializer.validated_data.get('acknowledged_by', request.user)
            preparation_notes = serializer.validated_data.get('preparation_notes', '')
            
            response_service = HospitalResponseService(communication)
            success = response_service.acknowledge_emergency(
                acknowledged_by=acknowledged_by,
                preparation_notes=preparation_notes
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
    
    @action(detail=True, methods=['post'])
    def update_preparation(self, request, pk=None):
        """
        Update preparation status - accessible to both first aiders and hospital staff
        """
        communication = self.get_object()
        user = request.user
        
        # Determine allowed fields based on user role
        allowed_fields = []
        
        if user.role == 'first_aider':
            allowed_fields = ['first_aid_provided', 'vital_signs', 'estimated_arrival_minutes']
            if communication.first_aider != user:
                return Response({
                    'status': 'error',
                    'message': 'You can only update preparations for your own communications'
                }, status=status.HTTP_403_FORBIDDEN)
                
        elif user.role == 'hospital_staff':
            allowed_fields = [
                'doctors_ready', 'nurses_ready', 'equipment_ready', 
                'bed_ready', 'blood_available', 'hospital_preparation_notes'
            ]
            if hasattr(user, 'hospital') and communication.hospital != user.hospital:
                return Response({
                    'status': 'error',
                    'message': 'You can only update preparations for your hospital'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Filter data to only allowed fields
        filtered_data = {key: value for key, value in request.data.items() if key in allowed_fields}
        
        if not filtered_data:
            return Response({
                'status': 'error',
                'message': f'No valid fields to update for your role ({user.role})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = HospitalPreparationUpdateSerializer(
            communication, 
            data=filtered_data, 
            partial=True,
            context={'user_role': user.role}
        )
        
        if serializer.is_valid():
            response_service = HospitalResponseService(communication)
            # FIX: Remove the extra parameters
            success = response_service.update_preparation_status(
                serializer.validated_data
            )
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Preparation status updated successfully',
                    'communication_status': communication.status,
                    'updated_by': user.role,
                    'updated_fields': list(filtered_data.keys())
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to update preparation status'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_assessment(self, request, pk=None):
        """
        Add detailed first aider assessment
        """
        communication = self.get_object()
        
        # Check if first aider owns this communication
        if request.user.role == 'first_aider' and communication.first_aider != request.user:
            return Response({
                'status': 'error',
                'message': 'You can only add assessments to your own communications'
            }, status=status.HTTP_403_FORBIDDEN)
        
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
        
        # Check permissions based on user role
        if request.user.role == 'first_aider' and communication.first_aider != request.user:
            return Response({
                'status': 'error',
                'message': 'You can only update status of your own communications'
            }, status=status.HTTP_403_FORBIDDEN)
            
        if request.user.role == 'hospital_staff' and hasattr(request.user, 'hospital'):
            if communication.hospital != request.user.hospital:
                return Response({
                    'status': 'error',
                    'message': 'You can only update status of communications for your hospital'
                }, status=status.HTTP_403_FORBIDDEN)
        
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
        
        # Check permissions
        if request.user.role == 'first_aider' and communication.first_aider != request.user:
            return Response({
                'status': 'error',
                'message': 'You can only view logs for your own communications'
            }, status=status.HTTP_403_FORBIDDEN)
            
        if request.user.role == 'hospital_staff' and hasattr(request.user, 'hospital'):
            if communication.hospital != request.user.hospital:
                return Response({
                    'status': 'error',
                    'message': 'You can only view logs for communications for your hospital'
                }, status=status.HTTP_403_FORBIDDEN)
        
        logs = communication.logs.all()
        serializer = CommunicationLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def hospital_pending(self, request):
        """
        Get pending communications for hospital
        """
        if request.user.role != 'hospital_staff' or not hasattr(request.user, 'hospital'):
            return Response({
                'status': 'error',
                'message': 'Only hospital staff can access pending communications'
            }, status=status.HTTP_403_FORBIDDEN)
        
        pending_comms = self.get_queryset().filter(
            status__in=['sent', 'acknowledged']
        ).order_by('-priority', 'created_at')
        
        page = self.paginate_queryset(pending_comms)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending_comms, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def first_aider_active(self, request):
        """
        Get active communications for first aider
        """
        if request.user.role != 'first_aider':
            return Response({
                'status': 'error',
                'message': 'Only first aiders can access active communications'
            }, status=status.HTTP_403_FORBIDDEN)
        
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
    

    @action(detail=True, methods=['post', 'put'])
    def add_patient_assessment(self, request, pk=None):
        """
        Add or update comprehensive patient assessment for a communication
        POST/PUT /api/hospital-comms/communications/{pk}/add-patient-assessment/
        """
        communication = self.get_object()
        
        # Check permissions
        if request.user.role == 'first_aider' and communication.first_aider != request.user:
            return Response({
                'status': 'error',
                'message': 'You can only add assessments to your own communications'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if assessment already exists
        assessment_exists = hasattr(communication, 'patient_assessment')
        
        if assessment_exists and request.method == 'POST':
            return Response({
                'status': 'error',
                'message': 'Patient assessment already exists. Use PUT to update.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PatientAssessmentCreateSerializer(
            data=request.data,
            instance=communication.patient_assessment if assessment_exists else None
        )
        
        if serializer.is_valid():
            if assessment_exists:
                # Update existing assessment
                assessment = serializer.save()
                message = 'Patient assessment updated successfully'
            else:
                # Create new assessment
                assessment = serializer.save(communication=communication)
                message = 'Patient assessment created successfully'
            
            # Update communication priority based on assessment
            if assessment.condition:
                communication.priority = assessment.priority_level
                communication.save()
            
            # Log the assessment activity
            CommunicationLog.objects.create(
                communication=communication,
                channel='in_app',
                direction='outgoing',
                message_type='patient_assessment',
                message_content=f"Patient assessment {'updated' if assessment_exists else 'added'}",
                message_data={
                    'assessment_id': str(assessment.id),
                    'patient_name': assessment.full_name,
                    'condition': assessment.condition,
                    'triage': assessment.triage_category
                },
                is_successful=True
            )
            
            return Response({
                'status': 'success',
                'message': message,
                'assessment': PatientAssessmentSerializer(assessment).data,
                'communication_priority': communication.priority
            }, status=status.HTTP_200_OK if assessment_exists else status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def patient_assessment(self, request, pk=None):
        """
        Get patient assessment for a communication
        GET /api/hospital-comms/communications/{pk}/patient-assessment/
        """
        communication = self.get_object()
        
        if not hasattr(communication, 'patient_assessment'):
            return Response({
                'status': 'error',
                'message': 'No patient assessment found for this communication'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PatientAssessmentSerializer(communication.patient_assessment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def delete_patient_assessment(self, request, pk=None):
        """
        Delete patient assessment for a communication
        DELETE /api/hospital-comms/communications/{pk}/delete-patient-assessment/
        """
        communication = self.get_object()
        
        # Check permissions
        if request.user.role == 'first_aider' and communication.first_aider != request.user:
            return Response({
                'status': 'error',
                'message': 'You can only delete assessments from your own communications'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not hasattr(communication, 'patient_assessment'):
            return Response({
                'status': 'error',
                'message': 'No patient assessment found for this communication'
            }, status=status.HTTP_404_NOT_FOUND)
        
        assessment = communication.patient_assessment
        assessment_id = assessment.id
        assessment.delete()
        
        # Log the deletion
        CommunicationLog.objects.create(
            communication=communication,
            channel='in_app',
            direction='outgoing',
            message_type='patient_assessment_deleted',
            message_content="Patient assessment deleted",
            message_data={'assessment_id': str(assessment_id)},
            is_successful=True
        )
        
        return Response({
            'status': 'success',
            'message': 'Patient assessment deleted successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def create_with_assessment(self, request):
        """
        Create hospital communication and assessment in one call
        POST /api/hospital-comms/communications/create-with-assessment/
        """
        try:
            # Extract communication and assessment data
            communication_data = request.data.get('communication', {})
            assessment_data = request.data.get('assessment', {})
            
            # Create communication first
            comm_serializer = EmergencyHospitalCommunicationCreateSerializer(
                data=communication_data,
                context={'request': request}
            )
            
            if not comm_serializer.is_valid():
                return Response({
                    'status': 'error',
                    'message': 'Communication validation failed',
                    'errors': comm_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            communication = comm_serializer.save()
            
            # Create assessment if data provided
            assessment = None
            if assessment_data:
                assessment_serializer = PatientAssessmentCreateSerializer(
                    data=assessment_data
                )
                
                if assessment_serializer.is_valid():
                    assessment = assessment_serializer.save(communication=communication)
                else:
                    # If assessment fails, still return success but with warning
                    print("Assessment creation failed:", assessment_serializer.errors)
            
            # Prepare response
            response_data = {
                'status': 'success',
                'message': 'Communication created successfully',
                'communication': EmergencyHospitalCommunicationDetailSerializer(communication).data,
            }
            
            if assessment:
                response_data['assessment'] = PatientAssessmentSerializer(assessment).data
                response_data['message'] = 'Communication and assessment created successfully'
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to create communication: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def get_or_create_assessment(self, request, pk=None):
        """
        Get existing assessment or create empty one
        GET /api/hospital-comms/communications/{pk}/get-or-create-assessment/
        """
        communication = self.get_object()
        
        # Check if assessment already exists
        if hasattr(communication, 'patient_assessment'):
            serializer = PatientAssessmentSerializer(communication.patient_assessment)
            return Response({
                'status': 'existing',
                'assessment': serializer.data
            })
        
        # Create empty assessment
        empty_assessment_data = {
            'first_name': communication.victim_name.split(' ')[0] if communication.victim_name else '',
            'last_name': ' '.join(communication.victim_name.split(' ')[1:]) if communication.victim_name else '',
            'age': communication.victim_age,
            'gender': communication.victim_gender,
            'communication_id': communication.id
        }
        
        assessment_serializer = PatientAssessmentCreateSerializer(data=empty_assessment_data)
        
        if assessment_serializer.is_valid():
            assessment = assessment_serializer.save(communication=communication)
            return Response({
                'status': 'created',
                'assessment': PatientAssessmentSerializer(assessment).data
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Failed to create assessment',
                'errors': assessment_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


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
        elif user.role == 'hospital_staff':
            queryset = queryset.filter(communication__hospital__admins=user)
        
        return queryset.select_related('communication')


class FirstAiderAssessmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing first aider assessments
    """
    permission_classes = [permissions.IsAuthenticated & IsFirstAider, IsSystemAdmin]
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
    permission_classes = [permissions.IsAuthenticated & IsHospitalStaff, IsSystemAdmin]
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
    permission_classes = [permissions.IsAuthenticated & IsFirstAider, IsSystemAdmin]
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
    permission_classes = [permissions.IsAuthenticated & IsHospitalStaff, IsSystemAdmin]
    
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
    Update preparation status - accessible to both first aiders and hospital staff
    POST /api/hospital-comms/api/communications/{pk}/update-preparation/
    """
    permission_classes = [permissions.IsAuthenticated & (IsFirstAider | IsHospitalStaff)]
    
    def post(self, request, pk):
        communication = get_object_or_404(EmergencyHospitalCommunication, pk=pk)
        user = request.user
        
        # Determine allowed fields based on user role
        allowed_fields = []
        
        if user.role == 'first_aider':
            allowed_fields = ['first_aid_provided', 'vital_signs', 'estimated_arrival_minutes']
            if communication.first_aider != user:
                return Response({
                    'status': 'error',
                    'message': 'You can only update preparations for your own communications'
                }, status=status.HTTP_403_FORBIDDEN)
                
        elif user.role == 'hospital_staff':
            allowed_fields = [
                'doctors_ready', 'nurses_ready', 'equipment_ready', 
                'bed_ready', 'blood_available', 'hospital_preparation_notes'
            ]
            if hasattr(user, 'hospital') and communication.hospital != user.hospital:
                return Response({
                    'status': 'error',
                    'message': 'You can only update preparations for your hospital'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Filter data to only allowed fields
        filtered_data = {key: value for key, value in request.data.items() if key in allowed_fields}
        
        if not filtered_data:
            return Response({
                'status': 'error',
                'message': f'No valid fields to update for your role ({user.role})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = HospitalPreparationUpdateSerializer(
            communication, 
            data=filtered_data, 
            partial=True,
            context={'user_role': user.role}
        )
        
        if serializer.is_valid():
            response_service = HospitalResponseService(communication)
            # FIX: Remove the extra parameters that the method doesn't accept
            success = response_service.update_preparation_status(
                serializer.validated_data
            )
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Preparation status updated successfully',
                    'communication_status': communication.status,
                    'updated_by': user.role,
                    'updated_fields': list(filtered_data.keys())
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
    permission_classes = [permissions.IsAuthenticated & IsFirstAider, IsSystemAdmin]
    
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
    
class PatientAssessmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient assessments
    """
    permission_classes = [permissions.IsAuthenticated & IsFirstAider]
    queryset = PatientAssessment.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PatientAssessmentCreateSerializer
        return PatientAssessmentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == 'first_aider':
            queryset = queryset.filter(communication__first_aider=user)
        elif user.role == 'hospital_staff':
            queryset = queryset.filter(communication__hospital__admins=user)
        
        return queryset.select_related('communication')
    
    def perform_create(self, serializer):
        # Patient assessment is created through the communication endpoint
        raise serializers.ValidationError(
            "Use the communication assessment endpoint to create patient assessments"
        )
    

class HospitalReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hospital reports
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = HospitalReportSerializer
    queryset = HospitalReport.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'hospital_staff' or user.role == 'hospital_admin':
            if hasattr(user, 'hospital') and user.hospital:
                queryset = queryset.filter(hospital=user.hospital)
            else:
                return HospitalReport.objects.none()
        
        # Filter by hospital ID if provided
        hospital_id = self.request.query_params.get('hospital')
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                start_date__gte=start_date,
                end_date__lte=end_date
            )
        
        # Filter by report type
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        return queryset.select_related('hospital', 'generated_by')
    
    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate a new hospital report
        POST /api/hospital-comms/reports/generate/
        """
        serializer = ReportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = serializer.validated_data
            user = request.user
            
            # Get hospital for current user
            hospital = None
            if hasattr(user, 'hospital') and user.hospital:
                hospital = user.hospital
            elif request.data.get('hospital_id'):
                hospital = get_object_or_404(Hospital, id=request.data['hospital_id'])
            
            if not hospital:
                return Response(
                    {'error': 'No hospital assigned to user or specified'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check permissions
            if user.role in ['hospital_staff', 'hospital_admin'] and hasattr(user, 'hospital'):
                if user.hospital != hospital:
                    return Response(
                        {'error': 'You can only generate reports for your assigned hospital'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Get date range
            start_date, end_date = ReportGenerator.get_date_range_for_period(
                data['period'],
                data.get('start_date'),
                data.get('end_date')
            )
            
            # Calculate statistics
            statistics = ReportGenerator.calculate_statistics(hospital, start_date, end_date)
            
            # Get communications summary
            communications_summary = []
            if data['include_communications']:
                communications_summary = ReportGenerator.get_communications_summary(
                    hospital, start_date, end_date
                )
            
            # Generate recommendations
            recommendations = []
            if data['include_recommendations']:
                recommendations = ReportGenerator.generate_recommendations(statistics)
            
            # Create report title
            period_display = dict(HospitalReport.PERIOD_CHOICES).get(data['period'], data['period'])
            report_type_display = dict(HospitalReport.REPORT_TYPE_CHOICES).get(data['report_type'], data['report_type'])
            title = f"{report_type_display} - {hospital.name} ({period_display})"
            
            # Create report instance
            report_data = {
                'hospital': hospital.id,
                'title': title,
                'report_type': data['report_type'],
                'period': data['period'],
                'start_date': start_date,
                'end_date': end_date,
                'statistics': statistics,
                'breakdowns': {
                    'by_status': statistics.get('communications_by_status', {}),
                    'by_priority': statistics.get('communications_by_priority', {}),
                    'by_time': statistics.get('communications_by_time', {}),
                },
                'communications': communications_summary,
                'recommendations': recommendations,
            }
            
            report_serializer = HospitalReportSerializer(data=report_data, context={'request': request})
            
            if not report_serializer.is_valid():
                return Response(report_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            report = report_serializer.save(generated_by=user)
            
            # Generate files if requested
            if data['generate_csv']:
                try:
                    # Generate CSV file
                    from django.core.files.base import ContentFile
                    csv_content = ReportGenerator.generate_csv_report(
                        hospital,
                        start_date,
                        end_date,
                        EmergencyHospitalCommunication.objects.filter(
                            hospital=hospital,
                            created_at__date__gte=start_date,
                            created_at__date__lte=end_date
                        )
                    )
                    
                    csv_file = ContentFile(csv_content.encode('utf-8'))
                    report.csv_file.save(
                        f"report_{hospital.id}_{start_date}_{end_date}.csv",
                        csv_file
                    )
                    report.save()
                except Exception as e:
                    logger.error(f"Failed to generate CSV report: {str(e)}")
            
            return Response(
                HospitalReportSerializer(report).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return Response(
                {'error': f'Failed to generate report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Download report as PDF
        GET /api/hospital-comms/reports/{id}/download-pdf/
        """
        report = self.get_object()
        
        if not report.pdf_file:
            return Response(
                {'error': 'PDF file not available for this report'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response = HttpResponse(report.pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.title}.pdf"'
        return response
    
    @action(detail=True, methods=['get'])
    def download_csv(self, request, pk=None):
        """
        Download report as CSV
        GET /api/hospital-comms/reports/{id}/download-csv/
        """
        report = self.get_object()
        
        if not report.csv_file:
            # Generate CSV on the fly if not already generated
            try:
                hospital = report.hospital
                start_date = report.start_date
                end_date = report.end_date
                
                csv_content = ReportGenerator.generate_csv_report(
                    hospital,
                    start_date,
                    end_date,
                    EmergencyHospitalCommunication.objects.filter(
                        hospital=hospital,
                        created_at__date__gte=start_date,
                        created_at__date__lte=end_date
                    )
                )
                
                response = HttpResponse(csv_content, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{report.title}.csv"'
                return response
            except Exception as e:
                logger.error(f"Failed to generate CSV: {str(e)}")
                return Response(
                    {'error': 'Failed to generate CSV file'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        response = HttpResponse(report.csv_file, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report.title}.csv"'
        return response
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """
        Share report with other users
        POST /api/hospital-comms/reports/{id}/share/
        """
        report = self.get_object()
        
        # Check permissions
        if request.user.role in ['hospital_staff', 'hospital_admin']:
            if hasattr(request.user, 'hospital') and request.user.hospital != report.hospital:
                return Response(
                    {'error': 'You can only share reports for your hospital'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # For now, just mark as shared
        report.is_shared = True
        report.save()
        
        return Response({
            'status': 'success',
            'message': 'Report marked as shared',
            'report_id': report.id
        })


class HospitalStatisticsReportAPIView(APIView):
    """
    API endpoint for quick statistics report
    GET /api/hospital-comms/reports/statistics/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            # Get hospital for current user
            hospital = None
            if hasattr(user, 'hospital') and user.hospital:
                hospital = user.hospital
            else:
                return Response(
                    {'error': 'No hospital assigned to user'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get date range from query params (default to last 30 days)
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            
            custom_start = request.GET.get('start_date')
            custom_end = request.GET.get('end_date')
            
            if custom_start and custom_end:
                try:
                    start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
                    end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
                except ValueError:
                    return Response(
                        {'error': 'Invalid date format. Use YYYY-MM-DD'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Calculate statistics
            statistics = ReportGenerator.calculate_statistics(hospital, start_date, end_date)
            
            # Get recent communications
            recent_comms = ReportGenerator.get_communications_summary(hospital, start_date, end_date, limit=10)
            
            # Get bed occupancy if available
            bed_occupancy = 0
            if hasattr(hospital, 'capacity'):
                bed_occupancy = hospital.capacity.bed_occupancy_rate
            
            statistics['bed_occupancy_rate'] = bed_occupancy
            
            # Generate recommendations
            recommendations = ReportGenerator.generate_recommendations(statistics)
            
            response_data = {
                'hospital': {
                    'id': hospital.id,
                    'name': hospital.name,
                    'type': hospital.hospital_type,
                    'level': hospital.level,
                },
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'period_days': (end_date - start_date).days + 1
                },
                'statistics': statistics,
                'recent_communications': recent_comms,
                'recommendations': recommendations,
                'generated_at': timezone.now().isoformat(),
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Statistics report failed: {str(e)}")
            return Response(
                {'error': f'Failed to generate statistics report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExportCommunicationsDataAPIView(APIView):
    """
    Export communications data as CSV
    GET /api/hospital-comms/reports/export-data/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            # Get hospital for current user
            hospital = None
            if hasattr(user, 'hospital') and user.hospital:
                hospital = user.hospital
            else:
                return Response(
                    {'error': 'No hospital assigned to user'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get date range from query params
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            
            custom_start = request.GET.get('start_date')
            custom_end = request.GET.get('end_date')
            
            if custom_start and custom_end:
                try:
                    start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
                    end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
                except ValueError:
                    return Response(
                        {'error': 'Invalid date format. Use YYYY-MM-DD'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get communications
            communications = EmergencyHospitalCommunication.objects.filter(
                hospital=hospital,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).order_by('-created_at')
            
            # Generate CSV
            csv_content = ReportGenerator.generate_csv_report(hospital, start_date, end_date, communications)
            
            # Create response
            filename = f"emergency_communications_{hospital.name}_{start_date}_{end_date}.csv"
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            logger.error(f"Data export failed: {str(e)}")
            return Response(
                {'error': f'Failed to export data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
