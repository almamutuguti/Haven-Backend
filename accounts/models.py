import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.forms import ValidationError
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username must be set')
        
        if not extra_fields.get('badge_number'):
            extra_fields['badge_number'] = username
            
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'system_admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        if not extra_fields.get('role') == 'system_admin':
            raise ValueError('Superuser must have role=system_admin.')
        
        return self.create_user(username, password, **extra_fields)


class Organization(models.Model):
    """Organization model for first aiders"""
    ORGANIZATION_TYPE_CHOICES = [
        ('red_cross', 'Red Cross Society'),
        ('st_john', 'St. John Ambulance'),
        ('community', 'Community Volunteers'),
        ('corporate', 'Corporate First Aid'),
        ('government', 'Government Agency'),
        ('ngo', 'Non-Governmental Organization'),
    ]

    # Use AutoField instead of UUIDField to avoid migration issues
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=20, choices=ORGANIZATION_TYPE_CHOICES, default='community')
    description = models.TextField(blank=True)
    
    # Contact Information
    contact_person = models.CharField(max_length=255, blank=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$')
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True)
    
    # Location
    address = models.TextField(blank=True)
    
    # Operational Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('system_admin', 'System Admin'),
        ('hospital_admin', 'Hospital Admin'),
        ('organization_admin', 'Organization Admin'),
        ('first_aider', 'First Aider'),
        ('hospital_staff', 'Hospital Staff'),
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be in format: '+254712345678'."
    )

    # Use AutoField instead of UUIDField to avoid migration issues
    id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='first_aider')
    
    # Required fields for AbstractBaseUser
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    
    # OTP fields
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    otp_for_password_reset = models.BooleanField(default=False)
    
    # Contact methods (phone optional)
    phone = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        unique=True, 
        null=True,
        blank=True
    )
    
    # For First Aiders
    badge_number = models.CharField(max_length=50, unique=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)  
    
    # Hospital and Organization relationships
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='staff'
    )
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='first_aiders'
    )
    
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(
        max_length=17, 
        blank=True,
        validators=[phone_regex]
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        role_display = self.get_role_display()
        if self.badge_number:
            return f"{self.badge_number} ({role_display})"
        return f"User {self.id} ({role_display})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name
    
    class Meta:
        db_table = 'accounts_customusers'


class EmergencyAccessLog(models.Model):
    # Use AutoField instead of UUIDField to avoid migration issues
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def is_valid(self):
        return timezone.now() < self.expires_at
    
    class Meta:
        db_table = 'accounts_emergency_access_logs'

class SystemSettings(models.Model):
    """
    System-wide configuration settings for the Haven platform
    """
    # General Settings
    system_name = models.CharField(max_length=255, default="Haven Emergency Response")
    system_email = models.EmailField(default="noreply@haven.com")
    
    # Feature Flags
    maintenance_mode = models.BooleanField(default=False)
    user_registration_enabled = models.BooleanField(default=True)
    
    # Notification Settings
    email_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=True)
    push_notifications_enabled = models.BooleanField(default=True)
    
    # Data Management
    backup_frequency = models.CharField(
        max_length=20,
        choices=[
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='daily'
    )
    data_retention_days = models.PositiveIntegerField(default=365)
    
    # Security Settings
    security_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('maximum', 'Maximum'),
        ],
        default='high'
    )
    
    # Audit Information
    last_modified = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_settings'
    )
    last_security_audit = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_settings'
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return f"System Settings (Last modified: {self.last_modified})"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SystemSettings.objects.exists():
            raise ValidationError("Only one SystemSettings instance can exist")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create system settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj