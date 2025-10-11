import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
from emergencies.models import EmergencyAlert
from emergencies.services.alert_service import AlertService
# from apps.hospitals.models import Hospital  # We'll create this next
from geolocation.services.distance_service import DistanceService
from geolocation.services.places_service import PlacesService
from geolocation.utils import calculate_distance_haversine

logger = logging.getLogger(__name__)


class EmergencyOrchestrator:
    """
    Orchestrates the entire emergency response workflow
    """
    
    @staticmethod
    def process_emergency_alert(alert_id: str) -> bool:
        """
        Process a new emergency alert through the complete workflow
        """
        try:
            with transaction.atomic():
                alert = EmergencyAlert.objects.get(alert_id=alert_id)
                
                # Step 1: Verify alert
                if not EmergencyOrchestrator._verify_alert(alert):
                    logger.error(f"Alert verification failed for {alert_id}")
                    return False
                
                # Step 2: Find suitable hospitals
                hospitals = EmergencyOrchestrator._find_suitable_hospitals(alert)
                if not hospitals:
                    logger.error(f"No suitable hospitals found for {alert_id}")
                    return False
                
                # Step 3: Select best hospital
                best_hospital = EmergencyOrchestrator._select_best_hospital(alert, hospitals)
                if not best_hospital:
                    logger.error(f"Could not select best hospital for {alert_id}")
                    return False
                
                # Step 4: Dispatch to hospital
                if not EmergencyOrchestrator._dispatch_to_hospital(alert, best_hospital):
                    logger.error(f"Hospital dispatch failed for {alert_id}")
                    return False
                
                logger.info(f"Emergency alert {alert_id} processed successfully")
                return True
                
        except EmergencyAlert.DoesNotExist:
            logger.error(f"Alert not found: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Emergency processing failed: {str(e)}")
            return False
    
    @staticmethod
    def _verify_alert(alert: EmergencyAlert) -> bool:
        """
        Verify the emergency alert through multiple methods
        """
        try:
            # For now, auto-verify critical alerts
            # In production, this would involve SMS/call verification
            if alert.priority in ['critical', 'high']:
                AlertService.update_alert_status(
                    alert.alert_id,
                    'verified',
                    details={'verification_method': 'auto_priority'}
                )
                return True
            
            # For medium/low priority, implement verification logic
            # This could involve sending SMS verification codes, etc.
            AlertService.update_alert_status(
                alert.alert_id,
                'verified',
                details={'verification_method': 'auto'}
            )
            return True
            
        except Exception as e:
            logger.error(f"Alert verification failed: {str(e)}")
            return False
    
    @staticmethod
    def _find_suitable_hospitals(alert: EmergencyAlert) -> List[Dict]:
        """
        Find hospitals suitable for the emergency type and location
        """
        try:
            # Use geolocation service to find nearby hospitals

            
            hospitals = PlacesService.find_nearby_hospitals(
                float(alert.current_latitude),
                float(alert.current_longitude),
                radius=10000  # 10km radius
            )
            
            if not hospitals:
                return []
            
            # Filter hospitals based on emergency type and capabilities
            suitable_hospitals = []
            for hospital in hospitals:
                if EmergencyOrchestrator._is_hospital_suitable(alert, hospital):
                    suitable_hospitals.append(hospital)
            
            return suitable_hospitals
            
        except Exception as e:
            logger.error(f"Hospital discovery failed: {str(e)}")
            return []
    
    @staticmethod
    def _is_hospital_suitable(alert: EmergencyAlert, hospital: Dict) -> bool:
        """
        Check if a hospital is suitable for the specific emergency
        """
        # Basic checks
        if hospital.get('permanently_closed', False):
            return False
        
        if hospital.get('business_status') != 'OPERATIONAL':
            return False
        
        # Emergency type specific checks
        emergency_type = alert.emergency_type
        hospital_types = hospital.get('types', [])
        
        # Map emergency types to required hospital types
        emergency_requirements = {
            'cardiac': ['hospital', 'health', 'doctor'],
            'trauma': ['hospital', 'health', 'emergency_care'],
            'pediatric': ['hospital', 'health', 'doctor'],
            'respiratory': ['hospital', 'health', 'doctor'],
        }
        
        required_types = emergency_requirements.get(emergency_type, ['hospital', 'health'])
        
        # Check if hospital has at least one of the required types
        return any(req_type in hospital_types for req_type in required_types)
    
    @staticmethod
    def _select_best_hospital(alert: EmergencyAlert, hospitals: List[Dict]) -> Optional[Dict]:
        """
        Select the best hospital based on multiple factors
        """
        if not hospitals:
            return None
        
        # Calculate distances and ETAs for all hospitals
        origins = [(float(alert.current_latitude), float(alert.current_longitude))]
        destinations = [(h['latitude'], h['longitude']) for h in hospitals]
        
        distance_matrix = DistanceService.calculate_distance_matrix(origins, destinations)
        
        if not distance_matrix:
            # Fallback: select by proximity using Haversine

            
            for hospital in hospitals:
                distance = calculate_distance_haversine(
                    float(alert.current_latitude),
                    float(alert.current_longitude),
                    hospital['latitude'],
                    hospital['longitude']
                )
                hospital['distance_km'] = distance
            
            hospitals.sort(key=lambda x: x['distance_km'])
            return hospitals[0]
        
        # Find hospital with shortest travel time
        elements = distance_matrix['rows'][0]['elements']
        best_index = None
        best_duration = float('inf')
        
        for i, element in enumerate(elements):
            if element['status'] == 'OK' and element['duration']['value'] < best_duration:
                best_duration = element['duration']['value']
                best_index = i
        
        return hospitals[best_index] if best_index is not None else None
    
    @staticmethod
    def _dispatch_to_hospital(alert: EmergencyAlert, hospital: Dict) -> bool:
        """
        Dispatch the emergency to the selected hospital
        """
        try:
            # Update alert status
            AlertService.update_alert_status(
                alert.alert_id,
                'hospital_selected',
                details={
                    'hospital_name': hospital['name'],
                    'hospital_address': hospital['address'],
                    'hospital_place_id': hospital['place_id'],
                    'coordinates': f"{hospital['latitude']},{hospital['longitude']}"
                }
            )
            
            # TODO: Implement hospital communication
            # This would integrate with the hospital communication service
            
            logger.info(f"Dispatched alert {alert.alert_id} to hospital {hospital['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Hospital dispatch failed: {str(e)}")
            return False