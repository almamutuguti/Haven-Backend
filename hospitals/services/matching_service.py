import logging
from typing import List, Dict, Optional, Tuple
from django.db.models import Q, F, Value, FloatField
from django.db.models.functions import Coalesce

from hospitals.models import Hospital, HospitalSpecialty, HospitalCapacity
from geolocation.services.distance_service import DistanceService
from geolocation.utils import calculate_distance_haversine
from emergencies import models

logger = logging.getLogger(__name__)


class MatchingService:
    """
    Service for matching emergencies with the most suitable hospitals
    """
    
    @staticmethod
    def find_best_hospitals_for_emergency(
        emergency_lat: float,
        emergency_lon: float,
        emergency_type: str,
        required_specialties: List[str] = None,
        max_distance_km: int = 50,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Find the best hospitals for a specific emergency
        """
        try:
            # Step 1: Find nearby hospitals
            nearby_hospitals = MatchingService._get_nearby_hospitals(
                emergency_lat, emergency_lon, max_distance_km
            )
            
            if not nearby_hospitals:
                return []
            
            # Step 2: Score each hospital based on multiple factors
            scored_hospitals = []
            for hospital in nearby_hospitals:
                score = MatchingService._calculate_hospital_score(
                    hospital, emergency_lat, emergency_lon, emergency_type, required_specialties
                )
                
                if score['total_score'] > 0:  # Only include hospitals with positive scores
                    hospital_data = MatchingService._serialize_hospital_for_matching(hospital)
                    hospital_data['matching_score'] = score
                    scored_hospitals.append(hospital_data)
            
            # Step 3: Sort by total score (descending)
            scored_hospitals.sort(key=lambda x: x['matching_score']['total_score'], reverse=True)
            
            return scored_hospitals[:max_results]
            
        except Exception as e:
            logger.error(f"Hospital matching failed: {str(e)}")
            return []
    
    @staticmethod
    def _get_nearby_hospitals(latitude: float, longitude: float, max_distance_km: int) -> List[Hospital]:
        """
        Get hospitals within the maximum distance
        """
        hospitals = Hospital.objects.filter(
            is_operational=True,
            accepts_emergencies=True
        ).select_related(
            'location', 'location__location', 'capacity'
        ).prefetch_related('specialties')
        
        nearby_hospitals = []
        for hospital in hospitals:
            hospital_lat = float(hospital.location.location.latitude)
            hospital_lon = float(hospital.location.location.longitude)
            
            distance = calculate_distance_haversine(
                latitude, longitude, hospital_lat, hospital_lon
            )
            
            if distance <= max_distance_km:
                hospital.distance_km = distance
                nearby_hospitals.append(hospital)
        
        return nearby_hospitals
    
    @staticmethod
    def _calculate_hospital_score(
        hospital: Hospital,
        emergency_lat: float,
        emergency_lon: float,
        emergency_type: str,
        required_specialties: List[str]
    ) -> Dict:
        """
        Calculate matching score for a hospital based on multiple factors
        """
        scores = {
            'distance_score': 0,
            'capacity_score': 0,
            'specialty_score': 0,
            'level_score': 0,
            'rating_score': 0,
            'total_score': 0
        }
        
        # 1. Distance Score (40% weight)
        distance_score = MatchingService._calculate_distance_score(hospital.distance_km)
        scores['distance_score'] = distance_score
        
        # 2. Capacity Score (25% weight)
        capacity_score = MatchingService._calculate_capacity_score(hospital)
        scores['capacity_score'] = capacity_score
        
        # 3. Specialty Score (20% weight)
        specialty_score = MatchingService._calculate_specialty_score(hospital, emergency_type, required_specialties)
        scores['specialty_score'] = specialty_score
        
        # 4. Level Score (10% weight)
        level_score = MatchingService._calculate_level_score(hospital)
        scores['level_score'] = level_score
        
        # 5. Rating Score (5% weight)
        rating_score = MatchingService._calculate_rating_score(hospital)
        scores['rating_score'] = rating_score
        
        # Calculate weighted total score
        total_score = (
            distance_score * 0.40 +
            capacity_score * 0.25 +
            specialty_score * 0.20 +
            level_score * 0.10 +
            rating_score * 0.05
        )
        
        scores['total_score'] = round(total_score, 2)
        
        return scores
    
    @staticmethod
    def _calculate_distance_score(distance_km: float) -> float:
        """
        Calculate score based on distance (closer = higher score)
        """
        if distance_km <= 5:
            return 100
        elif distance_km <= 10:
            return 80
        elif distance_km <= 20:
            return 60
        elif distance_km <= 30:
            return 40
        elif distance_km <= 50:
            return 20
        else:
            return 0
    
    @staticmethod
    def _calculate_capacity_score(hospital: Hospital) -> float:
        """
        Calculate score based on hospital capacity
        """
        capacity = getattr(hospital, 'capacity', None)
        if not capacity or not capacity.is_accepting_patients:
            return 0
        
        # Base score on capacity status
        capacity_scores = {
            'low': 100,      # Lots of capacity
            'moderate': 75,  # Moderate capacity
            'high': 50,      # Limited capacity
            'full': 10,      # Very limited capacity
            'overflow': 0,   # No capacity
        }
        
        base_score = capacity_scores.get(capacity.capacity_status, 50)
        
        # Adjust based on emergency bed availability
        if capacity.emergency_beds_available > 0:
            emergency_bed_ratio = capacity.emergency_beds_available / max(capacity.emergency_beds_total, 1)
            adjustment = emergency_bed_ratio * 30  # Up to 30 points adjustment
            return min(base_score + adjustment, 100)
        
        return base_score
    
    @staticmethod
    def _calculate_specialty_score(
        hospital: Hospital,
        emergency_type: str,
        required_specialties: List[str]
    ) -> float:
        """
        Calculate score based on hospital specialties and emergency type
        """
        specialties = hospital.specialties.filter(is_available=True)
        
        if not specialties.exists():
            return 0
        
        # Map emergency types to required specialties
        emergency_specialty_map = {
            'trauma': ['trauma', 'surgical', 'emergency', 'orthopedic'],
            'cardiac': ['cardiac', 'icu', 'emergency'],
            'pediatric': ['pediatric', 'emergency'],
            'respiratory': ['emergency', 'icu'],
            'medical': ['emergency'],
            'accident': ['trauma', 'emergency', 'surgical'],
        }
        
        required_specialties = required_specialties or emergency_specialty_map.get(emergency_type, ['emergency'])
        
        # Calculate specialty match score
        available_specialties = [spec.specialty for spec in specialties]
        matched_specialties = set(available_specialties) & set(required_specialties)
        
        if not matched_specialties:
            return 0
        
        # Score based on number of matched specialties and their capability levels
        specialty_score = 0
        for spec in specialties:
            if spec.specialty in matched_specialties:
                capability_scores = {
                    'basic': 20,
                    'intermediate': 40,
                    'advanced': 70,
                    'specialized': 100
                }
                specialty_score += capability_scores.get(spec.capability_level, 20)
        
        # Normalize score
        max_possible_score = len(required_specialties) * 100
        return min((specialty_score / max_possible_score) * 100, 100)
    
    @staticmethod
    def _calculate_level_score(hospital: Hospital) -> float:
        """
        Calculate score based on hospital level
        """
        level_scores = {
            'level_1': 30,
            'level_2': 50,
            'level_3': 70,
            'level_4': 85,
            'level_5': 95,
            'level_6': 100,
        }
        
        return level_scores.get(hospital.level, 50)
    
    @staticmethod
    def _calculate_rating_score(hospital: Hospital) -> float:
        """
        Calculate score based on hospital ratings
        """
        ratings = hospital.ratings.filter(is_approved=True, was_emergency=True)
        
        if not ratings.exists():
            return 50  # Default score if no ratings
        
        avg_rating = ratings.aggregate(models.Avg('emergency_care_rating'))['emergency_care_rating__avg']
        
        if avg_rating is None:
            return 50
        
        # Convert 1-5 rating to 0-100 scale
        return (avg_rating / 5) * 100
    
    @staticmethod
    def _serialize_hospital_for_matching(hospital: Hospital) -> Dict:
        """
        Serialize hospital data for matching results
        """
        capacity = getattr(hospital, 'capacity', None)
        
        return {
            'id': hospital.id,
            'name': hospital.name,
            'hospital_type': hospital.hospital_type,
            'level': hospital.level,
            'distance_km': round(hospital.distance_km, 2),
            'address': hospital.location.location.formatted_address,
            'latitude': float(hospital.location.location.latitude),
            'longitude': float(hospital.location.location.longitude),
            'phone_number': hospital.phone_number,
            'emergency_phone': hospital.emergency_phone,
            'specialties': [
                {
                    'specialty': spec.specialty,
                    'capability_level': spec.capability_level
                }
                for spec in hospital.specialties.filter(is_available=True)
            ],
            'capacity': {
                'status': capacity.capacity_status if capacity else 'unknown',
                'emergency_beds_available': capacity.emergency_beds_available if capacity else 0,
                'icu_beds_available': capacity.icu_beds_available if capacity else 0,
                'wait_time': capacity.emergency_wait_time if capacity else 0,
            } if capacity else None,
            'eta_minutes': MatchingService._estimate_eta(hospital.distance_km),
        }
    
    @staticmethod
    def _estimate_eta(distance_km: float) -> int:
        """
        Estimate ETA in minutes based on distance
        """
        # Assume average speed of 40 km/h in urban areas
        average_speed_kmh = 40
        time_hours = distance_km / average_speed_kmh
        return max(5, int(time_hours * 60))  # Minimum 5 minutes
    
    @staticmethod
    def get_fallback_hospitals(
        primary_hospital_id: int,
        emergency_lat: float,
        emergency_lon: float,
        max_results: int = 3
    ) -> List[Dict]:
        """
        Get fallback hospitals in case primary hospital cannot accept patient
        """
        try:
            # Get primary hospital to exclude it
            primary_hospital = Hospital.objects.get(id=primary_hospital_id)
            
            # Find alternative hospitals
            alternatives = MatchingService.find_best_hospitals_for_emergency(
                emergency_lat,
                emergency_lon,
                emergency_type='medical',  # Generic type for fallback
                max_distance_km=100,  # Wider search radius for fallbacks
                max_results=max_results + 1  # Get extra to exclude primary
            )
            
            # Filter out primary hospital
            fallbacks = [h for h in alternatives if h['id'] != primary_hospital_id]
            
            return fallbacks[:max_results]
            
        except Exception as e:
            logger.error(f"Fallback hospital search failed: {str(e)}")
            return []