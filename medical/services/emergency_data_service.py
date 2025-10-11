import logging
import json
from typing import Dict, Optional, Any
from django.utils import timezone

from medical.models import MedicalProfile
from medical.services.medical_profile_service import MedicalProfileService

logger = logging.getLogger(__name__)


class EmergencyDataService:
    """
    Service for handling emergency medical data formatting and transmission
    """
    
    @staticmethod
    def generate_fhir_compliant_data(user) -> Optional[Dict[str, Any]]:
        """
        Generate FHIR-compliant medical data for hospital systems
        """
        try:
            medical_profile = MedicalProfileService.get_medical_profile(user)
            if not medical_profile:
                return None
            
            # Basic FHIR Patient resource structure
            fhir_data = {
                "resourceType": "Bundle",
                "type": "document",
                "timestamp": timezone.now().isoformat(),
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": f"patient-{user.id}",
                            "identifier": [
                                {
                                    "system": "https://haven.ke/patient",
                                    "value": str(user.id)
                                }
                            ],
                            "name": [
                                {
                                    "use": "official",
                                    "family": user.last_name,
                                    "given": [user.first_name]
                                }
                            ],
                            "telecom": [
                                {
                                    "system": "email",
                                    "value": user.email,
                                    "use": "home"
                                }
                            ],
                            "gender": user.gender if hasattr(user, 'gender') else "unknown",
                            "birthDate": user.date_of_birth.isoformat() if user.date_of_birth else None,
                            "extension": [
                                {
                                    "url": "https://haven.ke/extension/blood-type",
                                    "valueCode": medical_profile.blood_type
                                }
                            ]
                        }
                    }
                ]
            }
            
            # Add conditions as FHIR Conditions
            for condition in medical_profile.conditions.filter(status='active'):
                condition_entry = {
                    "resource": {
                        "resourceType": "Condition",
                        "id": f"condition-{condition.id}",
                        "clinicalStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                    "code": "active",
                                    "display": "Active"
                                }
                            ]
                        },
                        "code": {
                            "coding": [
                                {
                                    "system": "http://hl7.org/fhir/sid/icd-10",
                                    "code": condition.icd_code if condition.icd_code else "UNKNOWN",
                                    "display": condition.name
                                }
                            ],
                            "text": condition.name
                        },
                        "subject": {
                            "reference": f"Patient/patient-{user.id}"
                        },
                        "onsetDateTime": condition.diagnosis_date.isoformat() if condition.diagnosis_date else None,
                        "severity": {
                            "coding": [
                                {
                                    "system": "https://haven.ke/severity",
                                    "code": condition.severity,
                                    "display": condition.get_severity_display()
                                }
                            ]
                        }
                    }
                }
                fhir_data["entry"].append(condition_entry)
            
            # Add allergies as FHIR Allergies
            for allergy in medical_profile.allergies.all():
                allergy_entry = {
                    "resource": {
                        "resourceType": "AllergyIntolerance",
                        "id": f"allergy-{allergy.id}",
                        "clinicalStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                    "code": "active",
                                    "display": "Active"
                                }
                            ]
                        },
                        "verificationStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                                    "code": "confirmed",
                                    "display": "Confirmed"
                                }
                            ]
                        },
                        "type": "allergy",
                        "category": [allergy.allergy_type],
                        "criticality": allergy.severity.upper() if allergy.severity in ['severe', 'life_threatening'] else "LOW",
                        "code": {
                            "text": allergy.allergen
                        },
                        "reaction": [
                            {
                                "manifestation": [
                                    {
                                        "text": allergy.reaction
                                    }
                                ],
                                "severity": allergy.severity
                            }
                        ],
                        "patient": {
                            "reference": f"Patient/patient-{user.id}"
                        }
                    }
                }
                fhir_data["entry"].append(allergy_entry)
            
            # Add medications as FHIR Medications
            for medication in medical_profile.medications.filter(status='active'):
                medication_entry = {
                    "resource": {
                        "resourceType": "MedicationStatement",
                        "id": f"medication-{medication.id}",
                        "status": "active",
                        "medicationCodeableConcept": {
                            "text": medication.name
                        },
                        "subject": {
                            "reference": f"Patient/patient-{user.id}"
                        },
                        "effectivePeriod": {
                            "start": medication.start_date.isoformat() if medication.start_date else None
                        },
                        "dosage": [
                            {
                                "text": f"{medication.dosage} {medication.frequency}"
                            }
                        ],
                        "reasonCode": [
                            {
                                "text": medication.purpose
                            }
                        ] if medication.purpose else []
                    }
                }
                fhir_data["entry"].append(medication_entry)
            
            logger.info(f"FHIR data generated for user {user.email}")
            return fhir_data
            
        except Exception as e:
            logger.error(f"Failed to generate FHIR data: {str(e)}")
            return None
    
    @staticmethod
    def format_emergency_summary(user) -> Optional[Dict[str, Any]]:
        """
        Format a concise emergency summary for first responders
        """
        try:
            medical_profile = MedicalProfileService.get_medical_profile(user)
            if not medical_profile:
                return None
            
            emergency_data = MedicalProfileService.get_emergency_data_packet(user)
            if not emergency_data:
                return None
            
            # Create concise summary
            summary = {
                "patient_summary": {
                    "name": user.get_full_name(),
                    "age": medical_profile.age,
                    "blood_type": medical_profile.blood_type,
                    "organ_donor": medical_profile.organ_donor,
                    "dnr": medical_profile.dnr_order,
                },
                "critical_alerts": {
                    "severe_allergies": [
                        allergy for allergy in emergency_data['patient_info']['allergies']
                        if allergy['severity'] in ['severe', 'life_threatening']
                    ],
                    "critical_medications": emergency_data['patient_info']['current_medications'],
                    "critical_conditions": emergency_data['patient_info']['medical_conditions'],
                },
                "emergency_contacts": emergency_data['patient_info']['emergency_contacts'][:2],  # Top 2 contacts
                "last_updated": medical_profile.updated_at.isoformat(),
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to format emergency summary: {str(e)}")
            return None
    
    @staticmethod
    def encrypt_medical_data(data: Dict[str, Any], encryption_key: str = None) -> Optional[str]:
        """
        Encrypt sensitive medical data (placeholder for actual encryption)
        """
        try:
            # TODO: Implement proper encryption
            # For now, return JSON string
            # In production, use proper encryption like AES
            return json.dumps(data)
            
        except Exception as e:
            logger.error(f"Failed to encrypt medical data: {str(e)}")
            return None
    
    @staticmethod
    def decrypt_medical_data(encrypted_data: str, decryption_key: str = None) -> Optional[Dict[str, Any]]:
        """
        Decrypt medical data (placeholder for actual decryption)
        """
        try:
            # TODO: Implement proper decryption
            # For now, parse JSON string
            # In production, use proper decryption
            return json.loads(encrypted_data)
            
        except Exception as e:
            logger.error(f"Failed to decrypt medical data: {str(e)}")
            return None