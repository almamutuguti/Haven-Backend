import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Hospital(models.Model):
    SPECIALTY_CHOICES = (
        ('general', 'General Hospital'),
        ('trauma', 'Trauma Center'),
        ('cardiac', 'Cardiac Care'),
        ('pediatric', 'Pediatric'),
        ('neuro', 'Neurology'),
        ('ortho', 'Orthopedics'),
        ('burn', 'Burn Center'),
        ('maternity', 'Maternity'),
        ('psychiatric', 'Psychiatric'),
    )
    
    FACILITY_LEVEL_CHOICES = (
        ('level_1', 'Level 1 - Comprehensive Specialized'),
        ('level_2', 'Level 2 - Basic Specialized'),
        ('level_3', 'Level 3 - Primary Care'),
        ('level_4', 'Level 4 - Health Center'),
        ('level_5', 'Level 5 - Health Post'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    
    # Contact Information
    phone_number = models.CharField(max_length=20)
    emergency_contact = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField()
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100, blank=True)
    
    # Hospital Details
    facility_level = models.CharField(max_length=20, choices=FACILITY_LEVEL_CHOICES)
    specialties = models.JSONField(default=list)  # List of specialties from SPECIALTY_CHOICES
    registration_number = models.CharField(max_length=50, unique=True)
    
    # Capacity Information
    total_beds = models.PositiveIntegerField(default=0)
    available_beds = models.PositiveIntegerField(default=0)
    icu_beds = models.PositiveIntegerField(default=0)
    available_icu_beds = models.PositiveIntegerField(default=0)
    operating_theaters = models.PositiveIntegerField(default=0)
    available_theaters = models.PositiveIntegerField(default=0)
    
    # Staff Information
    doctors_count = models.PositiveIntegerField(default=0)
    nurses_count = models.PositiveIntegerField(default=0)
    emergency_staff_count = models.PositiveIntegerField(default=0)
    
    # Services and Equipment
    has_ambulance = models.BooleanField(default=False)
    available_ambulances = models.PositiveIntegerField(default=0)
    has_helipad = models.BooleanField(default=False)
    has_blood_bank = models.BooleanField(default=False)
    has_mri = models.BooleanField(default=False)
    has_ct_scan = models.BooleanField(default=False)
    has_xray = models.BooleanField(default=False)
    
    # Operational Status
    is_operational = models.BooleanField(default=True)
    accepts_emergencies = models.BooleanField(default=True)
    
    # Performance Metrics
    average_response_time = models.PositiveIntegerField(default=0, help_text="Average response time in minutes")
    success_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Success rate percentage"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hospitals'
        ordering = ['name']
        indexes = [
            models.Index(fields=['county', 'facility_level']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['is_operational', 'accepts_emergencies']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.county}"
    
    @property
    def bed_occupancy_rate(self):
        """Calculate bed occupancy rate"""
        if self.total_beds > 0:
            return ((self.total_beds - self.available_beds) / self.total_beds) * 100
        return 0
    
    @property
    def icu_occupancy_rate(self):
        """Calculate ICU bed occupancy rate"""
        if self.icu_beds > 0:
            return ((self.icu_beds - self.available_icu_beds) / self.icu_beds) * 100
        return 0

class HospitalAvailability(models.Model):
    """Track real-time hospital availability"""
    hospital = models.OneToOneField(Hospital, on_delete=models.CASCADE, related_name='availability')
    
    # Current capacity
    available_beds = models.PositiveIntegerField(default=0)
    available_icu_beds = models.PositiveIntegerField(default=0)
    available_theaters = models.PositiveIntegerField(default=0)
    available_ambulances = models.PositiveIntegerField(default=0)
    
    # Staff availability
    available_doctors = models.PositiveIntegerField(default=0)
    available_nurses = models.PositiveIntegerField(default=0)
    available_emergency_staff = models.PositiveIntegerField(default=0)
    
    # Emergency readiness
    can_accept_trauma = models.BooleanField(default=True)
    can_accept_cardiac = models.BooleanField(default=True)
    can_accept_pediatric = models.BooleanField(default=True)
    can_accept_neuro = models.BooleanField(default=True)
    
    # Status
    is_accepting_emergencies = models.BooleanField(default=True)
    estimated_wait_time = models.PositiveIntegerField(default=0, help_text="Estimated wait time in minutes")
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hospital_availability'
        verbose_name_plural = 'Hospital Availabilities'
    
    def __str__(self):
        return f"Availability for {self.hospital.name}"

class HospitalService(models.Model):
    """Track specific services offered by hospitals"""
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=50, choices=(
        ('emergency', 'Emergency Service'),
        ('specialty', 'Specialty Service'),
        ('diagnostic', 'Diagnostic Service'),
        ('surgical', 'Surgical Service'),
    ))
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'hospital_services'
        unique_together = ['hospital', 'service_name']
    
    def __str__(self):
        return f"{self.service_name} at {self.hospital.name}"