import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

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


@api_view(['POST', 'GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def medical_profile_management(request):
    """
    Manage user's medical profile
    POST /api/v1/medical-profile - Create medical profile
    GET /api/v1/medical-profile - Retrieve medical profile
    PUT /api/v1/medical-profile - Update medical profile
    DELETE /api/v1/medical-profile - Delete medical profile (GDPR compliance)
    """
    if request.method == 'POST':
        # Create medical profile
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
    
    elif request.method == 'GET':
        # Retrieve medical profile
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
    
    elif request.method == 'PUT':
        # Update medical profile
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
    
    elif request.method == 'DELETE':
        # Delete medical profile (GDPR compliance)
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emergency_data_packet(request):
    """
    Get emergency data packet for hospital transmission
    GET /api/v1/medical-profile/emergency-data
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fhir_data(request):
    """
    Get FHIR-compliant medical data
    GET /api/v1/medical-profile/fhir-data
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emergency_summary(request):
    """
    Get concise emergency summary for first responders
    GET /api/v1/medical-profile/emergency-summary
    """
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
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def medical_conditions_management(request, condition_id=None):
    """
    Manage medical conditions
    GET /api/v1/medical-profile/conditions - List all conditions
    POST /api/v1/medical-profile/conditions - Create new condition
    """
    if request.method == 'GET':
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            conditions = medical_profile.conditions.all()
            serializer = MedicalConditionSerializer(conditions, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Medical conditions retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve medical conditions'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        serializer = MedicalConditionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            condition = MedicalProfileService.add_medical_condition(
                request.user, serializer.validated_data
            )
            
            if not condition:
                return Response(
                    {'error': 'Failed to add medical condition'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            response_serializer = MedicalConditionSerializer(condition)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Medical condition creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create medical condition'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def medical_condition_detail(request, condition_id):
    """
    Manage specific medical condition
    GET /api/v1/medical-profile/conditions/{id} - Get condition
    PUT /api/v1/medical-profile/conditions/{id} - Update condition
    DELETE /api/v1/medical-profile/conditions/{id} - Delete condition
    """
    try:
        medical_profile = MedicalProfileService.get_medical_profile(request.user)
        if not medical_profile:
            return Response(
                {'error': 'Medical profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        condition = get_object_or_404(MedicalCondition, id=condition_id, medical_profile=medical_profile)
        
        if request.method == 'GET':
            serializer = MedicalConditionSerializer(condition)
            return Response(serializer.data)
        
        elif request.method == 'PUT':
            serializer = MedicalConditionCreateSerializer(condition, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response(serializer.data)
        
        elif request.method == 'DELETE':
            condition.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        logger.error(f"Medical condition operation failed: {str(e)}")
        return Response(
            {'error': 'Operation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Allergies Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def allergies_management(request, allergy_id=None):
    """
    Manage allergies
    """
    if request.method == 'GET':
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            allergies = medical_profile.allergies.all()
            serializer = AllergySerializer(allergies, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Allergies retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve allergies'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        serializer = AllergyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            allergy = MedicalProfileService.add_allergy(
                request.user, serializer.validated_data
            )
            
            if not allergy:
                return Response(
                    {'error': 'Failed to add allergy'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            response_serializer = AllergySerializer(allergy)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Allergy creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create allergy'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Medications Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def medications_management(request, medication_id=None):
    """
    Manage medications
    """
    if request.method == 'GET':
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            medications = medical_profile.medications.all()
            serializer = MedicationSerializer(medications, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Medications retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve medications'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        serializer = MedicationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            medication = MedicalProfileService.add_medication(
                request.user, serializer.validated_data
            )
            
            if not medication:
                return Response(
                    {'error': 'Failed to add medication'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            response_serializer = MedicationSerializer(medication)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Medication creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create medication'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Emergency Contacts Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def emergency_contacts_management(request, contact_id=None):
    """
    Manage emergency contacts
    """
    if request.method == 'GET':
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            contacts = medical_profile.emergency_contacts.all()
            serializer = EmergencyContactSerializer(contacts, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Emergency contacts retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve emergency contacts'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        serializer = EmergencyContactCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            contact = MedicalProfileService.add_emergency_contact(
                request.user, serializer.validated_data
            )
            
            if not contact:
                return Response(
                    {'error': 'Failed to add emergency contact'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            response_serializer = EmergencyContactSerializer(contact)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Emergency contact creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create emergency contact'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_primary_contact(request, contact_id):
    """
    Set an emergency contact as primary
    POST /api/v1/medical-profile/contacts/{id}/primary
    """
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
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def insurance_management(request, insurance_id=None):
    """
    Manage insurance information
    """
    if request.method == 'GET':
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            insurance_info = medical_profile.insurance_info.all()
            serializer = InsuranceInformationSerializer(insurance_info, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Insurance information retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve insurance information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        serializer = InsuranceInformationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            insurance = InsuranceInformation.objects.create(
                medical_profile=medical_profile,
                **serializer.validated_data
            )
            
            response_serializer = InsuranceInformationSerializer(insurance)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Insurance information creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create insurance information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Surgical History Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def surgical_history_management(request, surgery_id=None):
    """
    Manage surgical history
    """
    if request.method == 'GET':
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            surgical_history = medical_profile.surgical_history.all()
            serializer = SurgicalHistorySerializer(surgical_history, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Surgical history retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve surgical history'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        serializer = SurgicalHistoryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            medical_profile = MedicalProfileService.get_medical_profile(request.user)
            if not medical_profile:
                return Response(
                    {'error': 'Medical profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            surgery = SurgicalHistory.objects.create(
                medical_profile=medical_profile,
                **serializer.validated_data
            )
            
            response_serializer = SurgicalHistorySerializer(surgery)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Surgical history creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create surgical history'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )