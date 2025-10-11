import logging
from typing import List, Dict, Optional, Tuple
from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.db.models.functions import ACos, Cos, Radians, Sin
from django.core.cache import cache
from emergencies import models # confirm no circular import
from hospitals.models import Hospital, HospitalSpecialty, HospitalCapacity
from geolocation.services.places_service import PlacesService
from geolocation.services.distance_service import DistanceService
from geolocation.utils import calculate_distance_haversine

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Service for discovering and finding hospitals based on various criteria
    """
    
    @staticmethod
    def find_nearby_hospitals(
        latitude: float,
        longitude: float,
        radius_km: int = 50,
        emergency_type: str = None,
        specialties: List[str] = None,
        hospital_level: str = None,
        max_results: int = 20
    ) -> List[Dict]:
        """
        Find hospitals near a location with optional filtering
        """
        try:
            # Create cache key based on parameters
            cache_key = f"nearby_hospitals_{latitude}_{longitude}_{radius_km}_{emergency_type}_{hospital_level}_{max_results}"
            if specialties:
                cache_key += f"_{'_'.join(sorted(specialties))}"
            
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Base query for operational hospitals that accept emergencies
            hospitals = Hospital.objects.filter(
                is_operational=True,
                accepts_emergencies=True
            ).select_related(
                'location', 'location__location', 'capacity'
            ).prefetch_related('specialties')
            
            # Filter by hospital level if specified
            if hospital_level:
                hospitals = hospitals.filter(level=hospital_level)
            
            # Filter by specialties if specified
            if specialties:
                hospitals = hospitals.filter(
                    specialties__specialty__in=specialties,
                    specialties__is_available=True
                ).distinct()
            
            # Calculate distance for each hospital and filter by radius
            nearby_hospitals = []
            for hospital in hospitals:
                hospital_lat = float(hospital.location.location.latitude)
                hospital_lon = float(hospital.location.location.longitude)
                
                distance = calculate_distance_haversine(
                    latitude, longitude, hospital_lat, hospital_lon
                )
                
                if distance <= radius_km:
                    hospital_data = DiscoveryService._serialize_hospital_for_discovery(
                        hospital, distance
                    )
                    nearby_hospitals.append(hospital_data)
            
            # Sort by distance
            nearby_hospitals.sort(key=lambda x: x['distance_km'])
            
            # Limit results
            result = nearby_hospitals[:max_results]
            
            # Cache for 5 minutes
            cache.set(cache_key, result, 300)
            return result
            
        except Exception as e:
            logger.error(f"Hospital discovery failed: {str(e)}")
            return []
    
    @staticmethod
    def _serialize_hospital_for_discovery(hospital: Hospital, distance_km: float) -> Dict:
        """
        Serialize hospital data for discovery results
        """
        capacity = getattr(hospital, 'capacity', None)
        
        return {
            'id': hospital.id,
            'name': hospital.name,
            'hospital_type': hospital.hospital_type,
            'level': hospital.level,
            'distance_km': round(distance_km, 2),
            'address': hospital.location.location.formatted_address,
            'latitude': float(hospital.location.location.latitude),
            'longitude': float(hospital.location.location.longitude),
            'phone_number': hospital.phone_number,
            'emergency_phone': hospital.emergency_phone,
            'is_verified': hospital.is_verified,
            'specialties': [
                {
                    'specialty': spec.specialty,
                    'capability_level': spec.capability_level,
                    'is_available': spec.is_available
                }
                for spec in hospital.specialties.all()
            ],
            'capacity': {
                'total_beds': capacity.total_beds if capacity else 0,
                'available_beds': capacity.available_beds if capacity else 0,
                'emergency_beds_available': capacity.emergency_beds_available if capacity else 0,
                'icu_beds_available': capacity.icu_beds_available if capacity else 0,
                'capacity_status': capacity.capacity_status if capacity else 'moderate',
                'is_accepting_patients': capacity.is_accepting_patients if capacity else True,
            } if capacity else None,
            'rating': DiscoveryService._calculate_hospital_rating(hospital),
        }
    
    @staticmethod
    def _calculate_hospital_rating(hospital: Hospital) -> Dict:
        """
        Calculate hospital rating from reviews
        """
        ratings = hospital.ratings.filter(is_approved=True)
        
        if not ratings.exists():
            return {
                'overall': 0,
                'count': 0,
                'emergency_care': 0
            }
        
        overall_avg = ratings.aggregate(models.Avg('overall_rating'))['overall_rating__avg']
        emergency_avg = ratings.filter(was_emergency=True).aggregate(
            models.Avg('emergency_care_rating')
        )['emergency_care_rating__avg']
        
        return {
            'overall': round(overall_avg, 1) if overall_avg else 0,
            'count': ratings.count(),
            'emergency_care': round(emergency_avg, 1) if emergency_avg else 0
        }
    
    @staticmethod
    def search_hospitals(
        query: str,
        latitude: float = None,
        longitude: float = None,
        max_results: int = 20
    ) -> List[Dict]:
        """
        Search hospitals by name, specialty, or location
        """
        try:
            hospitals = Hospital.objects.filter(
                Q(name__icontains=query) |
                Q(specialties__specialty__icontains=query) |
                Q(location__location__city__icontains=query) |
                Q(location__location__county__icontains=query),
                is_operational=True
            ).select_related(
                'location', 'location__location', 'capacity'
            ).prefetch_related('specialties').distinct()[:max_results]
            
            results = []
            for hospital in hospitals:
                distance_km = None
                if latitude and longitude:
                    hospital_lat = float(hospital.location.location.latitude)
                    hospital_lon = float(hospital.location.location.longitude)
                    distance_km = calculate_distance_haversine(
                        latitude, longitude, hospital_lat, hospital_lon
                    )
                
                hospital_data = DiscoveryService._serialize_hospital_for_discovery(
                    hospital, distance_km or 0
                )
                results.append(hospital_data)
            
            # Sort by distance if coordinates provided
            if latitude and longitude:
                results.sort(key=lambda x: x['distance_km'])
            
            return results
            
        except Exception as e:
            logger.error(f"Hospital search failed: {str(e)}")
            return []
    
    @staticmethod
    def get_hospital_details(hospital_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific hospital
        """
        try:
            hospital = Hospital.objects.select_related(
                'location', 'location__location', 'capacity'
            ).prefetch_related(
                'specialties', 'working_hours', 'ratings'
            ).get(id=hospital_id)
            
            return DiscoveryService._serialize_hospital_details(hospital)
            
        except Hospital.DoesNotExist:
            logger.warning(f"Hospital not found: {hospital_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get hospital details: {str(e)}")
            return None
    
    @staticmethod
    def _serialize_hospital_details(hospital: Hospital) -> Dict:
        """
        Serialize detailed hospital information
        """
        base_data = DiscoveryService._serialize_hospital_for_discovery(hospital, 0)
        
        # Add detailed information
        base_data.update({
            'email': hospital.email,
            'website': hospital.website,
            'mfl_code': hospital.mfl_code,
            'working_hours': [
                {
                    'day': wh.day,
                    'opens_at': wh.opens_at.isoformat() if wh.opens_at else None,
                    'closes_at': wh.closes_at.isoformat() if wh.closes_at else None,
                    'emergency_opens_at': wh.emergency_opens_at.isoformat() if wh.emergency_opens_at else None,
                    'emergency_closes_at': wh.emergency_closes_at.isoformat() if wh.emergency_closes_at else None,
                    'is_24_hours': wh.is_24_hours,
                    'is_emergency_24_hours': wh.is_emergency_24_hours,
                    'is_closed': wh.is_closed,
                }
                for wh in hospital.working_hours.all()
            ],
            'accessibility_notes': hospital.location.accessibility_notes,
            'entrance_instructions': hospital.location.entrance_instructions,
            'has_ambulance_bay': hospital.location.has_ambulance_bay,
            'emergency_entrance_coordinates': hospital.location.emergency_entrance_coordinates,
        })
        
        return base_data
    
    @staticmethod
    def check_hospital_availability(hospital_id: int) -> Optional[Dict]:
        """
        Check real-time hospital availability and capacity
        """
        try:
            hospital = Hospital.objects.select_related('capacity').get(id=hospital_id)
            capacity = hospital.capacity
            
            if not capacity:
                return {
                    'is_available': False,
                    'reason': 'Capacity information not available',
                    'capacity_status': 'unknown'
                }
            
            return {
                'is_available': capacity.is_accepting_patients,
                'capacity_status': capacity.capacity_status,
                'available_beds': capacity.available_beds,
                'emergency_beds_available': capacity.emergency_beds_available,
                'icu_beds_available': capacity.icu_beds_available,
                'average_wait_time': capacity.average_wait_time,
                'emergency_wait_time': capacity.emergency_wait_time,
                'doctors_available': capacity.doctors_available,
                'nurses_available': capacity.nurses_available,
                'last_updated': capacity.last_updated.isoformat(),
            }
            
        except Hospital.DoesNotExist:
            logger.warning(f"Hospital not found: {hospital_id}")
            return None
        except Exception as e:
            logger.error(f"Availability check failed: {str(e)}")
            return None