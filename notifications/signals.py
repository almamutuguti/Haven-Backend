from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Notification,
    UserNotificationPreference
)
from emergencies.models import EmergencyAlert
from hospital_communication.models import EmergencyHospitalCommunication

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    """
    Automatically create notification preferences when a user is created
    """
    if created and not hasattr(instance, 'notification_preferences'):
        UserNotificationPreference.objects.create(user=instance)

@receiver(post_save, sender=EmergencyAlert)
def notify_first_aiders_about_emergency(sender, instance, created, **kwargs):
    """
    Send notifications to first-aiders when a new emergency is created
    """
    if created and instance.status == 'active':
        from .services import NotificationOrchestrator, NotificationTemplateService
        
        # Get nearby first-aiders (simplified - you'd implement location-based logic)
        nearby_first_aiders = User.objects.filter(
            role='first_aider',
            is_active=True
        )[:10]  # Limit for demo
        
        orchestrator = NotificationOrchestrator()
        
        for first_aider in nearby_first_aiders:
            context = {
                'first_aider_name': first_aider.get_full_name(),
                'alert_id': instance.alert_id,
                'location': instance.location_description or 'Unknown location',
                'timestamp': timezone.now().strftime('%H:%M')
            }
            
            # Create notification from template
            notification = NotificationTemplateService.create_notification_from_template(
                user=first_aider,
                template_name='first_aider_dispatch',
                context=context,
                emergency_alert=instance
            )
            
            if notification:
                orchestrator.send_notification(notification)

@receiver(post_save, sender=EmergencyHospitalCommunication)
def notify_hospital_and_first_aider(sender, instance, created, **kwargs):
    """
    Send notifications when hospital communication is created or updated
    """
    from .services import NotificationOrchestrator, NotificationTemplateService
    
    if created:
        # Notify hospital staff
        hospital_staff = User.objects.filter(
            role='hospital_staff',
            hospital=instance.hospital,
            is_active=True
        )
        
        for admin in hospital_staff:
            context = {
                'admin_name': admin.get_full_name(),
                'alert_id': instance.alert_reference_id,
                'victim_name': instance.victim_name or 'Unknown',
                'chief_complaint': instance.chief_complaint,
                'eta_minutes': instance.estimated_arrival_minutes or 'Unknown'
            }
            
            notification = NotificationTemplateService.create_notification_from_template(
                user=admin,
                template_name='hospital_assignment',
                context=context,
                hospital_communication=instance
            )
            
            if notification:
                orchestrator.send_notification(notification)
    
    # Notify first-aider about status changes
    if not created:
        old_instance = EmergencyHospitalCommunication.objects.get(pk=instance.pk)
        
        if old_instance.status != instance.status:
            context = {
                'first_aider_name': instance.first_aider.get_full_name(),
                'hospital_name': instance.hospital.name,
                'status': instance.get_status_display(),
                'alert_id': instance.alert_reference_id
            }
            
            notification = NotificationTemplateService.create_notification_from_template(
                user=instance.first_aider,
                template_name='hospital_ready' if instance.status == 'ready' else 'eta_update',
                context=context,
                hospital_communication=instance
            )
            
            if notification:
                orchestrator.send_notification(notification)

@receiver(pre_save, sender=Notification)
def handle_notification_retry(sender, instance, **kwargs):
    """
    Handle notification retry logic
    """
    if instance.pk:
        try:
            old_instance = Notification.objects.get(pk=instance.pk)
            
            # If status changed from failed to pending, increment retry count
            if (old_instance.status == 'failed' and instance.status == 'pending' and
                instance.retry_count == old_instance.retry_count):
                instance.retry_count += 1
                
        except Notification.DoesNotExist:
            pass