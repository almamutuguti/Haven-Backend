from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import (
    EmergencyHospitalCommunication, 
    CommunicationLog, 
    HospitalPreparationChecklist,
    FirstAiderAssessment
)
from emergencies.models import EmergencyAlert
from hospitals.models import Hospital
from accounts.models import CustomUser as User

class FirstAiderAssessmentSerializer(serializers.ModelSerializer):
    gcs_total = serializers.ReadOnlyField()
    
    class Meta:
        model = FirstAiderAssessment
        fields = '__all__'
        read_only_fields = ('communication', 'created_at', 'updated_at')
    
    def validate_gcs_eyes(self, value):
        if value and (value < 1 or value > 4):
            raise serializers.ValidationError("GCS Eyes must be between 1 and 4")
        return value
    
    def validate_gcs_verbal(self, value):
        if value and (value < 1 or value > 5):
            raise serializers.ValidationError("GCS Verbal must be between 1 and 5")
        return value
    
    def validate_gcs_motor(self, value):
        if value and (value < 1 or value > 6):
            raise serializers.ValidationError("GCS Motor must be between 1 and 6")
        return value
    
    def validate_oxygen_saturation(self, value):
        if value and (value < 0 or value > 100):
            raise serializers.ValidationError("Oxygen saturation must be between 0 and 100")
        return value

class HospitalPreparationChecklistSerializer(serializers.ModelSerializer):
    completion_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = HospitalPreparationChecklist
        fields = '__all__'
        read_only_fields = ('communication', 'created_at', 'updated_at')

class CommunicationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationLog
        fields = '__all__'
        read_only_fields = ('communication', 'sent_at')

class EmergencyHospitalCommunicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new emergency hospital communications"""
    emergency_alert_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = EmergencyHospitalCommunication
        fields = [
            'emergency_alert_id', 'hospital', 'first_aider', 'priority',
            'victim_name', 'victim_age', 'victim_gender', 'chief_complaint',
            'vital_signs', 'initial_assessment', 'first_aid_provided',
            'estimated_arrival_minutes', 'required_specialties', 'equipment_needed',
            'blood_type_required'
        ]
    
    def validate_emergency_alert_id(self, value):
        try:
            EmergencyAlert.objects.get(id=value)
        except EmergencyAlert.DoesNotExist:
            raise serializers.ValidationError("Emergency alert not found")
        return value
    
    def validate_hospital(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Selected hospital is not active")
        return value
    
    def validate_first_aider(self, value):
        if value.role != 'first_aider':
            raise serializers.ValidationError("User must be a first aider")
        return value
    
    def create(self, validated_data):
        emergency_alert_id = validated_data.pop('emergency_alert_id')
        communication = EmergencyHospitalCommunication.objects.create(
            emergency_alert_id=emergency_alert_id,
            **validated_data
        )
        return communication

class EmergencyHospitalCommunicationListSerializer(serializers.ModelSerializer):
    """Serializer for listing emergency communications"""
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    first_aider_name = serializers.CharField(source='first_aider.get_full_name', read_only=True)
    alert_reference_id = serializers.CharField(read_only=True)
    
    class Meta:
        model = EmergencyHospitalCommunication
        fields = [
            'id', 'alert_reference_id', 'hospital_name', 'first_aider_name',
            'status', 'priority', 'victim_name', 'estimated_arrival_minutes',
            'created_at', 'sent_to_hospital_at', 'hospital_ready_at'
        ]

class EmergencyHospitalCommunicationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with nested relationships"""
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    hospital_address = serializers.CharField(source='hospital.address', read_only=True)
    hospital_phone = serializers.CharField(source='hospital.phone_number', read_only=True)
    first_aider_name = serializers.CharField(source='first_aider.get_full_name', read_only=True)
    first_aider_phone = serializers.CharField(source='first_aider.phone_number', read_only=True)
    
    # Nested serializers
    assessment = FirstAiderAssessmentSerializer(
        source='first_aider_assessment', 
        read_only=True
    )
    checklist = HospitalPreparationChecklistSerializer(
        source='preparation_checklist',
        read_only=True
    )
    communication_logs = CommunicationLogSerializer(
        many=True,
        read_only=True
    )
    
    class Meta:
        model = EmergencyHospitalCommunication
        fields = '__all__'

class HospitalAcknowledgmentSerializer(serializers.Serializer):
    """Serializer for hospital acknowledgment"""
    acknowledged_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='hospital_admin')
    )
    preparation_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_acknowledged_by(self, value):
        if value.role != 'hospital_admin':
            raise serializers.ValidationError("User must be a hospital admin")
        return value

class HospitalPreparationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating hospital preparation status"""
    
    class Meta:
        model = EmergencyHospitalCommunication
        fields = [
            'doctors_ready', 'nurses_ready', 'equipment_ready', 'bed_ready',
            'blood_available', 'hospital_preparation_notes'
        ]

class CommunicationStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating communication status"""
    status = serializers.ChoiceField(
        choices=EmergencyHospitalCommunication.STATUS_CHOICES
    )
    notes = serializers.CharField(required=False, allow_blank=True)

class FirstAiderAssessmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating first aider assessment"""
    
    class Meta:
        model = FirstAiderAssessment
        exclude = ('communication', 'created_at', 'updated_at')
    
    def validate(self, data):
        # Validate GCS components if provided
        gcs_fields = ['gcs_eyes', 'gcs_verbal', 'gcs_motor']
        provided_gcs = [data.get(field) for field in gcs_fields if data.get(field) is not None]
        
        if len(provided_gcs) > 0 and len(provided_gcs) < 3:
            raise serializers.ValidationError(
                "All GCS components (eyes, verbal, motor) must be provided together"
            )
        return data