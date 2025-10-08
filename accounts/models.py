# apps/accounts/models.py
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, badge_number, password=None, **extra_fields):
        if not badge_number:
            raise ValueError('The Badge Number must be set')
        
        if not extra_fields.get('username'):
            extra_fields['username'] = badge_number
            
        user = self.model(badge_number=badge_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, badge_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'system_admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(badge_number, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('system_admin', 'System Admin'),
        ('first_aider', 'First Aider'),
        ('hospital_staff', 'Hospital Staff'),
        ('patient', 'Patient'),
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be in format: '+254712345678'."
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='first_aider')
    
    # Required fields for AbstractBaseUser
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    # Contact methods (phone optional)
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        unique=True, 
        null=True,
        blank=True
    )
    
    # For First Aiders - CHANGED: certification_level → registration_number
    badge_number = models.CharField(max_length=50, unique=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)  # NEW FIELD
    
    # # For Hospital Staff
    # hospital = models.ForeignKey(
    #     'hospitals.Hospital', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True
    # )
    
    # For Patients (optional)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(
        max_length=17, 
        blank=True,
        validators=[phone_regex]
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'badge_number'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        user_type_display = self.get_user_type_display()
        if self.badge_number:
            return f"{self.badge_number} ({user_type_display})"
        return f"User {self.id} ({user_type_display})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name

class EmergencyAccessLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def is_valid(self):
        return timezone.now() < self.expires_at