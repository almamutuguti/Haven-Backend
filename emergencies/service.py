# apps/emergencies/services/alert_service.py
import logging
from django.db import transaction
from django.utils import timezone
from .models import EmergencyAlert, EmergencyStatusUpdate, EmergencyLocationUpdate

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self):
        self.hospital_discovery = None
        self.sms_service = None
        self.push_service = None
    
    def create_emergency_alert(self, first_aider, emergency_data):
        """Create a new emergency alert"""
        try:
            with transaction.atomic():
                # Create emergency alert
                alert = EmergencyAlert.objects.create(
                    first_aider=first_aider,
                    **emergency_data
                )
                
                # Create initial status update
                EmergencyStatusUpdate.objects.create(
                    emergency=alert,
                    user=first_aider,
                    status='pending',
                    notes='Emergency alert created'
                )
                
                # Set placeholder hospital name
                alert.assigned_hospital_name = "Hospital assignment pending"
                alert.save()
                
                logger.info(f"Emergency alert created: {alert.id} by {first_aider.badge_number}")
                return alert
                
        except Exception as e:
            logger.error(f"Error creating emergency alert: {str(e)}")
            raise
    
    def update_emergency_status(self, alert, new_status, user, notes=""):
        """Update emergency status and create audit trail"""
        try:
            with transaction.atomic():
                # Create status update
                status_update = EmergencyStatusUpdate.objects.create(
                    emergency=alert,
                    user=user,
                    status=new_status,
                    notes=notes
                )
                
                # Update alert timestamps
                if new_status == 'dispatched' and not alert.dispatched_at:
                    alert.dispatched_at = timezone.now()
                elif new_status == 'arrived' and not alert.arrived_at:
                    alert.arrived_at = timezone.now()
                elif new_status == 'completed' and not alert.completed_at:
                    alert.completed_at = timezone.now()
                
                alert.status = new_status
                alert.save()
                
                logger.info(f"Emergency {alert.id} status updated to {new_status} by {user.badge_number}")
                return status_update
                
        except Exception as e:
            logger.error(f"Error updating emergency status: {str(e)}")
            raise
    
    def update_emergency_location(self, alert, latitude, longitude):
        """Update emergency location for real-time tracking"""
        try:
            location_update = EmergencyLocationUpdate.objects.create(
                emergency=alert,
                latitude=latitude,
                longitude=longitude
            )
            
            logger.info(f"Emergency {alert.id} location updated: {latitude}, {longitude}")
            return location_update
            
        except Exception as e:
            logger.error(f"Error updating emergency location: {str(e)}")
            raise
    
    def get_emergency_history(self, user):
        """Get emergency history based on user role"""
        try:
            if user.user_type == 'first_aider':
                emergencies = EmergencyAlert.objects.filter(first_aider=user)
            else:
                emergencies = EmergencyAlert.objects.none()
            
            return emergencies.order_by('-created_at')
            
        except Exception as e:
            logger.error(f"Error getting emergency history: {str(e)}")
            raise
    
    def can_user_access_emergency(self, user, emergency):
        """Check if user has permission to access this emergency"""
        if user.user_type == 'system_admin':
            return True
        elif user.user_type == 'first_aider' and emergency.first_aider == user:
            return True
        return False