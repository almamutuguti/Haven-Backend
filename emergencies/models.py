from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser as User
from geolocation.models import Location


class EmergencyAlert(models.Model):
    """
    Core model for emergency alerts and their lifecycle
    """
    ALERT_PRIORITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    ALERT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('dispatched', 'Dispatched'),
        ('hospital_selected', 'Hospital Selected'),
        ('en_route', 'En Route to Hospital'),
        ('arrived', 'Arrived at Hospital'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    EMERGENCY_TYPE_CHOICES = [
        ('medical', 'Medical Emergency'),
        ('accident', 'Accident'),
        ('cardiac', 'Cardiac Arrest'),
        ('trauma', 'Trauma'),
        ('respiratory', 'Respiratory Distress'),
        ('pediatric', 'Pediatric Emergency'),
        ('other', 'Other'),
    ]

    # Core alert information
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='emergency_alerts'
    )
    alert_id = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Emergency details
    emergency_type = models.CharField(
        max_length=20, 
        choices=EMERGENCY_TYPE_CHOICES, 
        default='medical'
    )
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10, 
        choices=ALERT_PRIORITY_CHOICES, 
        default='medium'
    )
    
    # Location information
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_alerts'
    )
    current_latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    current_longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    address = models.TextField(blank=True)
    
    # Status and timing
    status = models.CharField(
        max_length=20, 
        choices=ALERT_STATUS_CHOICES, 
        default='pending'
    )
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Verification
    verification_attempts = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'emergency_alerts'
        indexes = [
            models.Index(fields=['alert_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Emergency {self.alert_id} - {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.alert_id:
            self.alert_id = self.generate_alert_id()
        super().save(*args, **kwargs)

    def generate_alert_id(self):
        import random
        import string
        from django.utils import timezone
        
        timestamp = timezone.now().strftime('%Y%m%d%H%M')
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"EMG{timestamp}{random_chars}"


class EmergencySession(models.Model):
    """
    Track active emergency sessions for real-time management
    """
    alert = models.OneToOneField(
        EmergencyAlert,
        on_delete=models.CASCADE,
        related_name='session'
    )
    
    # Session management
    session_id = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    
    # Real-time tracking
    last_location_update = models.DateTimeField(auto_now=True)
    location_updates_count = models.PositiveIntegerField(default=0)
    
    # Communication
    websocket_channel = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'emergency_sessions'
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Session {self.session_id} for {self.alert.alert_id}"


class AlertVerification(models.Model):
    """
    Track emergency alert verification attempts
    """
    alert = models.ForeignKey(
        EmergencyAlert,
        on_delete=models.CASCADE,
        related_name='verifications'
    )
    
    # Verification methods
    verification_method = models.CharField(
        max_length=20,
        choices=[
            ('call', 'Phone Call'),
            ('sms', 'SMS'),
            ('push', 'Push Notification'),
            ('auto', 'Automatic'),
        ],
        default='auto'
    )
    
    # Verification details
    verification_code = models.CharField(max_length=10, blank=True)
    is_successful = models.BooleanField(default=False)
    response_received = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'alert_verifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"Verification for {self.alert.alert_id}"


class EmergencyUpdate(models.Model):
    """
    Track all updates and state changes for an emergency alert
    """
    alert = models.ForeignKey(
        EmergencyAlert,
        on_delete=models.CASCADE,
        related_name='updates'
    )
    
    # Update information
    update_type = models.CharField(
        max_length=30,
        choices=[
            ('created', 'Alert Created'),
            ('verified', 'Alert Verified'),
            ('location_updated', 'Location Updated'),
            ('status_changed', 'Status Changed'),
            ('hospital_assigned', 'Hospital Assigned'),
            ('ambulance_dispatched', 'Ambulance Dispatched'),
            ('eta_updated', 'ETA Updated'),
            ('cancelled', 'Alert Cancelled'),
            ('completed', 'Alert Completed'),
        ]
    )
    
    # Update details
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    details = models.JSONField(default=dict)  # Store additional update data
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'emergency_updates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert', 'created_at']),
        ]

    def __str__(self):
        return f"Update {self.update_type} for {self.alert.alert_id}"