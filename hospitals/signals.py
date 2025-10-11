from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Hospital, HospitalCapacity, HospitalRating


@receiver(post_save, sender=Hospital)
def create_hospital_capacity(sender, instance, created, **kwargs):
    """
    Create hospital capacity record when new hospital is created
    """
    if created and not hasattr(instance, 'capacity'):
        HospitalCapacity.objects.create(hospital=instance)


@receiver(pre_save, sender=Hospital)
def update_verification_timestamp(sender, instance, **kwargs):
    """
    Update verification timestamp when hospital is verified
    """
    if instance.pk:
        try:
            old_instance = Hospital.objects.get(pk=instance.pk)
            if not old_instance.is_verified and instance.is_verified:
                instance.verified_at = timezone.now()
        except Hospital.DoesNotExist:
            pass


@receiver(post_save, sender=HospitalRating)
def update_hospital_ratings_cache(sender, instance, **kwargs):
    """
    Update hospital ratings cache when new rating is added
    """
    from django.core.cache import cache
    
    # Invalidate cache for this hospital's ratings
    cache_key = f"hospital_ratings_{instance.hospital_id}"
    cache.delete(cache_key)
    
    # Also invalidate nearby hospitals cache that might include this hospital
    cache.delete_many([key for key in cache.keys() if 'nearby_hospitals' in key])


@receiver(post_save, sender=HospitalCapacity)
def update_capacity_cache(sender, instance, **kwargs):
    """
    Update capacity cache when hospital capacity changes
    """
    from django.core.cache import cache
    
    # Invalidate cache for this hospital's availability
    cache_key = f"hospital_availability_{instance.hospital_id}"
    cache.delete(cache_key)
    
    # Invalidate nearby hospitals cache
    cache.delete_many([key for key in cache.keys() if 'nearby_hospitals' in key])