from rest_framework import serializers
from .models import TrainingProgram, TrainingParticipant
from accounts.serializers import UserProfileSerializer

class TrainingProgramSerializer(serializers.ModelSerializer):
    available_slots = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    duration_text = serializers.CharField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = TrainingProgram
        fields = [
            'id', 'title', 'description', 'status', 'level',
            'start_date', 'end_date', 'duration_days', 'duration_text',
            'max_participants', 'current_participants', 'available_slots', 'is_full',
            'location', 'address', 'instructor_name', 'instructor_qualifications',
            'organization', 'organization_name', 'hospital', 'cost',
            'provides_certification', 'certification_validity_months',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['current_participants', 'created_at', 'updated_at', 'created_by']

class TrainingParticipantSerializer(serializers.ModelSerializer):
    user_details = UserProfileSerializer(source='user', read_only=True)
    training_title = serializers.CharField(source='training.title', read_only=True)
    
    class Meta:
        model = TrainingParticipant
        fields = [
            'id', 'training', 'training_title', 'user', 'user_details',
            'registration_date', 'attended', 'certificate_issued',
            'certificate_issue_date', 'certificate_number',
            'feedback', 'rating'
        ]
        read_only_fields = ['registration_date']

class TrainingProgramCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingProgram
        fields = [
            'title', 'description', 'status', 'level',
            'start_date', 'end_date', 'duration_days',
            'max_participants', 'location', 'address',
            'instructor_name', 'instructor_qualifications',
            'organization', 'hospital', 'cost',
            'provides_certification', 'certification_validity_months'
        ]