import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from emergencies.models import EmergencyAlert, EmergencySession, EmergencyUpdate
from accounts.models import CustomUser as User

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service for managing emergency alert lifecycle
    """
    
    @staticmethod
    def create_emergency_alert(
        user: User,
        emergency_type: str,
        latitude: float,
        longitude: float,
        description: str = "",
        address: str = "",
        location_id: int = None
    ) -> Optional[EmergencyAlert]:
        """
        Create a new emergency alert
        """
        try:
            with transaction.atomic():
                # Check for recent duplicate alerts (prevent spam)
                recent_alerts = EmergencyAlert.objects.filter(
                    user=user,
                    created_at__gte=timezone.now() - timezone.timedelta(minutes=2),
                    status__in=['pending', 'verified', 'dispatched']
                )
                
                if recent_alerts.exists():
                    logger.warning(f"Duplicate alert attempt by user {user.id}")
                    return recent_alerts.first()
                
                # Create the emergency alert
                alert = EmergencyAlert.objects.create(
                    user=user,
                    emergency_type=emergency_type,
                    current_latitude=latitude,
                    current_longitude=longitude,
                    description=description,
                    address=address,
                    location_id=location_id
                )
                
                # Create initial update
                EmergencyUpdate.objects.create(
                    alert=alert,
                    update_type='created',
                    details={
                        'emergency_type': emergency_type,
                        'coordinates': f"{latitude},{longitude}",
                        'description': description
                    }
                )
                
                # Create emergency session
                session = EmergencySession.objects.create(
                    alert=alert,
                    session_id=f"session_{alert.alert_id}",
                    websocket_channel=f"emergency_{alert.alert_id}"
                )
                
                logger.info(f"Emergency alert created: {alert.alert_id} for user {user.email}")
                return alert
                
        except Exception as e:
            logger.error(f"Failed to create emergency alert: {str(e)}")
            return None
    
    @staticmethod
    def update_alert_location(
        alert_id: str,
        latitude: float,
        longitude: float,
        address: str = ""
    ) -> bool:
        """
        Update the location of an active emergency alert
        """
        try:
            with transaction.atomic():
                alert = EmergencyAlert.objects.get(alert_id=alert_id, is_active=True)
                
                alert.current_latitude = latitude
                alert.current_longitude = longitude
                if address:
                    alert.address = address
                alert.save()
                
                # Update session location tracking
                if hasattr(alert, 'session'):
                    alert.session.location_updates_count += 1
                    alert.session.save()
                
                # Create location update record
                EmergencyUpdate.objects.create(
                    alert=alert,
                    update_type='location_updated',
                    details={
                        'coordinates': f"{latitude},{longitude}",
                        'address': address
                    }
                )
                
                logger.info(f"Location updated for alert {alert_id}")
                return True
                
        except EmergencyAlert.DoesNotExist:
            logger.warning(f"Alert not found or not active: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update alert location: {str(e)}")
            return False
    
    @staticmethod
    def update_alert_status(
        alert_id: str,
        new_status: str,
        user: User = None,
        details: Dict = None
    ) -> bool:
        """
        Update the status of an emergency alert with audit trail
        """
        try:
            with transaction.atomic():
                alert = EmergencyAlert.objects.get(alert_id=alert_id)
                previous_status = alert.status
                
                # Update status and related timestamps
                alert.status = new_status
                
                if new_status == 'verified':
                    alert.verified_at = timezone.now()
                    alert.is_verified = True
                elif new_status == 'dispatched':
                    alert.dispatched_at = timezone.now()
                elif new_status == 'completed':
                    alert.completed_at = timezone.now()
                    alert.is_active = False
                elif new_status == 'cancelled':
                    alert.cancelled_at = timezone.now()
                    alert.is_active = False
                
                alert.save()
                
                # Create status update record
                EmergencyUpdate.objects.create(
                    alert=alert,
                    update_type='status_changed',
                    previous_status=previous_status,
                    new_status=new_status,
                    created_by=user,
                    details=details or {}
                )
                
                logger.info(f"Alert {alert_id} status changed from {previous_status} to {new_status}")
                return True
                
        except EmergencyAlert.DoesNotExist:
            logger.warning(f"Alert not found: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update alert status: {str(e)}")
            return False
    
    @staticmethod
    def cancel_emergency_alert(alert_id: str, user: User, reason: str = "") -> bool:
        """
        Cancel an emergency alert
        """
        try:
            with transaction.atomic():
                alert = EmergencyAlert.objects.get(alert_id=alert_id, user=user)
                
                if alert.status in ['completed', 'cancelled']:
                    logger.warning(f"Alert {alert_id} already in final state: {alert.status}")
                    return False
                
                # Update alert status
                success = AlertService.update_alert_status(
                    alert_id=alert_id,
                    new_status='cancelled',
                    user=user,
                    details={'reason': reason}
                )
                
                if success and hasattr(alert, 'session'):
                    alert.session.is_active = False
                    alert.session.ended_at = timezone.now()
                    alert.session.save()
                
                logger.info(f"Emergency alert cancelled: {alert_id}")
                return success
                
        except EmergencyAlert.DoesNotExist:
            logger.warning(f"Alert not found or user mismatch: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to cancel emergency alert: {str(e)}")
            return False
    
    @staticmethod
    def get_user_emergency_history(user: User, limit: int = 50) -> List[EmergencyAlert]:
        """
        Get user's emergency alert history
        """
        try:
            alerts = EmergencyAlert.objects.filter(
                user=user
            ).select_related('location').prefetch_related('updates')[:limit]
            
            return list(alerts)
            
        except Exception as e:
            logger.error(f"Failed to get emergency history: {str(e)}")
            return []
    
    @staticmethod
    def get_active_emergencies() -> List[EmergencyAlert]:
        """
        Get all active emergency alerts
        """
        try:
            alerts = EmergencyAlert.objects.filter(
                is_active=True
            ).select_related('user', 'location').order_by('-created_at')
            
            return list(alerts)
            
        except Exception as e:
            logger.error(f"Failed to get active emergencies: {str(e)}")
            return []