from rest_framework import serializers
from .models import Verification
from accounts.serializers import UserProfileSerializer, OrganizationSerializer
from hospitals.serializers import HospitalSerializer

class VerificationSerializer(serializers.ModelSerializer):
    entity_name = serializers.SerializerMethodField()
    entity_email = serializers.SerializerMethodField()
    entity_phone = serializers.SerializerMethodField()
    entity_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Verification
        fields = [
            'id', 'verification_type', 'status', 'submitted_data',
            'entity_name', 'entity_email', 'entity_phone', 'entity_details',
            'reviewed_by', 'reviewed_at', 'review_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_entity_name(self, obj):
        return obj.get_entity_name()
    
    def get_entity_email(self, obj):
        return obj.get_entity_email()
    
    def get_entity_phone(self, obj):
        if obj.user:
            return obj.user.phone
        elif obj.hospital:
            return obj.hospital.phone
        elif obj.organization:
            return obj.organization.phone
        return None
    
    def get_entity_details(self, obj):
        if obj.user:
            return {
                'role': obj.user.role,
                'badge_number': obj.user.badge_number,
                'is_active': obj.user.is_active,
                'is_email_verified': obj.user.is_email_verified
            }
        elif obj.hospital:
            return {
                'hospital_type': obj.hospital.hospital_type,
                'level': obj.hospital.level,
                'is_operational': obj.hospital.is_operational
            }
        elif obj.organization:
            return {
                'organization_type': obj.organization.organization_type,
                'is_active': obj.organization.is_active,
                'is_verified': obj.organization.is_verified
            }
        return {}

class VerificationActionSerializer(serializers.Serializer):
    verification_type = serializers.CharField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    request = serializers.CharField(required=False, allow_blank=True)

class VerificationStatsSerializer(serializers.Serializer):
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    total = serializers.IntegerField()