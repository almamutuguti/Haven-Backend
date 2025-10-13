from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser as User


class MedicalProfile(models.Model):
    """
    Core medical profile model storing comprehensive medical information
    """
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('unknown', 'Unknown'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='medical_profile'
    )
    
    # Personal Medical Information
    blood_type = models.CharField(
        max_length=10,
        choices=BLOOD_TYPE_CHOICES,
        default='unknown'
    )
    height_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Height in centimeters")
    weight_kg = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Weight in kilograms"
    )
    
    # Emergency Information
    organ_donor = models.BooleanField(default=False)
    dnr_order = models.BooleanField(default=False, help_text="Do Not Resuscitate order")
    advance_directive = models.TextField(blank=True, help_text="Living will or advance directive")
    
    # Medical History
    primary_care_physician = models.CharField(max_length=255, blank=True)
    physician_phone = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_medical_review = models.DateField(null=True, blank=True)
    
    # GDPR/HIPAA Compliance
    data_consent_given = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)
    data_sharing_preferences = models.JSONField(
        default=dict,
        help_text="Preferences for data sharing with hospitals"
    )
    
    class Meta:
        db_table = 'medical_profiles'
        verbose_name = 'Medical Profile'
        verbose_name_plural = 'Medical Profiles'

    def __str__(self):
        return f"Medical Profile - {self.user.email}"

    @property
    def bmi(self):
        """Calculate Body Mass Index"""
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None

    @property
    def age(self):
        """Calculate age from user's date of birth"""
        if self.user.date_of_birth:
            from django.utils import timezone
            today = timezone.now().date()
            return today.year - self.user.date_of_birth.year - (
                (today.month, today.day) < (self.user.date_of_birth.month, self.user.date_of_birth.day)
            )
        return None


class MedicalCondition(models.Model):
    """
    Store chronic medical conditions and diagnoses
    """
    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('in_remission', 'In Remission'),
        ('resolved', 'Resolved'),
        ('monitoring', 'Monitoring'),
    ]

    medical_profile = models.ForeignKey(
        MedicalProfile,
        on_delete=models.CASCADE,
        related_name='conditions'
    )
    
    # Condition details
    name = models.CharField(max_length=255)
    diagnosis_date = models.DateField(null=True, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='moderate')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Medical details
    icd_code = models.CharField(max_length=20, blank=True, help_text="International Classification of Diseases code")
    description = models.TextField(blank=True)
    is_chronic = models.BooleanField(default=False)
    is_critical = models.BooleanField(default=False)
    
    # Treatment
    treatment_plan = models.TextField(blank=True)
    specialist = models.CharField(max_length=255, blank=True)
    specialist_contact = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_conditions'
        ordering = ['-is_critical', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.medical_profile.user.email}"


class Allergy(models.Model):
    """
    Store allergy information
    """
    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('life_threatening', 'Life Threatening'),
    ]

    TYPE_CHOICES = [
        ('drug', 'Drug Allergy'),
        ('food', 'Food Allergy'),
        ('environmental', 'Environmental Allergy'),
        ('insect', 'Insect Sting Allergy'),
        ('latex', 'Latex Allergy'),
        ('other', 'Other'),
    ]

    medical_profile = models.ForeignKey(
        MedicalProfile,
        on_delete=models.CASCADE,
        related_name='allergies'
    )
    
    # Allergy details
    allergen = models.CharField(max_length=255)
    allergy_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='moderate')
    
    # Reaction information
    reaction = models.TextField(help_text="Description of allergic reaction")
    onset_time = models.CharField(max_length=100, blank=True, help_text="e.g., immediate, delayed")
    
    # Treatment
    treatment = models.TextField(blank=True, help_text="Recommended treatment for reaction")
    epi_pen_required = models.BooleanField(default=False)
    
    # Verification
    diagnosed_by = models.CharField(max_length=255, blank=True)
    diagnosis_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'allergies'
        verbose_name_plural = 'Allergies'
        ordering = ['-severity', 'allergen']

    def __str__(self):
        return f"{self.allergen} Allergy - {self.medical_profile.user.email}"


class Medication(models.Model):
    """
    Store current and past medications
    """
    FREQUENCY_CHOICES = [
        ('as_needed', 'As Needed'),
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('three_times_daily', 'Three Times Daily'),
        ('four_times_daily', 'Four Times Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('discontinued', 'Discontinued'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]

    medical_profile = models.ForeignKey(
        MedicalProfile,
        on_delete=models.CASCADE,
        related_name='medications'
    )
    
    # Medication details
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg, 10 units")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='once_daily')
    custom_frequency = models.CharField(max_length=100, blank=True)
    
    # Prescription information
    prescribing_doctor = models.CharField(max_length=255, blank=True)
    prescription_date = models.DateField(null=True, blank=True)
    purpose = models.TextField(blank=True, help_text="Reason for taking this medication")
    
    # Status and timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Instructions
    instructions = models.TextField(blank=True, help_text="Special instructions for taking medication")
    with_food = models.BooleanField(default=False, help_text="Take with food")
    avoid_alcohol = models.BooleanField(default=False)
    
    # Emergency relevance
    is_critical = models.BooleanField(default=False, help_text="Critical medication that cannot be missed")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medications'
        ordering = ['-is_critical', '-status', 'name']

    def __str__(self):
        return f"{self.name} - {self.medical_profile.user.email}"


class EmergencyContact(models.Model):
    """
    Store emergency contact information
    """
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('sibling', 'Sibling'),
        ('friend', 'Friend'),
        ('other_relative', 'Other Relative'),
        ('caregiver', 'Caregiver'),
        ('other', 'Other'),
    ]

    medical_profile = models.ForeignKey(
        MedicalProfile,
        on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )
    
    # Contact information
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='family')
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    
    # Emergency specifics
    is_primary = models.BooleanField(default=False)
    can_make_medical_decisions = models.BooleanField(default=False)
    notes = models.TextField(blank=True, help_text="Special instructions or notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'emergency_contacts'
        ordering = ['-is_primary', 'full_name']

    def __str__(self):
        return f"{self.full_name} - {self.medical_profile.user.email}"


class MedicalDocument(models.Model):
    """
    Store medical documents and reports
    """
    DOCUMENT_TYPE_CHOICES = [
        ('insurance_card', 'Insurance Card'),
        ('id_document', 'ID Document'),
        ('medical_report', 'Medical Report'),
        ('lab_result', 'Lab Result'),
        ('prescription', 'Prescription'),
        ('scan_image', 'Scan/Image'),
        ('advance_directive', 'Advance Directive'),
        ('other', 'Other'),
    ]

    medical_profile = models.ForeignKey(
        MedicalProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    # Document information
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default='other')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # File storage
    file = models.FileField(upload_to='medical_documents/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    # Metadata
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    issuing_authority = models.CharField(max_length=255, blank=True)
    
    # Security
    is_encrypted = models.BooleanField(default=True)
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('emergency_only', 'Emergency Only'),
            ('medical_staff', 'Medical Staff'),
            ('full_access', 'Full Access'),
        ],
        default='medical_staff'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.medical_profile.user.email}"


class InsuranceInformation(models.Model):
    """
    Store health insurance information
    """
    medical_profile = models.ForeignKey(
        MedicalProfile,
        on_delete=models.CASCADE,
        related_name='insurance_info'
    )
    
    # Insurance details
    insurance_provider = models.CharField(max_length=255)
    policy_number = models.CharField(max_length=100)
    group_number = models.CharField(max_length=100, blank=True)
    plan_type = models.CharField(max_length=100, blank=True)
    
    # Contact information
    provider_phone = models.CharField(max_length=20, blank=True)
    provider_website = models.URLField(blank=True)
    
    # Coverage details
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Emergency coverage
    emergency_coverage = models.BooleanField(default=True)
    coverage_notes = models.TextField(blank=True)
    
    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('verified', 'Verified'),
            ('pending', 'Pending Verification'),
            ('unverified', 'Unverified'),
            ('expired', 'Expired'),
        ],
        default='unverified'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'insurance_information'
        verbose_name_plural = 'Insurance Information'

    def __str__(self):
        return f"{self.insurance_provider} - {self.medical_profile.user.email}"


class SurgicalHistory(models.Model):
    """
    Store surgical history
    """
    medical_profile = models.ForeignKey(
        MedicalProfile,
        on_delete=models.CASCADE,
        related_name='surgical_history'
    )
    
    # Surgery details
    procedure_name = models.CharField(max_length=255)
    date_performed = models.DateField()
    surgeon = models.CharField(max_length=255, blank=True)
    hospital = models.CharField(max_length=255, blank=True)
    
    # Medical details
    reason = models.TextField(blank=True, help_text="Reason for surgery")
    complications = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    
    # Emergency relevance
    has_implants = models.BooleanField(default=False)
    implant_details = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'surgical_history'
        verbose_name_plural = 'Surgical Histories'
        ordering = ['-date_performed']

    def __str__(self):
        return f"{self.procedure_name} - {self.medical_profile.user.email}"