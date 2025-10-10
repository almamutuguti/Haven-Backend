from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User


class Location(models.Model):
    """
    Generic location model that can be used by any app
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='locations'
    )
    name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)  # Kenya-specific
    country = models.CharField(max_length=100, default='Kenya')
    
    # GPS coordinates using PostGIS
    coordinates = gis_models.PointField(
        geography=True,
        blank=True,
        null=True,
        help_text="Longitude/Latitude Point"
    )
    
    # Accuracy metadata
    accuracy = models.FloatField(
        null=True, 
        blank=True,
        help_text="GPS accuracy in meters"
    )
    altitude = models.FloatField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    timestamp = models.DateTimeField(
        help_text="When this location was recorded"
    )
    
    # Source of location data
    SOURCE_CHOICES = [
        ('gps', 'GPS'),
        ('network', 'Network'),
        ('manual', 'Manual Entry'),
        ('emergency', 'Emergency Alert'),
    ]
    source = models.CharField(
        max_length=20, 
        choices=SOURCE_CHOICES, 
        default='gps'
    )
    
    # For emergency context
    emergency_alert = models.ForeignKey(
        'emergencies.EmergencyAlert',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locations'
    )
    
    class Meta:
        db_table = 'geolocation_locations'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['timestamp']),
            gis_models.Index(fields=['coordinates']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        if self.user:
            return f"{self.user.email} - {self.timestamp}"
        return f"Location {self.id} - {self.timestamp}"
    
    @property
    def latitude(self):
        return self.coordinates.y if self.coordinates else None
    
    @property
    def longitude(self):
        return self.coordinates.x if self.coordinates else None
    
    def to_geojson(self):
        """Convert location to GeoJSON format"""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude]
            },
            "properties": {
                "id": self.id,
                "name": self.name,
                "address": self.address,
                "timestamp": self.timestamp.isoformat(),
                "accuracy": self.accuracy
            }
        }


class GeoFence(models.Model):
    """
    Define geographical boundaries for hospitals, zones, etc.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Polygon defining the geofence boundary
    boundary = gis_models.PolygonField()
    
    # Geofence type
    TYPE_CHOICES = [
        ('hospital', 'Hospital Zone'),
        ('emergency', 'Emergency Zone'),
        ('restricted', 'Restricted Area'),
        ('custom', 'Custom Zone'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='custom')
    
    # Associated hospital (if applicable)
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='geofences'
    )
    
    radius = models.FloatField(
        null=True,
        blank=True,
        help_text="Radius in meters for circular geofences"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'geolocation_geofences'
    
    def __str__(self):
        return f"{self.name} ({self.type})"


class LocationLog(models.Model):
    """
    Audit log for location changes and queries
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    action = models.CharField(max_length=50)  # 'create', 'update', 'query', 'geocode'
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'geolocation_location_logs'
        ordering = ['-created_at']