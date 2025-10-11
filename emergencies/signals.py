from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EmergencyAlert
from .tasks import process_emergency_alert


@receiver(post_save, sender=EmergencyAlert)
def handle_emergency_alert_update(sender, instance, created, **kwargs):
    """
    Handle emergency alert updates and trigger appropriate actions
    """
    if created:
        # New emergency alert created

        # In production, use Celery for async processing
        process_emergency_alert.delay(instance.alert_id)
    
    # TODO: Add real-time notifications via WebSockets
    # TODO: Trigger hospital matching when alert is verified