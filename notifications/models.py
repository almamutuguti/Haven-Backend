import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    """
    Central notification system for the Haven platform
    """
    PRIORITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]
    
    CHANNEL_CHOICES = [
        ('push', 'Push Notification'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('in_app', 'In-App Notification'),
        ('voice', 'Voice Call'),
    ]
    
    NOTIFICATION_TYPES = [
        ('emergency_alert', 'Emergency Alert'),
        ('hospital_assignment', 'Hospital Assignment'),
        ('first_aider_dispatch', 'First Aider Dispatch'),
        ('eta_update', 'ETA Update'),
        ('hospital_ready', 'Hospital Ready'),
        ('patient_arrived', 'Patient Arrived'),
        ('system_alert', 'System Alert'),
        ('test', 'Test Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification content
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Delivery information
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    retry_count = models.PositiveIntegerField(default=0)
    
    # Related objects (for context)
    emergency_alert = models.ForeignKey(
        'emergencies.EmergencyAlert',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    hospital_communication = models.ForeignKey(
        'hospital_communication.EmergencyHospitalCommunication',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['notification_type', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['scheduled_for']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.user} ({self.status})"
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()

class NotificationTemplate(models.Model):
    """
    Reusable templates for different types of notifications
    """
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.CharField(max_length=50, choices=Notification.NOTIFICATION_TYPES)
    channel = models.CharField(max_length=20, choices=Notification.CHANNEL_CHOICES)
    
    # Template content
    title_template = models.CharField(max_length=255)
    message_template = models.TextField()
    priority = models.CharField(max_length=20, choices=Notification.PRIORITY_CHOICES, default='medium')
    
    # Variables help text
    variables_help = models.TextField(blank=True, help_text="Available template variables")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
    
    def __str__(self):
        return f"{self.name} ({self.channel})"

class SMSLog(models.Model):
    """
    Track SMS notifications and delivery status
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='sms_log'
    )
    
    # SMS specific fields
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    message_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Provider information
    provider = models.CharField(max_length=50, default='africas_talking')
    provider_message_id = models.CharField(max_length=100, blank=True)
    
    # Delivery status
    status = models.CharField(max_length=50, default='sent')
    delivery_status = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Cost tracking
    cost = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    currency = models.CharField(max_length=3, default='KES')
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'sms_logs'
        indexes = [
            models.Index(fields=['phone_number', 'sent_at']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        return f"SMS to {self.phone_number} - {self.status}"

class PushNotificationLog(models.Model):
    """
    Track push notifications and delivery status
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='push_log'
    )
    
    # Push specific fields
    device_token = models.CharField(max_length=255, db_index=True)
    platform = models.CharField(max_length=20, choices=[('ios', 'iOS'), ('android', 'Android')])
    
    # Push payload
    payload = models.JSONField(default=dict)
    
    # Delivery status
    status = models.CharField(max_length=50, default='sent')
    error_message = models.TextField(blank=True)
    failure_reason = models.CharField(max_length=100, blank=True)
    
    # Provider information
    provider_message_id = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'push_notification_logs'
    
    def __str__(self):
        return f"Push to {self.platform} - {self.status}"

class EmailLog(models.Model):
    """
    Track email notifications and delivery status
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='email_log'
    )
    
    # Email specific fields
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    
    # Delivery status
    status = models.CharField(max_length=50, default='sent')
    provider_message_id = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'email_logs'
    
    def __str__(self):
        return f"Email to {self.recipient} - {self.status}"

class UserNotificationPreference(models.Model):
    """
    User preferences for notification channels and types
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Channel preferences
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    voice_enabled = models.BooleanField(default=True)
    
    # Emergency notification preferences
    emergency_push = models.BooleanField(default=True)
    emergency_sms = models.BooleanField(default=True)
    emergency_voice = models.BooleanField(default=True)
    
    # Update preferences
    eta_updates = models.BooleanField(default=True)
    hospital_updates = models.BooleanField(default=True)
    system_alerts = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    quiet_hours_enabled = models.BooleanField(default=False)
    
    # Rate limiting
    max_notifications_per_hour = models.PositiveIntegerField(default=10)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_notification_preferences'
    
    def __str__(self):
        return f"Preferences for {self.user}"
    
    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        return self.quiet_hours_start <= now <= self.quiet_hours_end