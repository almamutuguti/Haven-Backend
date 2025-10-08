from rest_framework import serializers
from django.utils import timezone
from .models import EmergencyAlert, EmergencyStatusUpdate, EmergencyLocationUpdate

class EmergencyAlertSerializer(serializers.ModelSerializer):
    first_aider_name = serializers.CharField(source='first_aider.get_full_name', read_only=True)
    first_aider_badge = serializers.CharField(source='first_aider.badge_number', read_only=True)
    
    class Meta:
        model = EmergencyAlert
        fields = (
            'id', 'first_aider', 'first_aider_name', 'first_aider_badge',
            'priority', 'status', 'patient_name', 'patient_age', 'patient_gender',
            'emergency_type', 'condition_description', 'latitude', 'longitude', 'address',
            'vital_signs', 'allergies', 'medications_given', 'symptoms', 'assigned_hospital_name',
            'created_at', 'updated_at', 'dispatched_at', 'arrived_at', 'completed_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'dispatched_at', 'arrived_at', 'completed_at')
    
    def validate(self, data):
        request = self.context.get('request')
        if request and request.user.user_type != 'first_aider':
            raise serializers.ValidationError("Only first aiders can create emergencies.")
        
        if data.get('patient_age', 0) > 150:
            raise serializers.ValidationError("Patient age must be realistic.")
        
        return data

class EmergencyStatusUpdateSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_badge = serializers.CharField(source='user.badge_number', read_only=True)
    
    class Meta:
        model = EmergencyStatusUpdate
        fields = ('id', 'emergency', 'user', 'user_name', 'user_badge', 'status', 'notes', 'created_at')
        read_only_fields = ('id', 'created_at')

class EmergencyLocationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyLocationUpdate
        fields = ('id', 'emergency', 'latitude', 'longitude', 'created_at')
        read_only_fields = ('id', 'created_at')

class EmergencyAlertCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating emergencies quickly"""
    class Meta:
        model = EmergencyAlert
        fields = (
            'priority', 'patient_name', 'patient_age', 'patient_gender',
            'emergency_type', 'condition_description', 'latitude', 'longitude', 'address',
            'vital_signs', 'allergies', 'medications_given', 'symptoms'
        )
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['first_aider'] = request.user
        return super().create(validated_data)

class EmergencyAlertStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating emergency status"""
    class Meta:
        model = EmergencyAlert
        fields = ('status', 'notes')
    
    def update(self, instance, validated_data):
        new_status = validated_data.get('status')
        notes = validated_data.get('notes', '')
        
        # Create status update record
        EmergencyStatusUpdate.objects.create(
            emergency=instance,
            user=self.context['request'].user,
            status=new_status,
            notes=notes
        )
        
        # Update timestamps based on status
        if new_status == 'dispatched' and not instance.dispatched_at:
            instance.dispatched_at = timezone.now()
        elif new_status == 'arrived' and not instance.arrived_at:
            instance.arrived_at = timezone.now()
        elif new_status == 'completed' and not instance.completed_at:
            instance.completed_at = timezone.now()
        
        instance.status = new_status
        instance.save()
        
        return instance

class EmergencyLocationSerializer(serializers.ModelSerializer):
    """Serializer for updating emergency location"""
    class Meta:
        model = EmergencyLocationUpdate
        fields = ('latitude', 'longitude')
    
    def create(self, validated_data):
        request = self.context.get('request')
        emergency_id = self.context.get('emergency_id')
        
        from .models import EmergencyAlert
        emergency = EmergencyAlert.objects.get(id=emergency_id)
        
        if request.user != emergency.first_aider:
            raise serializers.ValidationError("You can only update locations for your own emergencies.")
        
        validated_data['emergency'] = emergency
        return super().create(validated_data)