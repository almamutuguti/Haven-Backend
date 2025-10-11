import logging
import random
from typing import Optional
from django.utils import timezone
from emergencies.models import EmergencyAlert, AlertVerification
# from apps.notifications.services.sms_service import SMSService  # We'll create this later
from emergencies.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class VerificationService:
    """
    Service for emergency alert verification
    """
    
    @staticmethod
    def initiate_verification(alert: EmergencyAlert, method: str = 'sms') -> bool:
        """
        Initiate emergency alert verification
        """
        try:
            if method == 'sms':
                return VerificationService._send_sms_verification(alert)
            elif method == 'call':
                return VerificationService._initiate_call_verification(alert)
            else:
                logger.warning(f"Unsupported verification method: {method}")
                return False
                
        except Exception as e:
            logger.error(f"Verification initiation failed: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms_verification(alert: EmergencyAlert) -> bool:
        """
        Send SMS verification code
        """
        try:
            # Generate verification code
            verification_code = str(random.randint(100000, 999999))
            
            # Create verification record
            verification = AlertVerification.objects.create(
                alert=alert,
                verification_method='sms',
                verification_code=verification_code
            )
            
            # Send SMS (mock implementation for now)
            user_phone = alert.user.phone_number  # Assuming user has phone_number field
            message = f"Emergency alert verification code: {verification_code}. Reply with this code to confirm your emergency."
            
            # TODO: Integrate with actual SMS service
            # SMSService.send_sms(user_phone, message)
            logger.info(f"SMS verification sent to {user_phone}: {message}")
            
            # Increment verification attempts
            alert.verification_attempts += 1
            alert.save()
            
            return True
            
        except Exception as e:
            logger.error(f"SMS verification failed: {str(e)}")
            return False
    
    @staticmethod
    def _initiate_call_verification(alert: EmergencyAlert) -> bool:
        """
        Initiate call verification (to be implemented)
        """
        # TODO: Implement call verification
        logger.info(f"Call verification initiated for alert {alert.alert_id}")
        return True
    
    @staticmethod
    def verify_code(alert_id: str, verification_code: str) -> bool:
        """
        Verify a provided verification code
        """
        try:
            alert = EmergencyAlert.objects.get(alert_id=alert_id)
            
            # Find pending verification
            verification = AlertVerification.objects.filter(
                alert=alert,
                is_successful=False,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
            ).first()
            
            if not verification:
                logger.warning(f"No pending verification found for alert {alert_id}")
                return False
            
            # Check code match
            if verification.verification_code == verification_code:
                verification.is_successful = True
                verification.response_received = True
                verification.responded_at = timezone.now()
                verification.save()
                
                # Update alert status

                AlertService.update_alert_status(
                    alert_id,
                    'verified',
                    details={'verification_method': 'sms_code'}
                )
                
                logger.info(f"Alert {alert_id} successfully verified via SMS code")
                return True
            else:
                verification.response_received = True
                verification.save()
                
                logger.warning(f"Invalid verification code for alert {alert_id}")
                return False
                
        except EmergencyAlert.DoesNotExist:
            logger.warning(f"Alert not found: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return False