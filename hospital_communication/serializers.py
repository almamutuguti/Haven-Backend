from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import (
    EmergencyHospitalCommunication, 
    CommunicationLog, 
    HospitalPreparationChecklist,
    FirstAiderAssessment,
    PatientAssessment
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
    emergency_alert_id = serializers.CharField(
        write_only=True,
        max_length=50,  # Add max_length
        error_messages={
            'invalid': 'Must be a valid alert ID.'
        }
    )
    
    class Meta:
        model = EmergencyHospitalCommunication
        fields = [
            'emergency_alert_id', 'hospital', 'first_aider', 'priority',
            'victim_name', 'victim_age', 'victim_gender', 'chief_complaint',
            'vital_signs', 'first_aid_provided',
            'estimated_arrival_minutes', 'required_specialties', 'equipment_needed',
            'blood_type_required'
        ]
    
    def validate_emergency_alert_id(self, value):  # Fixed method name
        """Validate that the emergency alert exists"""
        try:
            # Check what field stores your auto-generated IDs in EmergencyAlert
            # If it's 'alert_id', use: EmergencyAlert.objects.get(alert_id=value)
            # If it's 'emergency_alert_id', use: EmergencyAlert.objects.get(emergency_alert_id=value)
            EmergencyAlert.objects.get(alert_id=value)  # Adjust this field name as needed
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
        
        # Get the actual EmergencyAlert object to use its UUID
        try:
            alert = EmergencyAlert.objects.get(alert_id=emergency_alert_id)  # Adjust field name
        except EmergencyAlert.DoesNotExist:
            raise serializers.ValidationError("Emergency alert not found")
        
        communication = EmergencyHospitalCommunication.objects.create(
            emergency_alert_id=alert.id,  # Use the UUID ID, not the string
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


class PatientAssessmentSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    blood_pressure = serializers.ReadOnlyField()
    priority_level = serializers.ReadOnlyField()
    
    class Meta:
        model = PatientAssessment
        fields = '__all__'
        read_only_fields = ('communication', 'created_at', 'updated_at', 'gcs_total')
    
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
    
    def validate_heart_rate(self, value):
        if value and (value < 30 or value > 250):
            raise serializers.ValidationError("Heart rate must be between 30 and 250 BPM")
        return value
    
    def validate_temperature(self, value):
        if value and (value < 30 or value > 45):
            raise serializers.ValidationError("Temperature must be between 30 and 45°C")
        return value

class EmergencyHospitalCommunicationDetailSerializer(serializers.ModelSerializer):
    """Enhanced detailed serializer with patient assessment"""
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    hospital_address = serializers.CharField(source='hospital.address', read_only=True)
    hospital_phone = serializers.CharField(source='hospital.phone', read_only=True)
    first_aider_name = serializers.CharField(source='first_aider.get_full_name', read_only=True)
    first_aider_phone = serializers.CharField(source='first_aider.phone', read_only=True)
    
    # Nested serializers - UPDATED to include patient assessment
    first_aider_assessment = FirstAiderAssessmentSerializer(read_only=True)
    patient_assessment = PatientAssessmentSerializer(read_only=True)  # NEW
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
        # Use role instead of role
        queryset=User.objects.filter(role='hospital_staff')
    )
    preparation_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_acknowledged_by(self, value):
        # Use role instead of role
        if value.role != 'hospital_staff':
            raise serializers.ValidationError("User must be a hospital staff")
        return value

class HospitalPreparationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating preparation status - different fields for different roles"""
    
    class Meta:
        model = EmergencyHospitalCommunication
        fields = [
            # Hospital staff fields
            'doctors_ready', 'nurses_ready', 'equipment_ready', 'bed_ready',
            'blood_available', 'hospital_preparation_notes',
            # First aider fields
            'first_aid_provided', 'vital_signs', 'estimated_arrival_minutes'
        ]
    
    def validate(self, data):
        """
        Validate based on user role
        """
        user_role = self.context.get('user_role')
        
        if user_role == 'first_aider':
            # First aider cannot update hospital preparation fields
            hospital_fields = ['doctors_ready', 'nurses_ready', 'equipment_ready', 
                              'bed_ready', 'blood_available', 'hospital_preparation_notes']
            for field in hospital_fields:
                if field in data:
                    raise serializers.ValidationError(
                        f"First aiders cannot update hospital preparation field: {field}"
                    )
        
        elif user_role == 'hospital_staff':
            # Hospital staff cannot update first aider fields
            first_aider_fields = ['first_aid_provided', 'vital_signs', 'estimated_arrival_minutes']
            for field in first_aider_fields:
                if field in data:
                    raise serializers.ValidationError(
                        f"Hospital staff cannot update first aider field: {field}"
                    )
        
        return data
    
    
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
    
class PatientAssessmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAssessment
        exclude = ('communication', 'created_at', 'updated_at', 'gcs_total')
    
    def validate(self, data):
        # Validate GCS components if provided
        gcs_fields = ['gcs_eyes', 'gcs_verbal', 'gcs_motor']
        provided_gcs = [data.get(field) for field in gcs_fields if data.get(field) is not None]
        
        if len(provided_gcs) > 0 and len(provided_gcs) < 3:
            raise serializers.ValidationError(
                "All GCS components (eyes, verbal, motor) must be provided together"
            )
        
        # Validate blood pressure components
        bp_systolic = data.get('blood_pressure_systolic')
        bp_diastolic = data.get('blood_pressure_diastolic')
        
        if (bp_systolic and not bp_diastolic) or (bp_diastolic and not bp_systolic):
            raise serializers.ValidationError(
                "Both systolic and diastolic blood pressure must be provided together"
            )
        
        return data


