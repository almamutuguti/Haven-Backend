import uuid
from django.db import models
from accounts.models import CustomUser  # Import from accounts app



class EmergencyAlert(models.Model):
    PRIORITY_LEVELS = (
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('dispatched', 'Dispatched'),
        ('en_route', 'En Route'),
        ('arrived', 'Arrived'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    
    EMERGENCY_TYPES = (
        ('cardiac', 'Cardiac Arrest'),
        ('trauma', 'Trauma'),
        ('respiratory', 'Respiratory Distress'),
        ('stroke', 'Stroke'),
        ('seizure', 'Seizure'),
        ('allergic', 'Allergic Reaction'),
        ('burn', 'Burn'),
        ('poisoning', 'Poisoning'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_aider = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='emergencies')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Patient information (collected by first aider)
    patient_name = models.CharField(max_length=100)
    patient_age = models.PositiveIntegerField()
    patient_gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    
    # Emergency details
    emergency_type = models.CharField(max_length=50, choices=EMERGENCY_TYPES)
    condition_description = models.TextField()
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField(blank=True)
    
    # Medical information
    vital_signs = models.JSONField(default=dict, blank=True)
    allergies = models.TextField(blank=True)
    medications_given = models.TextField(blank=True)
    symptoms = models.TextField(blank=True)
    
    # Hospital assignment
    assigned_hospital_name = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'emergency_alerts'
    
    def __str__(self):
        return f"Emergency {self.id} - {self.patient_name} ({self.priority})"

class EmergencyStatusUpdate(models.Model):
    emergency = models.ForeignKey(EmergencyAlert, on_delete=models.CASCADE, related_name='status_updates')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=EmergencyAlert.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'emergency_status_updates'
    
    def __str__(self):
        return f"Status update for {self.emergency.id}: {self.status}"

class EmergencyLocationUpdate(models.Model):
    emergency = models.ForeignKey(EmergencyAlert, on_delete=models.CASCADE, related_name='location_updates')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'emergency_location_updates'
    
    def __str__(self):
        return f"Location update for {self.emergency.id}"