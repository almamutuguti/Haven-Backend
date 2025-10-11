from rest_framework import serializers
from .models import (
    MedicalProfile, MedicalCondition, Allergy, Medication,
    EmergencyContact, InsuranceInformation, SurgicalHistory, MedicalDocument
)


class MedicalConditionSerializer(serializers.ModelSerializer):
    """Serializer for Medical Condition model"""
    
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MedicalCondition
        fields = [
            'id', 'name', 'diagnosis_date', 'severity', 'severity_display',
            'status', 'status_display', 'icd_code', 'description',
            'is_chronic', 'is_critical', 'treatment_plan', 'specialist',
            'specialist_contact', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AllergySerializer(serializers.ModelSerializer):
    """Serializer for Allergy model"""
    
    allergy_type_display = serializers.CharField(source='get_allergy_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = Allergy
        fields = [
            'id', 'allergen', 'allergy_type', 'allergy_type_display', 'severity', 'severity_display',
            'reaction', 'onset_time', 'treatment', 'epi_pen_required', 'diagnosed_by',
            'diagnosis_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MedicationSerializer(serializers.ModelSerializer):
    """Serializer for Medication model"""
    
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Medication
        fields = [
            'id', 'name', 'dosage', 'frequency', 'frequency_display', 'custom_frequency',
            'prescribing_doctor', 'prescription_date', 'purpose', 'status', 'status_display',
            'start_date', 'end_date', 'instructions', 'with_food', 'avoid_alcohol',
            'is_critical', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Serializer for Emergency Contact model"""
    
    relationship_display = serializers.CharField(source='get_relationship_display', read_only=True)
    
    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'full_name', 'relationship', 'relationship_display', 'phone_number',
            'alternate_phone', 'email', 'address', 'is_primary',
            'can_make_medical_decisions', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InsuranceInformationSerializer(serializers.ModelSerializer):
    """Serializer for Insurance Information model"""
    
    verification_status_display = serializers.CharField(
        source='get_verification_status_display', 
        read_only=True
    )
    
    class Meta:
        model = InsuranceInformation
        fields = [
            'id', 'insurance_provider', 'policy_number', 'group_number', 'plan_type',
            'provider_phone', 'provider_website', 'is_active', 'effective_date',
            'expiry_date', 'emergency_coverage', 'coverage_notes', 'verification_status',
            'verification_status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SurgicalHistorySerializer(serializers.ModelSerializer):
    """Serializer for Surgical History model"""
    
    class Meta:
        model = SurgicalHistory
        fields = [
            'id', 'procedure_name', 'date_performed', 'surgeon', 'hospital',
            'reason', 'complications', 'outcome', 'has_implants', 'implant_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MedicalDocumentSerializer(serializers.ModelSerializer):
    """Serializer for Medical Document model"""
    
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    access_level_display = serializers.CharField(source='get_access_level_display', read_only=True)
    file_url = serializers.FileField(source='file', read_only=True)
    
    class Meta:
        model = MedicalDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'title', 'description',
            'file', 'file_url', 'file_name', 'file_size', 'issue_date', 'expiry_date',
            'issuing_authority', 'is_encrypted', 'access_level', 'access_level_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'file_name', 'file_size', 'created_at', 'updated_at']


class MedicalProfileSerializer(serializers.ModelSerializer):
    """Serializer for Medical Profile model"""
    
    blood_type_display = serializers.CharField(source='get_blood_type_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    bmi = serializers.FloatField(read_only=True)
    
    # Nested serializers for related data
    conditions = MedicalConditionSerializer(many=True, read_only=True)
    allergies = AllergySerializer(many=True, read_only=True)
    medications = MedicationSerializer(many=True, read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    insurance_info = InsuranceInformationSerializer(many=True, read_only=True)
    surgical_history = SurgicalHistorySerializer(many=True, read_only=True)
    documents = MedicalDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = MedicalProfile
        fields = [
            'id', 'user', 'user_email', 'user_name', 'blood_type', 'blood_type_display',
            'height_cm', 'weight_kg', 'age', 'bmi', 'organ_donor', 'dnr_order',
            'advance_directive', 'primary_care_physician', 'physician_phone',
            'data_consent_given', 'consent_given_at', 'data_sharing_preferences',
            'last_medical_review', 'created_at', 'updated_at',
            'conditions', 'allergies', 'medications', 'emergency_contacts',
            'insurance_info', 'surgical_history', 'documents'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at', 'consent_given_at',
            'conditions', 'allergies', 'medications', 'emergency_contacts',
            'insurance_info', 'surgical_history', 'documents'
        ]


class MedicalProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating medical profile"""
    
    class Meta:
        model = MedicalProfile
        fields = [
            'blood_type', 'height_cm', 'weight_kg', 'organ_donor', 'dnr_order',
            'advance_directive', 'primary_care_physician', 'physician_phone',
            'data_consent_given', 'data_sharing_preferences', 'last_medical_review'
        ]
    
    def validate_height_cm(self, value):
        if value and not (50 <= value <= 250):
            raise serializers.ValidationError("Height must be between 50cm and 250cm")
        return value
    
    def validate_weight_kg(self, value):
        if value and not (2 <= value <= 500):
            raise serializers.ValidationError("Weight must be between 2kg and 500kg")
        return value


class MedicalProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating medical profile"""
    
    class Meta:
        model = MedicalProfile
        fields = [
            'blood_type', 'height_cm', 'weight_kg', 'organ_donor', 'dnr_order',
            'advance_directive', 'primary_care_physician', 'physician_phone',
            'data_sharing_preferences', 'last_medical_review'
        ]
    
    def validate_height_cm(self, value):
        if value and not (50 <= value <= 250):
            raise serializers.ValidationError("Height must be between 50cm and 250cm")
        return value
    
    def validate_weight_kg(self, value):
        if value and not (2 <= value <= 500):
            raise serializers.ValidationError("Weight must be between 2kg and 500kg")
        return value


class MedicalConditionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating medical condition"""
    
    class Meta:
        model = MedicalCondition
        fields = [
            'name', 'diagnosis_date', 'severity', 'status', 'icd_code', 'description',
            'is_chronic', 'is_critical', 'treatment_plan', 'specialist', 'specialist_contact'
        ]


class AllergyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating allergy"""
    
    class Meta:
        model = Allergy
        fields = [
            'allergen', 'allergy_type', 'severity', 'reaction', 'onset_time',
            'treatment', 'epi_pen_required', 'diagnosed_by', 'diagnosis_date'
        ]


class MedicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating medication"""
    
    class Meta:
        model = Medication
        fields = [
            'name', 'dosage', 'frequency', 'custom_frequency', 'prescribing_doctor',
            'prescription_date', 'purpose', 'status', 'start_date', 'end_date',
            'instructions', 'with_food', 'avoid_alcohol', 'is_critical'
        ]


class EmergencyContactCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating emergency contact"""
    
    class Meta:
        model = EmergencyContact
        fields = [
            'full_name', 'relationship', 'phone_number', 'alternate_phone', 'email',
            'address', 'is_primary', 'can_make_medical_decisions', 'notes'
        ]


class InsuranceInformationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating insurance information"""
    
    class Meta:
        model = InsuranceInformation
        fields = [
            'insurance_provider', 'policy_number', 'group_number', 'plan_type',
            'provider_phone', 'provider_website', 'is_active', 'effective_date',
            'expiry_date', 'emergency_coverage', 'coverage_notes'
        ]


class SurgicalHistoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating surgical history"""
    
    class Meta:
        model = SurgicalHistory
        fields = [
            'procedure_name', 'date_performed', 'surgeon', 'hospital', 'reason',
            'complications', 'outcome', 'has_implants', 'implant_details'
        ]


class EmergencyDataPacketSerializer(serializers.Serializer):
    """Serializer for emergency data packet response"""
    
    patient_info = serializers.DictField()
    critical_information = serializers.DictField()


class FHIRDataSerializer(serializers.Serializer):
    """Serializer for FHIR-compliant data response"""
    
    resource_type = serializers.CharField()
    type = serializers.CharField()
    timestamp = serializers.DateTimeField()
    entry = serializers.ListField(child=serializers.DictField())


class EmergencySummarySerializer(serializers.Serializer):
    """Serializer for emergency summary response"""
    
    patient_summary = serializers.DictField()
    critical_alerts = serializers.DictField()
    emergency_contacts = serializers.ListField(child=serializers.DictField())
    last_updated = serializers.DateTimeField()