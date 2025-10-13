import secrets
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, EmergencyAccessLog

class EmergencyAccessService:
    @staticmethod
    def grant_emergency_access(badge_number, reason="", ip_address=None):
        """
        Emergency bypass for critical situations
        - First aiders can access system during emergencies
        - Limited time window
        - Full audit logging
        """
        try:
            user = CustomUser.objects.get(
                badge_number=badge_number, 
                role__in=['first_aider', 'hospital_staff']
            )
            
            access_token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(minutes=15)
            
            emergency_log = EmergencyAccessLog.objects.create(
                user=user,
                access_token=access_token,
                expires_at=expires_at,
                reason=reason,
                ip_address=ip_address
            )
            
            return {
                'access_token': access_token,
                'expires_at': expires_at,
                'user': user
            }
            
        except CustomUser.DoesNotExist:
            return None
    
    @staticmethod
    def validate_emergency_access(access_token):
        """Validate emergency access token"""
        try:
            emergency_log = EmergencyAccessLog.objects.get(access_token=access_token)
            if emergency_log.is_valid():
                return emergency_log.user
            return None
        except EmergencyAccessLog.DoesNotExist:
            return None