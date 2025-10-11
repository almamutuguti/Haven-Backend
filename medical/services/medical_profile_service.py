import logging
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.core.exceptions import ValidationError

from medical.models import (
    MedicalProfile, MedicalCondition, Allergy, Medication,
    EmergencyContact, InsuranceInformation, SurgicalHistory
)

logger = logging.getLogger(__name__)


class MedicalProfileService:
    """
    Service for managing medical profile operations
    """
    
    @staticmethod
    def create_medical_profile(user, profile_data: Dict[str, Any]) -> Optional[MedicalProfile]:
        """
        Create a new medical profile for a user
        """
        try:
            with transaction.atomic():
                # Check if profile already exists
                if hasattr(user, 'medical_profile'):
                    raise ValidationError("Medical profile already exists for this user")
                
                # Extract base profile data
                base_fields = [
                    'blood_type', 'height_cm', 'weight_kg', 'organ_donor',
                    'dnr_order', 'advance_directive', 'primary_care_physician',
                    'physician_phone', 'data_consent_given', 'data_sharing_preferences'
                ]
                
                profile_data_clean = {k: v for k, v in profile_data.items() if k in base_fields}
                
                # Create medical profile
                medical_profile = MedicalProfile.objects.create(
                    user=user,
                    **profile_data_clean
                )
                
                logger.info(f"Medical profile created for user {user.email}")
                return medical_profile
                
        except Exception as e:
            logger.error(f"Failed to create medical profile: {str(e)}")
            return None
    
    @staticmethod
    def get_medical_profile(user) -> Optional[MedicalProfile]:
        """
        Get user's medical profile with all related data
        """
        try:
            return MedicalProfile.objects.select_related('user').prefetch_related(
                'conditions', 'allergies', 'medications', 
                'emergency_contacts', 'insurance_info', 'surgical_history'
            ).get(user=user)
            
        except MedicalProfile.DoesNotExist:
            logger.warning(f"No medical profile found for user {user.email}")
            return None
        except Exception as e:
            logger.error(f"Failed to get medical profile: {str(e)}")
            return None
    
    @staticmethod
    def update_medical_profile(user, update_data: Dict[str, Any]) -> bool:
        """
        Update user's medical profile
        """
        try:
            with transaction.atomic():
                medical_profile = MedicalProfile.objects.get(user=user)
                
                # Update allowed fields
                allowed_fields = [
                    'blood_type', 'height_cm', 'weight_kg', 'organ_donor',
                    'dnr_order', 'advance_directive', 'primary_care_physician',
                    'physician_phone', 'data_sharing_preferences', 'last_medical_review'
                ]
                
                for field, value in update_data.items():
                    if field in allowed_fields and hasattr(medical_profile, field):
                        setattr(medical_profile, field, value)
                
                medical_profile.save()
                logger.info(f"Medical profile updated for user {user.email}")
                return True
                
        except MedicalProfile.DoesNotExist:
            logger.warning(f"No medical profile found for user {user.email}")
            return False
        except Exception as e:
            logger.error(f"Failed to update medical profile: {str(e)}")
            return False
    
    @staticmethod
    def delete_medical_profile(user) -> bool:
        """
        Delete user's medical profile (GDPR compliance)
        """
        try:
            with transaction.atomic():
                medical_profile = MedicalProfile.objects.get(user=user)
                medical_profile.delete()
                
                logger.info(f"Medical profile deleted for user {user.email}")
                return True
                
        except MedicalProfile.DoesNotExist:
            logger.warning(f"No medical profile found for user {user.email}")
            return True  # Consider it successful if it doesn't exist
        except Exception as e:
            logger.error(f"Failed to delete medical profile: {str(e)}")
            return False
    
    @staticmethod
    def add_medical_condition(user, condition_data: Dict[str, Any]) -> Optional[MedicalCondition]:
        """
        Add a medical condition to user's profile
        """
        try:
            with transaction.atomic():
                medical_profile = MedicalProfile.objects.get(user=user)
                
                condition = MedicalCondition.objects.create(
                    medical_profile=medical_profile,
                    **condition_data
                )
                
                logger.info(f"Medical condition added for user {user.email}: {condition.name}")
                return condition
                
        except MedicalProfile.DoesNotExist:
            logger.warning(f"No medical profile found for user {user.email}")
            return None
        except Exception as e:
            logger.error(f"Failed to add medical condition: {str(e)}")
            return None
    
    @staticmethod
    def add_allergy(user, allergy_data: Dict[str, Any]) -> Optional[Allergy]:
        """
        Add an allergy to user's profile
        """
        try:
            with transaction.atomic():
                medical_profile = MedicalProfile.objects.get(user=user)
                
                allergy = Allergy.objects.create(
                    medical_profile=medical_profile,
                    **allergy_data
                )
                
                logger.info(f"Allergy added for user {user.email}: {allergy.allergen}")
                return allergy
                
        except MedicalProfile.DoesNotExist:
            logger.warning(f"No medical profile found for user {user.email}")
            return None
        except Exception as e:
            logger.error(f"Failed to add allergy: {str(e)}")
            return None
    
    @staticmethod
    def add_medication(user, medication_data: Dict[str, Any]) -> Optional[Medication]:
        """
        Add a medication to user's profile
        """
        try:
            with transaction.atomic():
                medical_profile = MedicalProfile.objects.get(user=user)
                
                medication = Medication.objects.create(
                    medical_profile=medical_profile,
                    **medication_data
                )
                
                logger.info(f"Medication added for user {user.email}: {medication.name}")
                return medication
                
        except MedicalProfile.DoesNotExist:
            logger.warning(f"No medical profile found for user {user.email}")
            return None
        except Exception as e:
            logger.error(f"Failed to add medication: {str(e)}")
            return None
    
    @staticmethod
    def add_emergency_contact(user, contact_data: Dict[str, Any]) -> Optional[EmergencyContact]:
        """
        Add an emergency contact to user's profile
        """
        try:
            with transaction.atomic():
                medical_profile = MedicalProfile.objects.get(user=user)
                
                # If setting as primary, remove primary from other contacts
                if contact_data.get('is_primary'):
                    EmergencyContact.objects.filter(
                        medical_profile=medical_profile, 
                        is_primary=True
                    ).update(is_primary=False)
                
                contact = EmergencyContact.objects.create(
                    medical_profile=medical_profile,
                    **contact_data
                )
                
                logger.info(f"Emergency contact added for user {user.email}: {contact.full_name}")
                return contact
                
        except MedicalProfile.DoesNotExist:
            logger.warning(f"No medical profile found for user {user.email}")
            return None
        except Exception as e:
            logger.error(f"Failed to add emergency contact: {str(e)}")
            return None
    
    @staticmethod
    def get_emergency_data_packet(user) -> Optional[Dict[str, Any]]:
        """
        Generate emergency data packet for hospital transmission
        """
        try:
            medical_profile = MedicalProfileService.get_medical_profile(user)
            if not medical_profile:
                return None
            
            # Compile critical emergency information
            emergency_data = {
                'patient_info': {
                    'full_name': user.get_full_name(),
                    'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
                    'blood_type': medical_profile.blood_type,
                    'allergies': [],
                    'current_medications': [],
                    'medical_conditions': [],
                    'emergency_contacts': [],
                },
                'critical_information': {
                    'organ_donor': medical_profile.organ_donor,
                    'dnr_order': medical_profile.dnr_order,
                    'advance_directive': bool(medical_profile.advance_directive),
                }
            }
            
            # Add allergies
            for allergy in medical_profile.allergies.filter(severity__in=['severe', 'life_threatening']):
                emergency_data['patient_info']['allergies'].append({
                    'allergen': allergy.allergen,
                    'reaction': allergy.reaction,
                    'severity': allergy.severity,
                    'treatment': allergy.treatment,
                })
            
            # Add critical medications
            for medication in medical_profile.medications.filter(is_critical=True, status='active'):
                emergency_data['patient_info']['current_medications'].append({
                    'name': medication.name,
                    'dosage': medication.dosage,
                    'frequency': medication.frequency,
                    'purpose': medication.purpose,
                })
            
            # Add critical medical conditions
            for condition in medical_profile.conditions.filter(is_critical=True, status='active'):
                emergency_data['patient_info']['medical_conditions'].append({
                    'name': condition.name,
                    'severity': condition.severity,
                    'description': condition.description,
                })
            
            # Add emergency contacts
            for contact in medical_profile.emergency_contacts.all()[:3]:  # Limit to 3 primary contacts
                emergency_data['patient_info']['emergency_contacts'].append({
                    'name': contact.full_name,
                    'relationship': contact.relationship,
                    'phone': contact.phone_number,
                    'can_make_medical_decisions': contact.can_make_medical_decisions,
                })
            
            return emergency_data
            
        except Exception as e:
            logger.error(f"Failed to generate emergency data packet: {str(e)}")
            return None
    
    @staticmethod
    def validate_medical_data(data: Dict[str, Any]) -> List[str]:
        """
        Validate medical data for correctness and safety
        """
        errors = []
        
        # Blood type validation
        valid_blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'unknown']
        if data.get('blood_type') and data['blood_type'] not in valid_blood_types:
            errors.append(f"Invalid blood type: {data['blood_type']}")
        
        # Height validation (in cm)
        if data.get('height_cm'):
            height = data['height_cm']
            if not (50 <= height <= 250):  # Reasonable human height range
                errors.append(f"Invalid height: {height}cm")
        
        # Weight validation (in kg)
        if data.get('weight_kg'):
            weight = data['weight_kg']
            if not (2 <= weight <= 500):  # Reasonable human weight range
                errors.append(f"Invalid weight: {weight}kg")
        
        return errors