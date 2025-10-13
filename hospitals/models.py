from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser as User
from geolocation.models import Location, HospitalLocation


class Hospital(models.Model):
    """
    Core hospital model storing hospital information and capabilities
    """
    HOSPITAL_TYPE_CHOICES = [
        ('public', 'Public Hospital'),
        ('private', 'Private Hospital'),
        ('mission', 'Mission Hospital'),
        ('clinic', 'Clinic'),
        ('specialized', 'Specialized Center'),
    ]

    HOSPITAL_LEVEL_CHOICES = [
        ('level_1', 'Level 1 - Basic'),
        ('level_2', 'Level 2 - General'),
        ('level_3', 'Level 3 - Specialized'),
        ('level_4', 'Level 4 - Regional Referral'),
        ('level_5', 'Level 5 - National Referral'),
        ('level_6', 'Level 6 - International'),
    ]

    # Basic Information
    name = models.CharField(max_length=255)
    hospital_type = models.CharField(max_length=20, choices=HOSPITAL_TYPE_CHOICES, default='public')
    level = models.CharField(max_length=20, choices=HOSPITAL_LEVEL_CHOICES, default='level_2')
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Location Reference
    location = models.OneToOneField(
        HospitalLocation,
        on_delete=models.CASCADE,
        related_name='hospital'
    )
    
    # Identification
    place_id = models.CharField(max_length=255, unique=True, blank=True)
    mfl_code = models.CharField(max_length=20, blank=True, help_text="Ministry of Health Facility Code")
    
    # Operational Status
    is_operational = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    accepts_emergencies = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'hospitals'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['hospital_type']),
            models.Index(fields=['level']),
            models.Index(fields=['is_operational', 'accepts_emergencies']),
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_hospital_type_display()})"


class HospitalSpecialty(models.Model):
    """
    Hospital medical specialties and capabilities
    """
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='specialties'
    )
    
    specialty = models.CharField(
        max_length=50,
        choices=[
            ('trauma', 'Trauma Center'),
            ('cardiac', 'Cardiac Care'),
            ('pediatric', 'Pediatric Care'),
            ('maternity', 'Maternity'),
            ('surgical', 'Surgical Services'),
            ('icu', 'Intensive Care Unit'),
            ('emergency', 'Emergency Department'),
            ('orthopedic', 'Orthopedic'),
            ('neurology', 'Neurology'),
            ('oncology', 'Oncology'),
            ('burn_unit', 'Burn Unit'),
            ('psychiatric', 'Psychiatric'),
            ('rehabilitation', 'Rehabilitation'),
        ]
    )
    
    # Capability levels
    capability_level = models.CharField(
        max_length=20,
        choices=[
            ('basic', 'Basic'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('specialized', 'Specialized'),
        ],
        default='basic'
    )
    
    is_available = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'hospital_specialties'
        unique_together = ['hospital', 'specialty']
        verbose_name_plural = 'Hospital specialties'

    def __str__(self):
        return f"{self.hospital.name} - {self.get_specialty_display()}"


class HospitalCapacity(models.Model):
    """
    Real-time hospital capacity tracking
    """
    hospital = models.OneToOneField(
        Hospital,
        on_delete=models.CASCADE,
        related_name='capacity'
    )
    
    # Bed capacity
    total_beds = models.PositiveIntegerField(default=0)
    available_beds = models.PositiveIntegerField(default=0)
    
    # Emergency capacity
    emergency_beds_total = models.PositiveIntegerField(default=0)
    emergency_beds_available = models.PositiveIntegerField(default=0)
    
    # ICU capacity
    icu_beds_total = models.PositiveIntegerField(default=0)
    icu_beds_available = models.PositiveIntegerField(default=0)
    
    # Wait times (in minutes)
    average_wait_time = models.PositiveIntegerField(default=0, help_text="Average wait time in minutes")
    emergency_wait_time = models.PositiveIntegerField(default=0, help_text="Emergency department wait time")
    
    # Staff availability
    doctors_available = models.PositiveIntegerField(default=0)
    nurses_available = models.PositiveIntegerField(default=0)
    
    # Status
    is_accepting_patients = models.BooleanField(default=True)
    capacity_status = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Capacity'),
            ('moderate', 'Moderate Capacity'),
            ('high', 'High Capacity'),
            ('full', 'At Capacity'),
            ('overflow', 'Overflow'),
        ],
        default='moderate'
    )
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    next_update_expected = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'hospital_capacities'
        verbose_name_plural = 'Hospital capacities'

    def __str__(self):
        return f"Capacity for {self.hospital.name}"

    @property
    def bed_occupancy_rate(self):
        if self.total_beds == 0:
            return 0
        return ((self.total_beds - self.available_beds) / self.total_beds) * 100

    @property
    def emergency_occupancy_rate(self):
        if self.emergency_beds_total == 0:
            return 0
        return ((self.emergency_beds_total - self.emergency_beds_available) / self.emergency_beds_total) * 100


class HospitalRating(models.Model):
    """
    Hospital ratings and reviews
    """
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hospital_ratings'
    )
    
    # Ratings (1-5)
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    staff_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    facilities_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    emergency_care_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    # Review
    review_title = models.CharField(max_length=100, blank=True)
    review_text = models.TextField(blank=True)
    
    # Emergency context
    was_emergency = models.BooleanField(default=False)
    emergency_type = models.CharField(max_length=50, blank=True)
    
    # Metadata
    is_verified = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hospital_ratings'
        indexes = [
            models.Index(fields=['hospital', 'overall_rating']),
            models.Index(fields=['was_emergency']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Rating {self.overall_rating} for {self.hospital.name}"


class EmergencyResponse(models.Model):
    """
    Track hospital responses to emergency alerts
    """
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='emergency_responses'
    )
    
    # Response details
    response_time = models.PositiveIntegerField(help_text="Response time in seconds")
    accepted_patient = models.BooleanField(default=False)
    reason_for_rejection = models.TextField(blank=True)
    
    # Capacity at time of response
    beds_available_at_response = models.PositiveIntegerField(default=0)
    emergency_beds_available_at_response = models.PositiveIntegerField(default=0)
    
    # Timestamps
    alert_received_at = models.DateTimeField()
    response_sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'emergency_responses'
        indexes = [
            models.Index(fields=['hospital', 'response_sent_at']),
        ]
        ordering = ['-response_sent_at']

    def __str__(self):
        status = "Accepted" if self.accepted_patient else "Rejected"
        return f"Response from {self.hospital.name} - {status}"


class HospitalWorkingHours(models.Model):
    """
    Hospital working hours and emergency service availability
    """
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='working_hours'
    )
    
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    
    # Regular hours
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    
    # Emergency hours (if different)
    emergency_opens_at = models.TimeField(null=True, blank=True)
    emergency_closes_at = models.TimeField(null=True, blank=True)
    
    # Status
    is_24_hours = models.BooleanField(default=False)
    is_emergency_24_hours = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'hospital_working_hours'
        unique_together = ['hospital', 'day']
        verbose_name_plural = 'Hospital working hours'

    def __str__(self):
        return f"{self.hospital.name} - {self.get_day_display()}"

    @property
    def has_emergency_services(self):
        return self.is_emergency_24_hours or (self.emergency_opens_at is not None and self.emergency_closes_at is not None)