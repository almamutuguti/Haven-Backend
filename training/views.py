from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import TrainingProgram, TrainingParticipant
from .serializers import (
    TrainingProgramSerializer, 
    TrainingProgramCreateSerializer,
    TrainingParticipantSerializer
)
from accounts.permissions import (
    IsSystemAdmin, IsOrganizationAdmin, IsHospitalAdmin
)

class TrainingProgramListCreateAPIView(generics.ListCreateAPIView):
    """List all training programs or create new one"""
    serializer_class = TrainingProgramSerializer
    
    def get_queryset(self):
        queryset = TrainingProgram.objects.all()
        
        # Filter by organization if user is organization admin
        user = self.request.user
        if user.role == 'organization_admin' and user.organization:
            queryset = queryset.filter(organization=user.organization)
        
        # Filter by hospital if user is hospital admin
        elif user.role == 'hospital_admin' and user.hospital:
            queryset = queryset.filter(hospital=user.hospital)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by search term
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(instructor_name__icontains=search)
            )
        
        return queryset.order_by('-start_date')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TrainingProgramCreateSerializer
        return TrainingProgramSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsSystemAdmin | IsOrganizationAdmin | IsHospitalAdmin]
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class TrainingProgramDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete training program"""
    queryset = TrainingProgram.objects.all()
    serializer_class = TrainingProgramSerializer
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TrainingProgramCreateSerializer
        return TrainingProgramSerializer
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated(), IsSystemAdmin | IsOrganizationAdmin | IsHospitalAdmin]
        return [permissions.IsAuthenticated()]
    
    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        
        # Organization admins can only manage their organization's programs
        if request.user.role == 'organization_admin':
            if obj.organization != request.user.organization:
                raise PermissionDenied("You can only manage your organization's training programs")
        
        # Hospital admins can only manage their hospital's programs
        elif request.user.role == 'hospital_admin':
            if obj.hospital != request.user.hospital:
                raise PermissionDenied("You can only manage your hospital's training programs")

class TrainingProgramParticipantsAPIView(generics.ListAPIView):
    """List participants for a training program"""
    serializer_class = TrainingParticipantSerializer
    
    def get_queryset(self):
        training_id = self.kwargs['training_id']
        return TrainingParticipant.objects.filter(training_id=training_id)
    
    def get_permissions(self):
        training_id = self.kwargs['training_id']
        training = TrainingProgram.objects.get(id=training_id)
        
        # Allow access to program creator, system admin, or organization/hospital admins
        return [permissions.IsAuthenticated()]

class JoinTrainingProgramAPIView(APIView):
    """Allow users to join a training program"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, training_id):
        try:
            training = TrainingProgram.objects.get(id=training_id)
            
            # Check if training is full
            if training.is_full:
                return Response(
                    {'error': 'Training program is full'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user already registered
            if TrainingParticipant.objects.filter(training=training, user=request.user).exists():
                return Response(
                    {'error': 'You are already registered for this training'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create participant
            participant = TrainingParticipant.objects.create(
                training=training,
                user=request.user
            )
            
            # Update participant count
            training.current_participants += 1
            training.save()
            
            return Response({
                'message': 'Successfully registered for training program',
                'participant': TrainingParticipantSerializer(participant).data
            })
            
        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Training program not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class TrainingStatisticsAPIView(APIView):
    """Get training statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        queryset = TrainingProgram.objects.all()
        
        # Filter by organization/hospital for admins
        if user.role == 'organization_admin' and user.organization:
            queryset = queryset.filter(organization=user.organization)
        elif user.role == 'hospital_admin' and user.hospital:
            queryset = queryset.filter(hospital=user.hospital)
        
        total_programs = queryset.count()
        upcoming_programs = queryset.filter(status='upcoming').count()
        completed_programs = queryset.filter(status='completed').count()
        
        # Get recent programs
        recent_programs = queryset.order_by('-created_at')[:5]
        
        # Get user's registered trainings
        user_trainings = TrainingParticipant.objects.filter(user=user).count()
        
        return Response({
            'statistics': {
                'total_programs': total_programs,
                'upcoming_programs': upcoming_programs,
                'completed_programs': completed_programs,
                'user_trainings': user_trainings
            },
            'recent_programs': TrainingProgramSerializer(recent_programs, many=True).data
        })