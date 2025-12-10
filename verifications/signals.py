from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import CustomUser, Organization
from hospitals.models import Hospital
from .models import Verification

@receiver(post_save, sender=CustomUser)
def create_user_verification(sender, instance, created, **kwargs):
    if created and not instance.is_email_verified:
        # Create verification for user email
        Verification.objects.create(
            user=instance,
            verification_type='user',
            status='pending',
            submitted_data={
                'email': instance.email,
                'username': instance.username,
                'first_name': instance.first_name,
                'last_name': instance.last_name,
                'phone': instance.phone,
                'role': instance.role
            }
        )

@receiver(post_save, sender=Organization)
def create_organization_verification(sender, instance, created, **kwargs):
    if created:
        # Create verification for new organization
        Verification.objects.create(
            organization=instance,
            verification_type='organization',
            status='pending',
            submitted_data={
                'name': instance.name,
                'organization_type': instance.organization_type,
                'contact_person': instance.contact_person,
                'phone': instance.phone,
                'email': instance.email,
                'address': instance.address
            }
        )

@receiver(post_save, sender=Hospital)
def create_hospital_verification(sender, instance, created, **kwargs):
    if created:
        # Create verification for new hospital
        Verification.objects.create(
            hospital=instance,
            verification_type='hospital',
            status='pending',
            submitted_data={
                'name': instance.name,
                'hospital_type': instance.hospital_type,
                'level': instance.level,
                'phone': instance.phone,
                'email': instance.email,
                'address': instance.address
            }
        )