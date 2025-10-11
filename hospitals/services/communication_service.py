import logging
import requests
import json
from typing import Dict, Optional, List
from django.conf import settings
from django.utils import timezone

from hospitals.models import Hospital, EmergencyResponse

logger = logging.getLogger(__name__)


class CommunicationService:
    """
    Service for communicating with hospitals via multiple channels
    """
    
    @staticmethod
    def send_emergency_alert_to_hospital(
        hospital_id: int,
        emergency_data: Dict,
        communication_channels: List[str] = None
    ) -> Dict:
        """
        Send emergency alert to hospital through multiple channels
        """
        if communication_channels is None:
            communication_channels = ['api', 'sms']  # Default channels
        
        results = {}
        
        for channel in communication_channels:
            try:
                if channel == 'api':
                    results['api'] = CommunicationService._send_via_api(hospital_id, emergency_data)
                elif channel == 'sms':
                    results['sms'] = CommunicationService._send_via_sms(hospital_id, emergency_data)
                elif channel == 'webhook':
                    results['webhook'] = CommunicationService._send_via_webhook(hospital_id, emergency_data)
                else:
                    results[channel] = {'success': False, 'error': f'Unknown channel: {channel}'}
                    
            except Exception as e:
                logger.error(f"Failed to send via {channel}: {str(e)}")
                results[channel] = {'success': False, 'error': str(e)}
        
        # Log the communication attempt
        CommunicationService._log_communication_attempt(hospital_id, emergency_data, results)
        
        return results
    
    @staticmethod
    def _send_via_api(hospital_id: int, emergency_data: Dict) -> Dict:
        """
        Send emergency alert via hospital API
        """
        try:
            hospital = Hospital.objects.get(id=hospital_id)
            
            # Prepare API payload
            payload = CommunicationService._prepare_api_payload(emergency_data)
            
            # TODO: Implement actual hospital API integration
            # This would vary based on hospital system integration
            
            # Mock API call for now
            response = {
                'success': True,
                'message': 'Alert sent via API',
                'response_time': 2.5,  # seconds
                'hospital_system_id': 'mock_system_123'
            }
            
            # Log successful response
            CommunicationService._log_emergency_response(
                hospital, emergency_data, 'api', True, response
            )
            
            return response
            
        except Exception as e:
            logger.error(f"API communication failed: {str(e)}")
            
            # Log failed response
            CommunicationService._log_emergency_response(
                Hospital.objects.get(id=hospital_id), emergency_data, 'api', False, {'error': str(e)}
            )
            
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_via_sms(hospital_id: int, emergency_data: Dict) -> Dict:
        """
        Send emergency alert via SMS
        """
        try:
            hospital = Hospital.objects.get(id=hospital_id)
            
            if not hospital.emergency_phone:
                return {'success': False, 'error': 'No emergency phone number available'}
            
            # Prepare SMS message
            message = CommunicationService._prepare_sms_message(emergency_data)
            
            # TODO: Integrate with actual SMS service
            # This would use services like Africa's Talking, Twilio, etc.
            
            # Mock SMS sending for now
            response = {
                'success': True,
                'message': 'SMS sent successfully',
                'recipient': hospital.emergency_phone,
                'message_id': 'mock_sms_123'
            }
            
            return response
            
        except Exception as e:
            logger.error(f"SMS communication failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_via_webhook(hospital_id: int, emergency_data: Dict) -> Dict:
        """
        Send emergency alert via webhook
        """
        try:
            hospital = Hospital.objects.get(id=hospital_id)
            
            # TODO: Implement webhook URL from hospital configuration
            webhook_url = None  # hospital.webhook_url
            
            if not webhook_url:
                return {'success': False, 'error': 'No webhook URL configured'}
            
            payload = CommunicationService._prepare_webhook_payload(emergency_data)
            
            # Mock webhook call for now
            response = {
                'success': True,
                'message': 'Webhook notification sent',
                'url': webhook_url
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Webhook communication failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _prepare_api_payload(emergency_data: Dict) -> Dict:
        """
        Prepare payload for hospital API integration
        """
        return {
            'emergency_id': emergency_data.get('alert_id'),
            'patient_info': emergency_data.get('patient_info', {}),
            'emergency_type': emergency_data.get('emergency_type'),
            'location': emergency_data.get('location', {}),
            'timestamp': timezone.now().isoformat(),
            'priority': emergency_data.get('priority', 'medium'),
            'additional_notes': emergency_data.get('description', ''),
        }
    
    @staticmethod
    def _prepare_sms_message(emergency_data: Dict) -> str:
        """
        Prepare SMS message for hospital notification
        """
        patient_info = emergency_data.get('patient_info', {})
        location = emergency_data.get('location', {})
        
        message = f"EMERGENCY ALERT\n"
        message += f"Type: {emergency_data.get('emergency_type', 'Medical')}\n"
        message += f"Patient: {patient_info.get('name', 'Unknown')}\n"
        message += f"Location: {location.get('address', 'Unknown')}\n"
        message += f"Priority: {emergency_data.get('priority', 'Medium')}\n"
        message += f"ETA: {emergency_data.get('eta_minutes', 'Unknown')} min\n"
        message += f"ID: {emergency_data.get('alert_id')}"
        
        return message
    
    @staticmethod
    def _prepare_webhook_payload(emergency_data: Dict) -> Dict:
        """
        Prepare payload for webhook notification
        """
        return {
            'event_type': 'emergency_alert',
            'data': emergency_data,
            'sent_at': timezone.now().isoformat(),
            'source': 'Haven Emergency System'
        }
    
    @staticmethod
    def _log_communication_attempt(hospital_id: int, emergency_data: Dict, results: Dict):
        """
        Log communication attempt for auditing
        """
        try:
            hospital = Hospital.objects.get(id=hospital_id)
            
            # Determine if any channel was successful
            any_success = any(result.get('success', False) for result in results.values())
            
            # Log the attempt (you might want to create a separate model for this)
            logger.info(
                f"Emergency communication to {hospital.name}: "
                f"Success={any_success}, Channels={list(results.keys())}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log communication attempt: {str(e)}")
    
    @staticmethod
    def _log_emergency_response(
        hospital: Hospital,
        emergency_data: Dict,
        channel: str,
        success: bool,
        response_data: Dict
    ):
        """
        Log hospital response to emergency
        """
        try:
            response_time = response_data.get('response_time', 0)
            
            EmergencyResponse.objects.create(
                hospital=hospital,
                response_time=response_time,
                accepted_patient=success,  # Assume success means accepted
                beds_available_at_response=hospital.capacity.available_beds if hasattr(hospital, 'capacity') else 0,
                emergency_beds_available_at_response=hospital.capacity.emergency_beds_available if hasattr(hospital, 'capacity') else 0,
                alert_received_at=timezone.now() - timezone.timedelta(seconds=response_time)
            )
            
        except Exception as e:
            logger.error(f"Failed to log emergency response: {str(e)}")
    
    @staticmethod
    def get_communication_status(alert_id: str) -> Dict:
        """
        Get communication status for an emergency alert
        """
        # TODO: Implement communication status tracking
        # This would query a communication log model
        
        return {
            'alert_id': alert_id,
            'channels_sent': ['api', 'sms'],
            'channels_confirmed': ['sms'],
            'last_update': timezone.now().isoformat(),
            'overall_status': 'delivered'
        }