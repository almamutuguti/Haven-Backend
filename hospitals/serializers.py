from rest_framework import serializers

from geolocation.models import HospitalLocation, Location
from .models import (
    Hospital, HospitalSpecialty, HospitalCapacity, 
    HospitalRating, EmergencyResponse, HospitalWorkingHours
)


class HospitalSpecialtySerializer(serializers.ModelSerializer):
    """Serializer for Hospital Specialty model"""
    
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    capability_display = serializers.CharField(source='get_capability_level_display', read_only=True)
    
    class Meta:
        model = HospitalSpecialty
        fields = [
            'id', 'specialty', 'specialty_display', 'capability_level', 
            'capability_display', 'is_available', 'notes'
        ]
        read_only_fields = ['id']


class HospitalCapacitySerializer(serializers.ModelSerializer):
    """Serializer for Hospital Capacity model"""
    
    bed_occupancy_rate = serializers.FloatField(read_only=True)
    emergency_occupancy_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = HospitalCapacity
        fields = [
            'id', 'total_beds', 'available_beds', 'emergency_beds_total',
            'emergency_beds_available', 'icu_beds_total', 'icu_beds_available',
            'average_wait_time', 'emergency_wait_time', 'doctors_available',
            'nurses_available', 'is_accepting_patients', 'capacity_status',
            'bed_occupancy_rate', 'emergency_occupancy_rate', 'last_updated',
            'next_update_expected'
        ]
        read_only_fields = ['id', 'last_updated']


class HospitalWorkingHoursSerializer(serializers.ModelSerializer):
    """Serializer for Hospital Working Hours"""
    
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    has_emergency_services = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = HospitalWorkingHours
        fields = [
            'id', 'day', 'day_display', 'opens_at', 'closes_at',
            'emergency_opens_at', 'emergency_closes_at', 'is_24_hours',
            'is_emergency_24_hours', 'is_closed', 'has_emergency_services'
        ]
        read_only_fields = ['id']


class HospitalRatingSerializer(serializers.ModelSerializer):
    """Serializer for Hospital Rating model"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = HospitalRating
        fields = [
            'id', 'user', 'user_name', 'user_email', 'overall_rating',
            'staff_rating', 'facilities_rating', 'emergency_care_rating',
            'review_title', 'review_text', 'was_emergency', 'emergency_type',
            'is_verified', 'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_overall_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class HospitalSerializer(serializers.ModelSerializer):
    """Serializer for Hospital model"""
    
    hospital_type_display = serializers.CharField(source='get_hospital_type_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    # Add location data if needed (for display)
    location_data = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'hospital_type', 'hospital_type_display', 'level', 'level_display',
            'phone', 'emergency_phone', 'email', 'website',
            'latitude', 'longitude', 'address',  # Use these directly instead of location
            'place_id', 'mfl_code', 'is_operational', 'is_verified', 'accepts_emergencies',
            'created_at', 'updated_at', 'verified_at', 'is_active', 'location_data'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'verified_at', 'location_data']
    
    def get_location_data(self, obj):
        """Get location data if exists"""
        if obj.location:
            return {
                'id': obj.location.id,
                'place_id': obj.location.place_id,
                'accessibility_notes': obj.location.accessibility_notes,
                'has_ambulance_bay': obj.location.has_ambulance_bay,
            }
        return None
    
    def validate(self, data):
        """Custom validation for hospital creation"""
        # Ensure latitude and longitude are valid if provided
        if data.get('latitude') and not (-90 <= float(data['latitude']) <= 90):
            raise serializers.ValidationError({
                'latitude': 'Latitude must be between -90 and 90 degrees'
            })
        
        if data.get('longitude') and not (-180 <= float(data['longitude']) <= 180):
            raise serializers.ValidationError({
                'longitude': 'Longitude must be between -180 and 180 degrees'
            })
        
        # Check if phone already exists (if provided)
        phone = data.get('phone')
        if phone:
            existing = Hospital.objects.filter(phone=phone)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError({
                    'phone': 'A hospital with this phone number already exists'
                })
        
        # Check if email already exists (if provided)
        email = data.get('email')
        if email:
            existing = Hospital.objects.filter(email=email)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError({
                    'email': 'A hospital with this email already exists'
                })
        
        return data

# Also update the HospitalCreateSerializer for better error handling
class HospitalCreateSerializer(HospitalSerializer):
    """Serializer specifically for creating hospitals with better validation"""
    
    class Meta(HospitalSerializer.Meta):
        fields = HospitalSerializer.Meta.fields
    
    def create(self, validated_data):
        """Create hospital with location if coordinates provided"""
        try:
            # Extract location data if provided
            latitude = validated_data.get('latitude')
            longitude = validated_data.get('longitude')
            address = validated_data.get('address')
            
            # Create the hospital
            hospital = Hospital.objects.create(**validated_data)
            
            # Create location if coordinates and address are provided
            if latitude and longitude and address:
                try:
                    # Create Location first
                    location = Location.objects.create(
                        latitude=latitude,
                        longitude=longitude,
                        formatted_address=address,
                        location_type='emergency'
                    )
                    
                    # Create HospitalLocation
                    hospital_location = HospitalLocation.objects.create(
                        location=location,
                        place_id=validated_data.get('place_id', ''),
                        has_ambulance_bay=True  # Default for hospitals
                    )
                    
                    # Link to hospital
                    hospital.location = hospital_location
                    hospital.save()
                    
                except Exception as e:
                    # If location creation fails, still keep the hospital
                    print(f"Warning: Failed to create location for hospital: {str(e)}")
                    # Hospital is already created, so continue
            
            return hospital
            
        except Exception as e:
            # Wrap any database errors in validation error for frontend
            raise serializers.ValidationError({
                'non_field_errors': [f'Failed to create hospital: {str(e)}']
            })

class HospitalDetailSerializer(HospitalSerializer):
    """Detailed serializer for Hospital with related data"""
    
    specialties = HospitalSpecialtySerializer(many=True, read_only=True)
    capacity = HospitalCapacitySerializer(read_only=True)
    working_hours = HospitalWorkingHoursSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)
    
    class Meta(HospitalSerializer.Meta):
        fields = HospitalSerializer.Meta.fields + [
            'specialties', 'capacity', 'working_hours', 'average_rating', 'rating_count'
        ]


class NearbyHospitalsRequestSerializer(serializers.Serializer):
    """Serializer for nearby hospitals request"""
    
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    radius_km = serializers.IntegerField(default=50, min_value=1, max_value=200)
    emergency_type = serializers.CharField(required=False, allow_null=True)
    specialties = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    hospital_level = serializers.CharField(required=False, allow_null=True)
    max_results = serializers.IntegerField(default=20, min_value=1, max_value=50)
    
    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class HospitalSearchRequestSerializer(serializers.Serializer):
    """Serializer for hospital search request"""
    
    query = serializers.CharField(required=True, max_length=100)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    max_results = serializers.IntegerField(default=20, min_value=1, max_value=50)
    
    def validate(self, data):
        if (data.get('latitude') is not None) != (data.get('longitude') is not None):
            raise serializers.ValidationError(
                "Both latitude and longitude must be provided together, or neither"
            )
        return data


class EmergencyMatchingRequestSerializer(serializers.Serializer):
    """Serializer for emergency matching request"""
    
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    emergency_type = serializers.CharField(required=True)
    required_specialties = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    max_distance_km = serializers.IntegerField(default=50, min_value=1, max_value=200)
    max_results = serializers.IntegerField(default=5, min_value=1, max_value=10)
    
    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
    
    def validate_emergency_type(self, value):
        valid_types = ['medical', 'accident', 'cardiac', 'trauma', 'respiratory', 'pediatric', 'other']
        if value not in valid_types:
            raise serializers.ValidationError(f"Emergency type must be one of: {valid_types}")
        return value


class HospitalAvailabilityResponseSerializer(serializers.Serializer):
    """Serializer for hospital availability response"""
    
    is_available = serializers.BooleanField()
    capacity_status = serializers.CharField()
    available_beds = serializers.IntegerField()
    emergency_beds_available = serializers.IntegerField()
    icu_beds_available = serializers.IntegerField()
    average_wait_time = serializers.IntegerField()
    emergency_wait_time = serializers.IntegerField()
    doctors_available = serializers.IntegerField()
    nurses_available = serializers.IntegerField()
    last_updated = serializers.DateTimeField()


class CommunicationRequestSerializer(serializers.Serializer):
    """Serializer for hospital communication request"""
    
    hospital_id = serializers.IntegerField(required=True)
    emergency_data = serializers.DictField(required=True)
    communication_channels = serializers.ListField(
        child=serializers.CharField(),
        default=['api', 'sms']
    )


class EmergencyResponseSerializer(serializers.ModelSerializer):
    """Serializer for Emergency Response model"""
    
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    
    class Meta:
        model = EmergencyResponse
        fields = [
            'id', 'hospital', 'hospital_name', 'response_time', 'accepted_patient',
            'reason_for_rejection', 'beds_available_at_response',
            'emergency_beds_available_at_response', 'alert_received_at',
            'response_sent_at'
        ]
        read_only_fields = ['id', 'response_sent_at']