from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Notification,
    NotificationTemplate,
    SMSLog,
    PushNotificationLog,
    EmailLog,
    UserNotificationPreference
)

User = get_user_model()

class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'role', 'title', 'message',
            'notification_type', 'priority', 'channel', 'status',
            'emergency_alert', 'hospital_communication', 'metadata',
            'created_at', 'sent_at', 'delivered_at', 'read_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'sent_at', 'delivered_at', 'read_at'
        ]

class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'user', 'title', 'message', 'notification_type', 'priority',
            'channel', 'emergency_alert', 'hospital_communication', 'metadata'
        ]
    
    def validate_user(self, value):
        """Ensure user can receive notifications"""
        if not value.is_active:
            raise serializers.ValidationError("User is not active")
        return value
    
    def validate_channel(self, value):
        """Validate channel based on user preferences"""
        # Get the user instance that was already validated
        user = None
        
        # Try to get user from different sources
        if hasattr(self, '_validated_data') and 'user' in self._validated_data:
            user = self._validated_data['user']
        elif 'user' in self.initial_data:
            user_id = self.initial_data['user']
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise serializers.ValidationError("User does not exist")
        
        if user:
            # Get or create user preferences
            preferences, created = UserNotificationPreference.objects.get_or_create(
                user=user,
                defaults={
                    'email_enabled': True,
                    'sms_enabled': True,
                    'push_enabled': True,
                    'voice_enabled': True
                }
            )
            
            channel_field = f"{value}_enabled"
            if not getattr(preferences, channel_field, False):
                raise serializers.ValidationError(
                    f"User has disabled {value} notifications"
                )
        
        return value

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationPreference
        fields = '__all__'
        read_only_fields = ['user', 'updated_at']
    
    def validate_quiet_hours(self, data):
        """Validate quiet hours configuration"""
        if data.get('quiet_hours_enabled'):
            start = data.get('quiet_hours_start')
            end = data.get('quiet_hours_end')
            
            if not start or not end:
                raise serializers.ValidationError(
                    "Both start and end times are required for quiet hours"
                )
            
            if start == end:
                raise serializers.ValidationError(
                    "Quiet hours start and end times cannot be the same"
                )
        
        return data

class SMSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSLog
        fields = '__all__'
        read_only_fields = ['id', 'sent_at']

class PushNotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushNotificationLog
        fields = '__all__'
        read_only_fields = ['id', 'sent_at']

class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = '__all__'
        read_only_fields = ['id', 'sent_at']

class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for sending bulk notifications"""
    users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True
    )
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(
        choices=Notification.NOTIFICATION_TYPES
    )
    channel = serializers.ChoiceField(
        choices=Notification.CHANNEL_CHOICES
    )
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='medium'
    )
    metadata = serializers.JSONField(required=False, default=dict)

class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    total_sent = serializers.IntegerField()
    total_delivered = serializers.IntegerField()
    total_failed = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    average_delivery_time = serializers.FloatField()
    channel_breakdown = serializers.JSONField()
    type_breakdown = serializers.JSONField()