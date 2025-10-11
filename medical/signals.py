from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import MedicalProfile, EmergencyContact


@receiver(post_save, sender=MedicalProfile)
def handle_medical_profile_creation(sender, instance, created, **kwargs):
    """
    Handle medical profile creation and updates
    """
    if created:
        # Set consent timestamp if consent given
        if instance.data_consent_given and not instance.consent_given_at:
            instance.consent_given_at = timezone.now()
            instance.save(update_fields=['consent_given_at'])
        
        # Log profile creation
        from django.core.cache import cache
        cache_key = f"medical_profile_{instance.user_id}"
        cache.delete(cache_key)


@receiver(pre_save, sender=MedicalProfile)
def update_consent_timestamp(sender, instance, **kwargs):
    """
    Update consent timestamp when consent is given
    """
    if instance.pk:
        try:
            old_instance = MedicalProfile.objects.get(pk=instance.pk)
            if not old_instance.data_consent_given and instance.data_consent_given:
                instance.consent_given_at = timezone.now()
        except MedicalProfile.DoesNotExist:
            pass


@receiver(post_save, sender=EmergencyContact)
def handle_primary_contact(sender, instance, created, **kwargs):
    """
    Ensure only one primary emergency contact exists
    """
    if instance.is_primary:
        # Remove primary from other contacts for this user
        EmergencyContact.objects.filter(
            medical_profile=instance.medical_profile,
            is_primary=True
        ).exclude(id=instance.id).update(is_primary=False)


@receiver(post_save, sender=MedicalProfile)
def invalidate_medical_cache(sender, instance, **kwargs):
    """
    Invalidate cache when medical profile changes
    """
    from django.core.cache import cache
    
    # Invalidate emergency data cache
    cache_keys = [
        f"emergency_data_{instance.user_id}",
        f"fhir_data_{instance.user_id}",
        f"emergency_summary_{instance.user_id}",
    ]
    
    for key in cache_keys:
        cache.delete(key)


@receiver(post_save, sender=MedicalProfile)
def create_default_data_sharing_preferences(sender, instance, created, **kwargs):
    """
    Create default data sharing preferences if none exist
    """
    if created and not instance.data_sharing_preferences:
        instance.data_sharing_preferences = {
            'share_with_emergency_services': True,
            'share_with_hospitals': True,
            'share_allergies': True,
            'share_medications': True,
            'share_conditions': True,
            'share_contacts': True,
            'encrypt_sensitive_data': True,
        }
        instance.save(update_fields=['data_sharing_preferences'])