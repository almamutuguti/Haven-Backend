import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from typing import List, Dict, Optional
from .models import (
    Notification,
    NotificationTemplate,
    SMSLog,
    PushNotificationLog,
    EmailLog,
    UserNotificationPreference
)

logger = logging.getLogger(__name__)

class BaseNotificationService:
    """Base class for all notification services"""
    
    def __init__(self):
        self.provider_name = "base"
    
    def send(self, notification: Notification) -> bool:
        """Send notification - to be implemented by subclasses"""
        raise NotImplementedError
    
    def handle_response(self, notification: Notification, response, log_model=None):
        """Handle provider response and update notification status"""
        try:
            if response.get('success', False):
                notification.mark_as_sent()
                
                # Create delivery log if log model provided
                if log_model:
                    log_model.objects.create(
                        notification=notification,
                        **response.get('log_data', {})
                    )
                
                logger.info(f"{self.provider_name.upper()} notification sent: {notification.id}")
                return True
            else:
                notification.status = 'failed'
                notification.save()
                logger.error(f"{self.provider_name.upper()} notification failed: {response.get('error')}")
                return False
                
        except Exception as e:
            notification.status = 'failed'
            notification.save()
            logger.error(f"Error handling {self.provider_name} response: {str(e)}")
            return False

class SMSService(BaseNotificationService):
    """
    SMS notification service using Africa's Talking
    """
    
    def __init__(self):
        super().__init__()
        self.provider_name = "africas_talking"
        self.api_key = getattr(settings, 'AFRICAS_TALKING_API_KEY', '')
        self.username = getattr(settings, 'AFRICAS_TALKING_USERNAME', '')
        self.base_url = 'https://api.africastalking.com/version1'
    
    def send(self, notification: Notification) -> bool:
        """Send SMS via Africa's Talking"""
        try:
            # Get user's phone number
            phone = notification.user.phone
            if not phone:
                logger.error(f"No phone number for user: {notification.user.id}")
                return False
            
            # Check user preferences
            if not self._can_send_sms(notification.user):
                logger.info(f"SMS disabled for user: {notification.user.id}")
                return False
            
            # Prepare SMS data
            headers = {
                'ApiKey': self.api_key,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'username': self.username,
                'to': phone,
                'message': notification.message,
                'from': getattr(settings, 'SMS_SENDER_ID', 'HAVEN')
            }
            
            # Make API request
            response = requests.post(
                f"{self.base_url}/messaging",
                data=data,
                headers=headers,
                timeout=30
            )
            
            return self._handle_sms_response(notification, response)
            
        except Exception as e:
            logger.error(f"SMS sending error: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def _can_send_sms(self, user) -> bool:
        """Check if SMS can be sent to user"""
        try:
            preferences = user.notification_preferences
            return preferences.sms_enabled and not preferences.is_quiet_hours()
        except UserNotificationPreference.DoesNotExist:
            return True  # Default to enabled if no preferences
    
    def _handle_sms_response(self, notification: Notification, response) -> bool:
        """Handle Africa's Talking SMS response"""
        try:
            response_data = response.json()
            
            if response.status_code == 201 and response_data.get('SMSMessageData'):
                message_data = response_data['SMSMessageData']
                recipients = message_data.get('Recipients', [])
                
                if recipients:
                    recipient = recipients[0]
                    log_data = {
                        'phone': recipient.get('number'),
                        'message': notification.message,
                        'message_id': recipient.get('messageId', ''),
                        'provider_message_id': recipient.get('messageId', ''),
                        'status': recipient.get('status', 'sent'),
                        'cost': float(recipient.get('cost', 0)),
                    }
                    
                    return self.handle_response(
                        notification,
                        {'success': True, 'log_data': log_data},
                        SMSLog
                    )
            
            # If we get here, something went wrong
            error_msg = response_data.get('SMSMessageData', {}).get('Message', 'Unknown error')
            return self.handle_response(
                notification,
                {'success': False, 'error': error_msg}
            )
            
        except Exception as e:
            logger.error(f"Error handling SMS response: {str(e)}")
            return False

class PushNotificationService(BaseNotificationService):
    """
    Push notification service using FCM (Firebase Cloud Messaging)
    """
    
    def __init__(self):
        super().__init__()
        self.provider_name = "fcm"
        self.server_key = getattr(settings, 'FCM_SERVER_KEY', '')
        self.fcm_url = 'https://fcm.googleapis.com/fcm/send'
    
    def send(self, notification: Notification) -> bool:
        """Send push notification via FCM"""
        try:
            # In a real implementation, you'd get device tokens from user profile
            device_tokens = self._get_user_device_tokens(notification.user)
            if not device_tokens:
                logger.info(f"No device tokens for user: {notification.user.id}")
                return False
            
            # Check user preferences
            if not self._can_send_push(notification.user):
                logger.info(f"Push disabled for user: {notification.user.id}")
                return False
            
            # Send to all device tokens
            success = False
            for device_token in device_tokens:
                if self._send_to_device(notification, device_token):
                    success = True
            
            return success
            
        except Exception as e:
            logger.error(f"Push notification error: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def _get_user_device_tokens(self, user) -> List[str]:
        """Get user's device tokens for push notifications"""
        # This would typically come from a UserDevice model
        # For now, return empty list - you'd implement this based on your device tracking
        return []
    
    def _can_send_push(self, user) -> bool:
        """Check if push can be sent to user"""
        try:
            preferences = user.notification_preferences
            return preferences.push_enabled and not preferences.is_quiet_hours()
        except UserNotificationPreference.DoesNotExist:
            return True
    
    def _send_to_device(self, notification: Notification, device_token: str) -> bool:
        """Send push to specific device"""
        try:
            headers = {
                'Authorization': f'key={self.server_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'to': device_token,
                'notification': {
                    'title': notification.title,
                    'body': notification.message,
                    'sound': 'default',
                    'badge': '1',
                },
                'data': {
                    'notification_id': str(notification.id),
                    'type': notification.notification_type,
                    'emergency_alert_id': str(notification.emergency_alert.id) if notification.emergency_alert else '',
                    'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                },
                'priority': 'high' if notification.priority in ['critical', 'high'] else 'normal'
            }
            
            response = requests.post(
                self.fcm_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            return self._handle_push_response(notification, response, device_token)
            
        except Exception as e:
            logger.error(f"Error sending to device {device_token}: {str(e)}")
            return False
    
    def _handle_push_response(self, notification: Notification, response, device_token: str) -> bool:
        """Handle FCM response"""
        try:
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('success') == 1:
                log_data = {
                    'device_token': device_token,
                    'platform': 'android',  # You'd determine this from device info
                    'payload': {
                        'title': notification.title,
                        'message': notification.message
                    },
                    'provider_message_id': response_data.get('message_id', ''),
                    'status': 'sent',
                }
                
                return self.handle_response(
                    notification,
                    {'success': True, 'log_data': log_data},
                    PushNotificationLog
                )
            else:
                error_msg = response_data.get('results', [{}])[0].get('error', 'Unknown error')
                return self.handle_response(
                    notification,
                    {'success': False, 'error': error_msg}
                )
                
        except Exception as e:
            logger.error(f"Error handling push response: {str(e)}")
            return False

class EmailService(BaseNotificationService):
    """
    Email notification service
    """
    
    def __init__(self):
        super().__init__()
        self.provider_name = "email"
    
    def send(self, notification: Notification) -> bool:
        """Send email notification"""
        try:
            # Check if user has email
            if not notification.user.email:
                logger.info(f"No email for user: {notification.user.id}")
                return False
            
            # Check user preferences
            if not self._can_send_email(notification.user):
                logger.info(f"Email disabled for user: {notification.user.id}")
                return False
            
            # In a real implementation, you'd use Django's send_mail or a service like SendGrid
            # For now, we'll simulate success
            log_data = {
                'recipient': notification.user.email,
                'subject': notification.title,
                'html_content': f"<p>{notification.message}</p>",
                'text_content': notification.message,
                'status': 'sent',
            }
            
            return self.handle_response(
                notification,
                {'success': True, 'log_data': log_data},
                EmailLog
            )
            
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def _can_send_email(self, user) -> bool:
        """Check if email can be sent to user"""
        try:
            preferences = user.notification_preferences
            return preferences.email_enabled
        except UserNotificationPreference.DoesNotExist:
            return True

class VoiceCallService(BaseNotificationService):
    """
    Voice call notification service
    """
    
    def __init__(self):
        super().__init__()
        self.provider_name = "voice"
    
    def send(self, notification: Notification) -> bool:
        """Send voice call notification"""
        try:
            # Check user preferences for voice calls
            if not self._can_send_voice(notification.user):
                logger.info(f"Voice calls disabled for user: {notification.user.id}")
                return False
            
            # In a real implementation, you'd integrate with a voice service like Africa's Talking Voice
            # or Twilio
            logger.info(f"Voice call would be sent to {notification.user.phone}")
            
            # For now, mark as sent (simulate success)
            notification.mark_as_sent()
            return True
            
        except Exception as e:
            logger.error(f"Voice call error: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def _can_send_voice(self, user) -> bool:
        """Check if voice call can be sent to user"""
        try:
            preferences = user.notification_preferences
            return preferences.voice_enabled and not preferences.is_quiet_hours()
        except UserNotificationPreference.DoesNotExist:
            return True

class NotificationOrchestrator:
    """
    Orchestrates sending notifications through appropriate channels
    """
    
    def __init__(self):
        self.services = {
            'sms': SMSService(),
            'push': PushNotificationService(),
            'email': EmailService(),
            'voice': VoiceCallService(),
        }
    
    def send_notification(self, notification: Notification) -> bool:
        """Send notification through specified channel"""
        service = self.services.get(notification.channel)
        if not service:
            logger.error(f"Unsupported notification channel: {notification.channel}")
            return False
        
        return service.send(notification)
    
    def send_bulk_notifications(self, notifications: List[Notification]) -> Dict[str, int]:
        """Send multiple notifications and return results"""
        results = {
            'total': len(notifications),
            'success': 0,
            'failed': 0
        }
        
        for notification in notifications:
            if self.send_notification(notification):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def send_emergency_alert(self, emergency_alert, users: List) -> Dict[str, int]:
        """Send emergency alerts to multiple users"""
        notifications = []
        
        for user in users:
            notification = Notification.objects.create(
                user=user,
                title="Emergency Alert",
                message=f"Emergency reported in your area. Alert ID: {emergency_alert.alert_id}",
                notification_type='emergency_alert',
                priority='critical',
                channel='push',  # Default channel for emergency alerts
                emergency_alert=emergency_alert
            )
            notifications.append(notification)
        
        return self.send_bulk_notifications(notifications)

class NotificationTemplateService:
    """
    Service for handling notification templates
    """
    
    @staticmethod
    def render_template(template_name: str, context: Dict) -> Dict[str, str]:
        """Render notification template with context"""
        try:
            template = NotificationTemplate.objects.get(
                name=template_name,
                is_active=True
            )
            
            title = template.title_template.format(**context)
            message = template.message_template.format(**context)
            
            return {
                'title': title,
                'message': message,
                'priority': template.priority,
                'channel': template.channel
            }
            
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_name}")
            return {}
    
    @staticmethod
    def create_notification_from_template(
        user,
        template_name: str,
        context: Dict,
        emergency_alert=None,
        hospital_communication=None
    ) -> Optional[Notification]:
        """Create notification from template"""
        template_data = NotificationTemplateService.render_template(template_name, context)
        
        if not template_data:
            return None
        
        return Notification.objects.create(
            user=user,
            title=template_data['title'],
            message=template_data['message'],
            notification_type=template_name,
            priority=template_data['priority'],
            channel=template_data['channel'],
            emergency_alert=emergency_alert,
            hospital_communication=hospital_communication,
            metadata={'template_used': template_name, 'context': context}
        )