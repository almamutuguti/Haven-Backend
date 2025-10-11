from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser as User


class Location(models.Model):
    """
    Store geographical locations with coordinates and address information
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='locations',
        null=True, 
        blank=True
    )
    
    # Coordinates
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90)
        ]
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180)
        ]
    )
    
    # Address components
    formatted_address = models.TextField(blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Kenya')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Metadata
    is_primary = models.BooleanField(default=False)
    location_type = models.CharField(
        max_length=20,
        choices=[
            ('home', 'Home'),
            ('work', 'Work'),
            ('emergency', 'Emergency'),
            ('current', 'Current Location'),
            ('other', 'Other')
        ],
        default='current'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'geolocation_locations'
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['user', 'is_primary']),
        ]
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"{self.latitude}, {self.longitude} - {self.formatted_address}"


class HospitalLocation(models.Model):
    """
    Extended location model specifically for hospitals with additional emergency-related fields
    """
    location = models.OneToOneField(
        Location,
        on_delete=models.CASCADE,
        related_name='hospital_location'
    )
    
    # Hospital-specific location data
    place_id = models.CharField(max_length=255, unique=True, blank=True)
    google_maps_url = models.URLField(blank=True)
    accessibility_notes = models.TextField(blank=True)
    entrance_instructions = models.TextField(blank=True)
    
    # Emergency service accessibility
    has_ambulance_bay = models.BooleanField(default=False)
    emergency_entrance_coordinates = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'geolocation_hospital_locations'
    
    def __str__(self):
        return f"Hospital Location: {self.location.formatted_address}"


