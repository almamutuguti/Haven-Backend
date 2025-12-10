from django.db import models
from django.conf import settings
from accounts.models import CustomUser, Organization
from hospitals.models import Hospital

class Verification(models.Model):
    VERIFICATION_TYPE_CHOICES = [
        ('hospital', 'Hospital'),
        ('organization', 'Organization'),
        ('user', 'User'),
        ('email', 'Email Verification Fallback'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('info_requested', 'More Info Requested'),
    ]
    
    # Link to the entity being verified
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    
    # Verification details
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_data = models.JSONField()  # Store all submitted information
    
    # Admin actions
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verifications_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_verification_type_display()} - {self.status}"
    
    def get_entity_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.email
        elif self.hospital:
            return self.hospital.name
        elif self.organization:
            return self.organization.name
        return "Unknown Entity"
    
    def get_entity_email(self):
        if self.user:
            return self.user.email
        elif self.hospital:
            return self.hospital.email
        elif self.organization:
            return self.organization.email
        return None