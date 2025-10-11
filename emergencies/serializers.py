from rest_framework import serializers
from .models import EmergencyAlert, EmergencySession, AlertVerification, EmergencyUpdate


class EmergencyAlertSerializer(serializers.ModelSerializer):
    """Serializer for Emergency Alert model"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = EmergencyAlert
        fields = [
            'alert_id', 'user', 'user_email', 'user_name', 'emergency_type',
            'description', 'priority', 'status', 'is_active', 'is_verified',
            'current_latitude', 'current_longitude', 'address',
            'verification_attempts', 'created_at', 'updated_at',
            'verified_at', 'dispatched_at', 'completed_at', 'cancelled_at'
        ]
        read_only_fields = [
            'alert_id', 'user', 'status', 'is_active', 'is_verified',
            'verification_attempts', 'created_at', 'updated_at',
            'verified_at', 'dispatched_at', 'completed_at', 'cancelled_at'
        ]
    
    def validate_emergency_type(self, value):
        valid_types = [choice[0] for choice in EmergencyAlert.EMERGENCY_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Emergency type must be one of: {valid_types}")
        return value
    
    def validate_priority(self, value):
        valid_priorities = [choice[0] for choice in EmergencyAlert.ALERT_PRIORITY_CHOICES]
        if value not in valid_priorities:
            raise serializers.ValidationError(f"Priority must be one of: {valid_priorities}")
        return value


class EmergencyAlertCreateSerializer(serializers.Serializer):
    """Serializer for creating emergency alerts"""
    
    emergency_type = serializers.ChoiceField(
        choices=EmergencyAlert.EMERGENCY_TYPE_CHOICES,
        default='medical'
    )
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    location_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class LocationUpdateSerializer(serializers.Serializer):
    """Serializer for updating emergency alert location"""
    
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    address = serializers.CharField(required=False, allow_blank=True)
    
    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class AlertStatusSerializer(serializers.Serializer):
    """Serializer for alert status updates"""
    
    status = serializers.ChoiceField(
        choices=EmergencyAlert.ALERT_STATUS_CHOICES,
        required=True
    )
    details = serializers.JSONField(required=False, default=dict)


class AlertVerificationSerializer(serializers.ModelSerializer):
    """Serializer for alert verification"""
    
    class Meta:
        model = AlertVerification
        fields = [
            'id', 'verification_method', 'verification_code',
            'is_successful', 'response_received', 'created_at', 'responded_at'
        ]
        read_only_fields = ['id', 'created_at', 'responded_at']


class EmergencyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for emergency updates"""
    
    created_by_email = serializers.EmailField(
        source='created_by.email', 
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = EmergencyUpdate
        fields = [
            'id', 'update_type', 'previous_status', 'new_status',
            'details', 'created_by', 'created_by_email', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmergencySessionSerializer(serializers.ModelSerializer):
    """Serializer for emergency sessions"""
    
    class Meta:
        model = EmergencySession
        fields = [
            'session_id', 'is_active', 'last_location_update',
            'location_updates_count', 'websocket_channel',
            'created_at', 'ended_at'
        ]
        read_only_fields = ['session_id', 'created_at', 'ended_at']


class VerificationCodeSerializer(serializers.Serializer):
    """Serializer for verification code submission"""
    
    verification_code = serializers.CharField(
        max_length=6,
        min_length=6,
        required=True
    )
    
    def validate_verification_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Verification code must contain only digits")
        return value


class CancelEmergencySerializer(serializers.Serializer):
    """Serializer for emergency cancellation"""
    
    reason = serializers.CharField(required=False, allow_blank=True)