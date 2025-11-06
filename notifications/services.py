from email.message import EmailMessage
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

from django.core.mail import send_mail

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
    Real Africa's Talking SMS Service
    """
    
    def __init__(self):
        super().__init__()
        self.provider_name = "africas_talking"
        self.api_key = getattr(settings, 'AFRICAS_TALKING_API_KEY')
        self.username = getattr(settings, 'AFRICAS_TALKING_USERNAME')
        self.base_url = 'https://api.africastalking.com/version1/messaging/'
        
        # Validate credentials on init
        if not self._validate_credentials():
            raise Exception("Africa's Talking credentials are invalid")
    
    def _validate_credentials(self):
        """Validate credentials are working"""
        if not self.api_key or not self.username:
            logger.error("Missing Africa's Talking credentials")
            return False
            
        headers = {'ApiKey': self.api_key, 'Accept': 'application/json'}
        try:
            response = requests.get(
                f'https://api.africastalking.com/version1/user?username={self.username}',
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                logger.info("Africa's Talking credentials validated successfully")
                return True
            else:
                logger.error(f"Credentials validation failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Credentials validation error: {str(e)}")
            return False
    
    def send(self, notification: Notification) -> bool:
        """Send real SMS via Africa's Talking"""
        try:
            # Get and validate phone number
            phone = self._format_phone_number(notification.user.phone)
            if not phone:
                logger.error(f"Invalid phone number for user {notification.user.id}")
                return False
            
            # Check user preferences
            if not self._can_send_sms(notification.user):
                logger.info(f"SMS disabled for user {notification.user.id}")
                return False
            
            # Prepare the request
            headers = {
                'ApiKey': self.api_key,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'username': self.username,
                'to': phone,
                'message': self._format_sms_message(notification),
                'from': getattr(settings, 'SMS_SENDER_ID', 'HAVEN')
            }
            
            logger.info(f"Sending SMS to {phone}: {data['message'][:50]}...")
            
            # Make API request
            response = requests.post(
                self.base_url,
                data=data,
                headers=headers,
                timeout=30
            )
            
            return self._handle_api_response(notification, response, phone)
            
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for Africa's Talking"""
        if not phone:
            return None
        
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, phone))
        
        # Convert to international format
        if cleaned.startswith('0') and len(cleaned) == 10:
            # 0712345678 -> 254712345678
            return '254' + cleaned[1:]
        elif cleaned.startswith('254') and len(cleaned) == 12:
            # 254712345678 -> 254712345678 (already correct)
            return cleaned
        elif cleaned.startswith('7') and len(cleaned) == 9:
            # 712345678 -> 254712345678
            return '254' + cleaned
        else:
            logger.error(f"Unrecognized phone format: {phone} -> {cleaned}")
            return None
    
    def _format_sms_message(self, notification: Notification) -> str:
        """Format SMS message (max 160 chars)"""
        message = notification.message
        
        # Add priority prefix
        if notification.priority == 'critical':
            message = f"URGENT: {message}"
        elif notification.priority == 'high':
            message = f"IMPORTANT: {message}"
        
        # Truncate if too long
        if len(message) > 160:
            message = message[:157] + "..."
        
        return message
    
    def _handle_api_response(self, notification: Notification, response, phone: str) -> bool:
        """Handle Africa's Talking API response"""
        logger.info(f"API Response Status: {response.status_code}")
        logger.info(f"API Response Text: {response.text}")
        
        if response.status_code == 401:
            error_msg = "Authentication failed - check API credentials"
            logger.error(f"{error_msg}")
            return self._handle_failure(notification, error_msg)
        
        if response.status_code != 201:
            error_msg = f"API Error {response.status_code}: {response.text}"
            logger.error(f"{error_msg}")
            return self._handle_failure(notification, error_msg)
        
        try:
            response_data = response.json()
            message_data = response_data.get('SMSMessageData', {})
            recipients = message_data.get('Recipients', [])
            
            if recipients:
                recipient = recipients[0]
                status = recipient.get('status', 'Unknown')
                
                if status in ['Sent', 'Buffered', 'Submitted']:
                    # Success!
                    log_data = {
                        'phone': phone,
                        'message': notification.message,
                        'message_id': recipient.get('messageId', ''),
                        'provider_message_id': recipient.get('messageId', ''),
                        'status': 'sent',
                        'cost': float(recipient.get('cost', 0)),
                        'status_code': status,
                    }
                    
                    logger.info(f"SMS sent successfully to {phone}")
                    return self.handle_response(
                        notification,
                        {'success': True, 'log_data': log_data},
                        SMSLog
                    )
                else:
                    error_msg = f"SMS failed with status: {status}"
                    logger.error(f"{error_msg}")
                    return self._handle_failure(notification, error_msg)
            else:
                error_msg = message_data.get('Message', 'No recipients in response')
                logger.error(f"{error_msg}")
                return self._handle_failure(notification, error_msg)
                
        except Exception as e:
            error_msg = f"Error parsing API response: {str(e)}"
            logger.error(f"{error_msg}")
            return self._handle_failure(notification, error_msg)
    
    def _handle_failure(self, notification: Notification, error_msg: str) -> bool:
        """Handle failed SMS sending"""
        notification.status = 'failed'
        notification.save()
        return self.handle_response(
            notification,
            {'success': False, 'error': error_msg}
        )
    
    def _can_send_sms(self, user) -> bool:
        """Check if SMS can be sent to user"""
        try:
            preferences = UserNotificationPreference.objects.get(user=user)
            return preferences.sms_enabled and not preferences.is_quiet_hours()
        except UserNotificationPreference.DoesNotExist:
            return True
        

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
        """Send actual email notification"""
        try:
            # Check if user has email
            if not notification.user.email:
                logger.info(f"No email for user: {notification.user.id}")
                return False
            
            # Check user preferences
            if not self._can_send_email(notification.user):
                logger.info(f"Email disabled for user: {notification.user.id}")
                return False
            
            # Prepare email content
            subject = self._format_subject(notification)
            message = self._format_message(notification)
            
            # Method 1: Using send_mail (Simpler)
            sent_count = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.user.email],
                fail_silently=False,
            )
            
            if sent_count > 0:
                log_data = {
                    'recipient': notification.user.email,
                    'subject': subject,
                    'text_content': message,
                    'status': 'sent',
                    'provider_message_id': f"email_{notification.id}",
                }
                
                logger.info(f"Email sent successfully to {notification.user.email}")
                return self.handle_response(
                    notification,
                    {'success': True, 'log_data': log_data},
                    EmailLog
                )
            else:
                logger.error(f"Email sending failed for {notification.user.email}")
                return self.handle_response(
                    notification,
                    {'success': False, 'error': 'Email sending failed - no emails sent'}
                )
            
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def _format_subject(self, notification: Notification) -> str:
        """Format email subject"""
        priority_prefix = {
            'critical': 'critical ',
            'high': 'high',
            'medium': 'medium ',
            'low': 'low'
        }
        
        prefix = priority_prefix.get(notification.priority, '')
        return f"{prefix}{notification.title}"
    
    def _format_message(self, notification: Notification) -> str:
        """Format email message content"""
        user_name = notification.user.get_full_name() or "User"
        
        message_lines = [
            f"Dear {user_name},",
            "",
            notification.message,
            "",
            "---",
            f"Notification Type: {notification.notification_type}",
            f"Priority: {notification.priority}",
            f"Sent: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "This is an automated message from HAVEN Emergency System.",
            "Please do not reply to this email."
        ]
        
        return "\n".join(message_lines)
    
    def _can_send_email(self, user) -> bool:
        """Check if email can be sent to user"""
        try:
            preferences = user.notification_preferences
            return preferences.email_enabled
        except UserNotificationPreference.DoesNotExist:
            return True
        
        
class VoiceCallService(BaseNotificationService):
    """
    Voice call service using Africa's Talking Voice API
    """
    
    def __init__(self):
        super().__init__()
        self.provider_name = "africas_talking_voice"
        self.api_key = getattr(settings, 'AFRICAS_TALKING_API_KEY', '')
        self.username = getattr(settings, 'AFRICAS_TALKING_USERNAME', '')
        self.voice_url = 'https://voice.africastalking.com/call'
        
    def send(self, notification: Notification) -> bool:
        """Send voice call notification"""
        try:
            # Get user's phone number
            phone = self._format_phone_number(notification.user.phone)
            if not phone:
                logger.error(f"No valid phone number for user: {notification.user.id}")
                return False
            
            # Check user preferences
            if not self._can_send_voice(notification.user):
                logger.info(f"Voice calls disabled for user: {notification.user.id}")
                return False
            
            # Validate configuration
            if not self.api_key or not self.username:
                logger.error("Africa's Talking API credentials not configured")
                return False
            
            # Prepare voice call data
            headers = {
                'ApiKey': self.api_key,
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            data = {
                'username': self.username,
                'to': phone,
                'from': getattr(settings, 'SMS_SENDER_ID', 'HAVEN'),
            }
            
            # Make API request to initiate call
            response = requests.post(
                self.voice_url,
                data=data,
                headers=headers,
                timeout=30
            )
            
            return self._handle_voice_response(notification, response, phone)
            
        except Exception as e:
            logger.error(f"Voice call error: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for voice calls (same as SMS)"""
        if not phone:
            return None
        
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        
        if cleaned_phone.startswith('0'):
            cleaned_phone = '254' + cleaned_phone[1:]
        elif cleaned_phone.startswith('254'):
            cleaned_phone = cleaned_phone
        elif cleaned_phone.startswith('+254'):
            cleaned_phone = cleaned_phone[1:]
        else:
            cleaned_phone = '254' + cleaned_phone
        
        return cleaned_phone
    
    def _can_send_voice(self, user) -> bool:
        """Check if voice call can be sent to user"""
        try:
            preferences = UserNotificationPreference.objects.get(user=user)
            return preferences.voice_enabled and not preferences.is_quiet_hours()
        except UserNotificationPreference.DoesNotExist:
            return True
    
    def _handle_voice_response(self, notification: Notification, response, phone: str) -> bool:
        """Handle Africa's Talking Voice response"""
        try:
            if response.status_code != 200:
                logger.error(f"Voice API error: {response.status_code} - {response.text}")
                return self.handle_response(
                    notification,
                    {'success': False, 'error': f"HTTP {response.status_code}"}
                )
            
            response_data = response.json()
            logger.info(f"Voice API Response: {response_data}")
            
            if response_data.get('status') == 'Queued' or response_data.get('errorMessage') is None:
                log_data = {
                    'phone': phone,
                    'message': notification.message,
                    'call_id': response_data.get('entries', [{}])[0].get('sessionId', ''),
                    'status': 'initiated',
                    'provider_message_id': response_data.get('entries', [{}])[0].get('sessionId', ''),
                }
                
                logger.info(f"Voice call initiated to {phone}")
                return self.handle_response(
                    notification,
                    {'success': True, 'log_data': log_data}
                )
            else:
                error_msg = response_data.get('errorMessage', 'Unknown error')
                logger.error(f"Voice call failed: {error_msg}")
                return self.handle_response(
                    notification,
                    {'success': False, 'error': error_msg}
                )
                
        except Exception as e:
            logger.error(f"Error handling voice response: {str(e)}")
            return False

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