# apps/hospital_comms/services.py
import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from .models import (
    EmergencyHospitalCommunication, 
    CommunicationLog,
    HospitalPreparationChecklist,
    FirstAiderAssessment
)
from hospitals.models import Hospital
from notifications.services import SMSService

logger = logging.getLogger(__name__)

class HospitalCommunicationService:
    """
    Service for handling hospital communication operations
    """
    
    def __init__(self, communication):
        self.communication = communication
        self.hospital = communication.hospital
    
    def send_emergency_alert(self):
        """
        Send emergency alert to hospital through multiple channels
        """
        try:
            # Update communication status
            self.communication.status = 'sent'
            self.communication.sent_to_hospital_at = timezone.now()
            self.communication.communication_attempts += 1
            self.communication.save()
            
            # Try different communication channels
            channels = self._get_communication_channels()
            
            for channel in channels:
                success = self._send_via_channel(channel)
                if success:
                    logger.info(f"Emergency alert sent to {self.hospital.name} via {channel}")
                    self._log_communication(channel, 'outgoing', 'emergency_alert', True)
                    return True
            
            # If all channels fail
            self.communication.status = 'failed'
            self.communication.save()
            self._log_communication('api', 'outgoing', 'emergency_alert', False, "All communication channels failed")
            return False
            
        except Exception as e:
            logger.error(f"Error sending emergency alert: {str(e)}")
            self.communication.status = 'failed'
            self.communication.save()
            self._log_communication('api', 'outgoing', 'emergency_alert', False, str(e))
            return False
    
    def _get_communication_channels(self):
        """Get available communication channels for the hospital"""
        channels = ['api']  # Always try API first
        
        if self.hospital.sms_notifications:
            channels.append('sms')
        if self.hospital.webhook_url:
            channels.append('webhook')
        if self.hospital.phone_number:
            channels.append('voice')
        
        return channels
    
    def _send_via_channel(self, channel):
        """Send message via specific channel"""
        try:
            if channel == 'api':
                return self._send_via_api()
            elif channel == 'sms':
                return self._send_via_sms()
            elif channel == 'webhook':
                return self._send_via_webhook()
            elif channel == 'voice':
                return self._send_via_voice()
            return False
        except Exception as e:
            logger.error(f"Error sending via {channel}: {str(e)}")
            return False
    
    def _send_via_api(self):
        """Send via hospital API integration"""
        try:
            # Prepare emergency data packet
            data = self._prepare_emergency_data_packet()
            
            # Make API request to hospital
            response = requests.post(
                f"{self.hospital.api_base_url}/emergency/alerts",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.hospital.api_key}"
                },
                timeout=10  # 10 second timeout
            )
            
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return False
    
    def _send_via_sms(self):
        """Send via SMS to hospital emergency number"""
        try:
            
            
            message = self._prepare_sms_message()
            sms_service = SMSService()
            
            # Send to hospital emergency contact
            success = sms_service.send_sms(
                to=self.hospital.emergency_contact_number,
                message=message
            )
            
            return success
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return False
    
    def _send_via_webhook(self):
        """Send via webhook to hospital system"""
        try:
            data = self._prepare_emergency_data_packet()
            
            response = requests.post(
                self.hospital.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Webhook request failed: {str(e)}")
            return False
    
    def _send_via_voice(self):
        """Send via voice call (would integrate with telephony service)"""
        # This would integrate with a voice call service like Twilio
        # For now, return True as placeholder
        return True
    
    def _prepare_emergency_data_packet(self):
        """Prepare comprehensive emergency data packet for hospital"""
        return {
            'alert_id': self.communication.alert_reference_id,
            'hospital_id': str(self.hospital.id),
            'timestamp': self.communication.created_at.isoformat(),
            'priority': self.communication.priority,
            'patient_info': {
                'name': self.communication.victim_name,
                'age': self.communication.victim_age,
                'gender': self.communication.victim_gender,
            },
            'emergency_details': {
                'chief_complaint': self.communication.chief_complaint,
                'vital_signs': self.communication.vital_signs,
                'initial_assessment': self.communication.initial_assessment,
                'first_aid_provided': self.communication.first_aid_provided,
            },
            'logistics': {
                'estimated_arrival_minutes': self.communication.estimated_arrival_minutes,
                'required_specialties': self.communication.required_specialties,
                'equipment_needed': self.communication.equipment_needed,
                'blood_type_required': self.communication.blood_type_required,
            },
            'first_aider_info': {
                'name': self.communication.first_aider.get_full_name(),
                'contact': self.communication.first_aider.phone_number,
            }
        }
    
    def _prepare_sms_message(self):
        """Prepare SMS message for hospital"""
        return (
            f"EMERGENCY ALERT - {self.communication.alert_reference_id}\n"
            f"Priority: {self.communication.priority.upper()}\n"
            f"Patient: {self.communication.victim_name}, {self.communication.victim_age}\n"
            f"Complaint: {self.communication.chief_complaint}\n"
            f"ETA: {self.communication.estimated_arrival_minutes} mins\n"
            f"First Aider: {self.communication.first_aider.get_full_name()}\n"
            f"Login to Haven for details"
        )
    
    def _log_communication(self, channel, direction, message_type, success, error_message=""):
        """Log communication attempt"""
        CommunicationLog.objects.create(
            communication=self.communication,
            channel=channel,
            direction=direction,
            message_type=message_type,
            message_content=self._prepare_sms_message() if channel == 'sms' else str(self._prepare_emergency_data_packet()),
            message_data=self._prepare_emergency_data_packet(),
            is_successful=success,
            error_message=error_message,
            response_code="200" if success else "500",
            delivered_at=timezone.now() if success else None
        )

class HospitalResponseService:
    """
    Service for handling hospital responses and acknowledgments
    """
    
    def __init__(self, communication):
        self.communication = communication
    
    def acknowledge_emergency(self, acknowledged_by, preparation_notes=""):
        """
        Handle hospital acknowledgment of emergency
        """
        try:
            self.communication.status = 'acknowledged'
            self.communication.hospital_acknowledged_at = timezone.now()
            self.communication.hospital_acknowledged_by = acknowledged_by
            self.communication.hospital_preparation_notes = preparation_notes
            self.communication.save()
            
            # Create preparation checklist
            self._create_preparation_checklist()
            
            # Log the acknowledgment
            CommunicationLog.objects.create(
                communication=self.communication,
                channel='api',
                direction='incoming',
                message_type='acknowledgment',
                message_content=f"Emergency acknowledged by {acknowledged_by.get_full_name()}",
                message_data={'acknowledged_by': str(acknowledged_by.id), 'notes': preparation_notes},
                is_successful=True,
                response_code="200",
                response_received_at=timezone.now()
            )
            
            # Notify first aider about acknowledgment
            self._notify_first_aider_about_acknowledgment()
            
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging emergency: {str(e)}")
            return False
    
    def update_preparation_status(self, preparation_data):
        """
        Update hospital preparation status
        """
        try:
            # Update main communication
            for field, value in preparation_data.items():
                if hasattr(self.communication, field):
                    setattr(self.communication, field, value)
            
            # Check if hospital is fully ready
            if self._is_hospital_ready():
                self.communication.status = 'ready'
                self.communication.hospital_ready_at = timezone.now()
            
            self.communication.save()
            
            # Update checklist if exists
            self._update_preparation_checklist(preparation_data)
            
            # Log preparation update
            CommunicationLog.objects.create(
                communication=self.communication,
                channel='api',
                direction='incoming',
                message_type='preparation_update',
                message_content=f"Hospital preparation updated: {preparation_data}",
                message_data=preparation_data,
                is_successful=True,
                response_received_at=timezone.now()
            )
            
            # Notify first aider about preparation progress
            self._notify_first_aider_about_preparation()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating preparation status: {str(e)}")
            return False
    
    def _create_preparation_checklist(self):
        """Create initial hospital preparation checklist"""
        if not hasattr(self.communication, 'preparation_checklist'):
            HospitalPreparationChecklist.objects.create(
                communication=self.communication
            )
    
    def _update_preparation_checklist(self, preparation_data):
        """Update preparation checklist based on hospital updates"""
        try:
            checklist = self.communication.preparation_checklist
            
            # Map communication fields to checklist fields
            field_mapping = {
                'doctors_ready': 'emergency_doctor_assigned',
                'nurses_ready': 'nursing_team_ready',
                'equipment_ready': 'vital_monitors_ready',  # Simplified mapping
                'blood_available': 'blood_products_available',
            }
            
            for comm_field, checklist_field in field_mapping.items():
                if comm_field in preparation_data and hasattr(checklist, checklist_field):
                    setattr(checklist, checklist_field, preparation_data[comm_field])
            
            checklist.save()
            
        except ObjectDoesNotExist:
            # Checklist doesn't exist yet, create it
            self._create_preparation_checklist()
    
    def _is_hospital_ready(self):
        """Check if hospital is fully prepared"""
        required_fields = ['doctors_ready', 'nurses_ready', 'equipment_ready', 'bed_ready']
        return all(getattr(self.communication, field, False) for field in required_fields)
    
    def _notify_first_aider_about_acknowledgment(self):
        """Notify first aider that hospital has acknowledged the emergency"""
        # This would integrate with your notification system
        logger.info(f"Notifying first aider {self.communication.first_aider} about hospital acknowledgment")
    
    def _notify_first_aider_about_preparation(self):
        """Notify first aider about hospital preparation progress"""
        # This would integrate with your notification system
        logger.info(f"Notifying first aider {self.communication.first_aider} about preparation progress")

class RetryService:
    """
    Service for handling failed communication retries
    """
    
    @staticmethod
    def retry_failed_communications():
        """
        Retry failed communications with exponential backoff
        """
        retry_threshold = timezone.now() - timedelta(minutes=5)
        
        failed_comms = EmergencyHospitalCommunication.objects.filter(
            status__in=['failed', 'pending'],
            communication_attempts__lt=3,
            created_at__gte=retry_threshold
        )
        
        for comm in failed_comms:
            # Calculate next retry time with exponential backoff
            retry_delay = 2 ** comm.communication_attempts  # 2, 4, 8 minutes
            next_retry_time = comm.last_communication_attempt + timedelta(minutes=retry_delay)
            
            if timezone.now() >= next_retry_time:
                service = HospitalCommunicationService(comm)
                service.send_emergency_alert()