import logging
from rest_framework import generics, status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from emergencies import serializers

from .models import (
    MedicalProfile, MedicalCondition, Allergy, Medication,
    EmergencyContact, InsuranceInformation, SurgicalHistory, MedicalDocument
)
from .serializers import (
    MedicalProfileSerializer, MedicalProfileCreateSerializer, MedicalProfileUpdateSerializer,
    MedicalConditionSerializer, MedicalConditionCreateSerializer,
    AllergySerializer, AllergyCreateSerializer,
    MedicationSerializer, MedicationCreateSerializer,
    EmergencyContactSerializer, EmergencyContactCreateSerializer,
    InsuranceInformationSerializer, InsuranceInformationCreateSerializer,
    SurgicalHistorySerializer, SurgicalHistoryCreateSerializer,
    MedicalDocumentSerializer, EmergencyDataPacketSerializer,
    FHIRDataSerializer, EmergencySummarySerializer
)
from .services import MedicalProfileService, EmergencyDataService

logger = logging.getLogger(__name__)


class MedicalProfileAPIView(APIView):
    """
    Manage user's medical profile
    GET /api/medical/profile/ - Retrieve medical profile
    POST /api/medical/profile/ - Create medical profile
    PUT /api/medical/profile/ - Update medical profile
    DELETE /api/medical/profile/ - Delete medical profile (GDPR compliance)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Retrieve medical profile"""
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = MedicalProfileSerializer(medical_profile)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Medical profile retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve medical profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Create medical profile"""
        serializer = MedicalProfileCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate medical data
            validation_errors = MedicalProfileService.validate_medical_data(serializer.validated_data)
            if validation_errors:
                return Response(
                    {'errors': validation_errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            medical_profile = MedicalProfileService.create_medical_profile(
                request.user, serializer.validated_data
            )
            
            if not medical_profile:
                return Response(
                    {'error': 'Failed to create medical profile'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            response_serializer = MedicalProfileSerializer(medical_profile)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Medical profile creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create medical profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        """Update medical profile"""
        serializer = MedicalProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            success = MedicalProfileService.update_medical_profile(
                request.user, serializer.validated_data
            )
            
            if not success:
                return Response(
                    {'error': 'Failed to update medical profile'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Return updated profile
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            response_serializer = MedicalProfileSerializer(medical_profile)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Medical profile update failed: {str(e)}")
            return Response(
                {'error': 'Failed to update medical profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """Delete medical profile (GDPR compliance)"""
        try:
            success = MedicalProfileService.delete_medical_profile(request.user)
            
            if not success:
                return Response(
                    {'error': 'Failed to delete medical profile'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(
                {'message': 'Medical profile deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            logger.error(f"Medical profile deletion failed: {str(e)}")
            return Response(
                {'error': 'Failed to delete medical profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmergencyDataPacketAPIView(APIView):
    """
    Get emergency data packet for hospital transmission
    GET /api/medical/profile/emergency-data/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            emergency_data = MedicalProfileService.get_emergency_data_packet(request.user)
            
            if not emergency_data:
                return Response(
                    {'error': 'No medical profile found or emergency data unavailable'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
            serializer = EmergencyDataPacketSerializer(emergency_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Emergency data packet retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve emergency data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FHIRDataAPIView(APIView):
    """
    Get FHIR-compliant medical data
    GET /api/medical/profile/fhir-data/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            fhir_data = EmergencyDataService.generate_fhir_compliant_data(request.user)
            
            if not fhir_data:
                return Response(
                    {'error': 'No medical profile found or FHIR data unavailable'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = FHIRDataSerializer(fhir_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"FHIR data generation failed: {str(e)}")
            return Response(
                {'error': 'Failed to generate FHIR data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmergencySummaryAPIView(APIView):
    """
    Get concise emergency summary for first responders
    GET /api/medical/profile/emergency-summary/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            emergency_summary = EmergencyDataService.format_emergency_summary(request.user)
            
            if not emergency_summary:
                return Response(
                    {'error': 'No medical profile found or emergency summary unavailable'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = EmergencySummarySerializer(emergency_summary)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Emergency summary generation failed: {str(e)}")
            return Response(
                {'error': 'Failed to generate emergency summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Medical Conditions Views
class MedicalConditionListCreateAPIView(generics.ListCreateAPIView):
    """
    Manage medical conditions
    GET /api/medical/profile/conditions/ - List all conditions
    POST /api/medical/profile/conditions/ - Create new condition
    """
    serializer_class = MedicalConditionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return MedicalCondition.objects.none()
        return medical_profile.conditions.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MedicalConditionCreateSerializer
        return MedicalConditionSerializer
    
    def perform_create(self, serializer):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            raise serializers.ValidationError({'error': 'Medical profile not found'})
        serializer.save(medical_profile=medical_profile)


class MedicalConditionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage specific medical condition
    GET /api/medical/profile/conditions/{id}/ - Get condition
    PUT /api/medical/profile/conditions/{id}/ - Update condition
    DELETE /api/medical/profile/conditions/{id}/ - Delete condition
    """
    serializer_class = MedicalConditionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return MedicalCondition.objects.none()
        return medical_profile.conditions.all()


# Allergies Views
class AllergyListCreateAPIView(generics.ListCreateAPIView):
    """
    Manage allergies
    GET /api/medical/profile/allergies/ - List all allergies
    POST /api/medical/profile/allergies/ - Create new allergy
    """
    serializer_class = AllergySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return Allergy.objects.none()
        return medical_profile.allergies.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AllergyCreateSerializer
        return AllergySerializer
    
    def perform_create(self, serializer):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            raise serializers.ValidationError({'error': 'Medical profile not found'})
        serializer.save(medical_profile=medical_profile)


class AllergyDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage specific allergy
    GET /api/medical/profile/allergies/{id}/ - Get allergy
    PUT /api/medical/profile/allergies/{id}/ - Update allergy
    DELETE /api/medical/profile/allergies/{id}/ - Delete allergy
    """
    serializer_class = AllergySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return Allergy.objects.none()
        return medical_profile.allergies.all()


# Medications Views
class MedicationListCreateAPIView(generics.ListCreateAPIView):
    """
    Manage medications
    GET /api/medical/profile/medications/ - List all medications
    POST /api/medical/profile/medications/ - Create new medication
    """
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return Medication.objects.none()
        return medical_profile.medications.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MedicationCreateSerializer
        return MedicationSerializer
    
    def perform_create(self, serializer):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            raise serializers.ValidationError({'error': 'Medical profile not found'})
        serializer.save(medical_profile=medical_profile)


class MedicationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage specific medication
    GET /api/medical/profile/medications/{id}/ - Get medication
    PUT /api/medical/profile/medications/{id}/ - Update medication
    DELETE /api/medical/profile/medications/{id}/ - Delete medication
    """
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return Medication.objects.none()
        return medical_profile.medications.all()


# Emergency Contacts Views
class EmergencyContactListCreateAPIView(generics.ListCreateAPIView):
    """
    Manage emergency contacts
    GET /api/medical/profile/contacts/ - List all contacts
    POST /api/medical/profile/contacts/ - Create new contact
    """
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return EmergencyContact.objects.none()
        return medical_profile.emergency_contacts.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EmergencyContactCreateSerializer
        return EmergencyContactSerializer
    
    def perform_create(self, serializer):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            raise serializers.ValidationError({'error': 'Medical profile not found'})
        serializer.save(medical_profile=medical_profile)


class EmergencyContactDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage specific emergency contact
    GET /api/medical/profile/contacts/{id}/ - Get contact
    PUT /api/medical/profile/contacts/{id}/ - Update contact
    DELETE /api/medical/profile/contacts/{id}/ - Delete contact
    """
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return EmergencyContact.objects.none()
        return medical_profile.emergency_contacts.all()


class SetPrimaryContactAPIView(APIView):
    """
    Set an emergency contact as primary
    POST /api/medical/profile/contacts/{id}/primary/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, contact_id):
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            contact = get_object_or_404(EmergencyContact, id=contact_id, medical_profile=medical_profile)
            
            # Remove primary from all contacts
            EmergencyContact.objects.filter(medical_profile=medical_profile, is_primary=True).update(is_primary=False)
            
            # Set new primary
            contact.is_primary = True
            contact.save()
            
            serializer = EmergencyContactSerializer(contact)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to set primary contact: {str(e)}")
            return Response(
                {'error': 'Failed to set primary contact'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Insurance Information Views
class InsuranceListCreateAPIView(generics.ListCreateAPIView):
    """
    Manage insurance information
    GET /api/medical/profile/insurance/ - List all insurance info
    POST /api/medical/profile/insurance/ - Create new insurance info
    """
    serializer_class = InsuranceInformationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return InsuranceInformation.objects.none()
        return medical_profile.insurance_info.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InsuranceInformationCreateSerializer
        return InsuranceInformationSerializer
    
    def perform_create(self, serializer):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            raise serializers.ValidationError({'error': 'Medical profile not found'})
        serializer.save(medical_profile=medical_profile)


class InsuranceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage specific insurance information
    GET /api/medical/profile/insurance/{id}/ - Get insurance info
    PUT /api/medical/profile/insurance/{id}/ - Update insurance info
    DELETE /api/medical/profile/insurance/{id}/ - Delete insurance info
    """
    serializer_class = InsuranceInformationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return InsuranceInformation.objects.none()
        return medical_profile.insurance_info.all()


# Surgical History Views
class SurgicalHistoryListCreateAPIView(generics.ListCreateAPIView):
    """
    Manage surgical history
    GET /api/medical/profile/surgical-history/ - List all surgical history
    POST /api/medical/profile/surgical-history/ - Create new surgical history
    """
    serializer_class = SurgicalHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return SurgicalHistory.objects.none()
        return medical_profile.surgical_history.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SurgicalHistoryCreateSerializer
        return SurgicalHistorySerializer
    
    def perform_create(self, serializer):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            raise serializers.ValidationError({'error': 'Medical profile not found'})
        serializer.save(medical_profile=medical_profile)


class SurgicalHistoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage specific surgical history
    GET /api/medical/profile/surgical-history/{id}/ - Get surgical history
    PUT /api/medical/profile/surgical-history/{id}/ - Update surgical history
    DELETE /api/medical/profile/surgical-history/{id}/ - Delete surgical history
    """
    serializer_class = SurgicalHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        medical_profile = MedicalProfileService.get_medical_profile(self.request.user)
        if not medical_profile:
            return SurgicalHistory.objects.none()
        return medical_profile.surgical_history.all()