import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser as User
from hospitals.models import Hospital
from emergencies.models import EmergencyAlert
from medical.models import MedicalProfile


class EmergencyHospitalCommunication(models.Model):
    """
    Core model for hospital communication during emergencies
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent to Hospital'),
        ('delivered', 'Delivered to Hospital'),
        ('acknowledged', 'Acknowledged by Hospital'),
        ('preparing', 'Hospital Preparing'),
        ('ready', 'Hospital Ready'),
        ('en_route', 'Patient En Route'),
        ('arrived', 'Patient Arrived'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Delivery Failed'),
    ]

    PRIORITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    # Core relationships - FIXED: Explicitly define the foreign key as UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Use CharField to store the EmergencyAlert's UUID and handle the relationship manually
    emergency_alert_id = models.UUIDField(editable=False, db_index=True)
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='emergency_communications'
    )
    first_aider = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_communications',
        limit_choices_to={'role': 'first_aider'}
    )
    
    # Store the alert_id as a separate field for easy reference
    alert_reference_id = models.CharField(max_length=20, blank=True, db_index=True)
    
    # Communication details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='high')
    
    # Victim information (collected by first aider at scene)
    victim_name = models.CharField(max_length=255, blank=True)
    victim_age = models.PositiveIntegerField(null=True, blank=True)
    victim_gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    
    # Emergency assessment by first aider
    chief_complaint = models.TextField(help_text="Primary complaint or reason for emergency")
    vital_signs = models.JSONField(default=dict, help_text="Vital signs recorded by first aider")
    initial_assessment = models.TextField(help_text="First aider's initial assessment and observations")
    first_aid_provided = models.TextField(blank=True, help_text="First aid treatment already provided")
    
    # Estimated arrival information
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    estimated_arrival_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Hospital preparation requirements
    required_specialties = models.JSONField(default=list, help_text="Required medical specialties")
    equipment_needed = models.JSONField(default=list, help_text="Special equipment needed")
    blood_type_required = models.CharField(max_length=10, blank=True, help_text="Blood type if transfusion might be needed")
    
    # Communication tracking
    communication_attempts = models.PositiveIntegerField(default=0)
    last_communication_attempt = models.DateTimeField(null=True, blank=True)
    
    # Hospital response
    hospital_acknowledged_at = models.DateTimeField(null=True, blank=True)
    hospital_acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_communications',
        limit_choices_to={'role': 'hospital_admin'}
    )
    
    # Preparation status from hospital
    doctors_ready = models.BooleanField(default=False)
    nurses_ready = models.BooleanField(default=False)
    equipment_ready = models.BooleanField(default=False)
    bed_ready = models.BooleanField(default=False)
    blood_available = models.BooleanField(default=False)
    
    hospital_preparation_notes = models.TextField(blank=True, help_text="Hospital preparation status notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_to_hospital_at = models.DateTimeField(null=True, blank=True)
    hospital_ready_at = models.DateTimeField(null=True, blank=True)
    patient_arrived_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'emergency_hospital_communications'
        indexes = [
            models.Index(fields=['emergency_alert_id']),
            models.Index(fields=['alert_reference_id']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Comm: {self.alert_reference_id} -> {self.hospital.name}"

    @property
    def emergency_alert(self):
        """Property to get the related EmergencyAlert"""
        try:
            return EmergencyAlert.objects.get(id=self.emergency_alert_id)
        except EmergencyAlert.DoesNotExist:
            return None

    @emergency_alert.setter
    def emergency_alert(self, value):
        """Property setter for EmergencyAlert"""
        if value:
            self.emergency_alert_id = value.id
            self.alert_reference_id = value.alert_id

    def save(self, *args, **kwargs):
        # Store the alert_id for easy reference
        if self.emergency_alert_id and not self.alert_reference_id:
            try:
                alert = EmergencyAlert.objects.get(id=self.emergency_alert_id)
                self.alert_reference_id = alert.alert_id
            except EmergencyAlert.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class CommunicationLog(models.Model):
    """
    Track all communication attempts and responses
    """
    CHANNEL_CHOICES = [
        ('api', 'Hospital API'),
        ('sms', 'SMS'),
        ('voice', 'Voice Call'),
        ('webhook', 'Webhook'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    ]

    DIRECTION_CHOICES = [
        ('outgoing', 'Outgoing to Hospital'),
        ('incoming', 'Incoming from Hospital'),
    ]

    communication = models.ForeignKey(
        EmergencyHospitalCommunication,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    # Communication details
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=50, help_text="Type of message sent/received")
    
    # Content
    message_content = models.TextField(help_text="Actual message content sent or received")
    message_data = models.JSONField(default=dict, help_text="Structured message data")
    
    # Status
    is_successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    response_code = models.CharField(max_length=10, blank=True)
    
    # Metadata
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    response_received_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'communication_logs'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.direction} {self.channel} - {self.communication}"


class HospitalPreparationChecklist(models.Model):
    """
    Hospital preparation checklist and status
    """
    communication = models.OneToOneField(
        EmergencyHospitalCommunication,
        on_delete=models.CASCADE,
        related_name='preparation_checklist'
    )
    
    # Medical team preparation
    emergency_doctor_assigned = models.BooleanField(default=False)
    specialist_doctor_notified = models.BooleanField(default=False)
    nursing_team_ready = models.BooleanField(default=False)
    anesthesiologist_alerted = models.BooleanField(default=False)
    
    # Facility preparation
    emergency_bed_prepared = models.BooleanField(default=False)
    operating_room_reserved = models.BooleanField(default=False)
    icu_bed_available = models.BooleanField(default=False)
    
    # Equipment preparation
    vital_monitors_ready = models.BooleanField(default=False)
    ventilator_available = models.BooleanField(default=False)
    defibrillator_ready = models.BooleanField(default=False)
    emergency_medications_ready = models.BooleanField(default=False)
    
    # Diagnostic preparation
    lab_tests_ordered = models.BooleanField(default=False)
    imaging_ready = models.BooleanField(default=False)
    blood_products_available = models.BooleanField(default=False)
    
    # Support services
    pharmacy_alerted = models.BooleanField(default=False)
    blood_bank_notified = models.BooleanField(default=False)
    transport_team_ready = models.BooleanField(default=False)
    
    # Status tracking
    checklist_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_checklists'
    )
    
    notes = models.TextField(blank=True, help_text="Additional preparation notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hospital_preparation_checklists'

    def __str__(self):
        return f"Checklist for {self.communication}"

    @property
    def completion_percentage(self):
        """Calculate checklist completion percentage"""
        total_items = 16  # Total number of checklist items
        completed_items = sum([
            self.emergency_doctor_assigned,
            self.specialist_doctor_notified,
            self.nursing_team_ready,
            self.anesthesiologist_alerted,
            self.emergency_bed_prepared,
            self.operating_room_reserved,
            self.icu_bed_available,
            self.vital_monitors_ready,
            self.ventilator_available,
            self.defibrillator_ready,
            self.emergency_medications_ready,
            self.lab_tests_ordered,
            self.imaging_ready,
            self.blood_products_available,
            self.pharmacy_alerted,
            self.blood_bank_notified,
            self.transport_team_ready,
        ])
        return round((completed_items / total_items) * 100, 1)


class FirstAiderAssessment(models.Model):
    """
    Detailed assessment by first aider at the scene
    """
    communication = models.OneToOneField(
        EmergencyHospitalCommunication,
        on_delete=models.CASCADE,
        related_name='first_aider_assessment'
    )
    
    # Glasgow Coma Scale
    gcs_eyes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        null=True,
        blank=True
    )
    gcs_verbal = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    gcs_motor = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        null=True,
        blank=True
    )
    gcs_total = models.IntegerField(
        validators=[MinValueValidator(3), MaxValueValidator(15)],
        null=True,
        blank=True
    )
    
    # Vital signs
    heart_rate = models.PositiveIntegerField(null=True, blank=True, help_text="BPM")
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Breaths per minute")
    oxygen_saturation = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        help_text="SpO2 percentage"
    )
    temperature = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        null=True, 
        blank=True,
        help_text="Temperature in Celsius"
    )
    
    # Trauma assessment
    mechanism_of_injury = models.TextField(blank=True, help_text="How the injury occurred")
    injuries_noted = models.JSONField(default=list, help_text="List of observed injuries")
    pain_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        null=True,
        blank=True,
        help_text="Pain scale 0-10"
    )
    
    # Medical history from scene
    known_allergies = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    past_medical_history = models.TextField(blank=True)
    last_oral_intake = models.TextField(blank=True, help_text="When patient last ate/drank")
    
    # First aid interventions
    interventions_provided = models.JSONField(
        default=list,
        help_text="First aid treatments already provided"
    )
    medications_administered = models.JSONField(
        default=list,
        help_text="Medications given by first aider"
    )
    
    # Triage category
    triage_category = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate (Red)'),
            ('delayed', 'Delayed (Yellow)'),
            ('minor', 'Minor (Green)'),
            ('expectant', 'Expectant (Black)'),
        ],
        default='immediate'
    )
    
    # Additional notes
    scene_observations = models.TextField(blank=True, help_text="Additional observations from the scene")
    safety_concerns = models.TextField(blank=True, help_text="Any safety concerns at the scene")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'first_aider_assessments'

    def __str__(self):
        return f"Assessment for {self.communication}"

    def save(self, *args, **kwargs):
        # Calculate GCS total if components are provided
        if self.gcs_eyes and self.gcs_verbal and self.gcs_motor:
            self.gcs_total = self.gcs_eyes + self.gcs_verbal + self.gcs_motor
        super().save(*args, **kwargs)