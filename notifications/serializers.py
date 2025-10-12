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
    user_type = serializers.CharField(source='user.user_type', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'user_type', 'title', 'message',
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
        user = self.initial_data.get('user')
        if user:
            try:
                preferences = user.notification_preferences
                channel_field = f"{value}_enabled"
                if not getattr(preferences, channel_field, False):
                    raise serializers.ValidationError(
                        f"User has disabled {value} notifications"
                    )
            except UserNotificationPreference.DoesNotExist:
                # Use default preferences if none exist
                pass
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