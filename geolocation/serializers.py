from rest_framework import serializers
from .models import Location, HospitalLocation



class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model"""
    
    class Meta:
        model = Location
        fields = [
            'id', 'latitude', 'longitude', 'formatted_address', 
            'street', 'city', 'county', 'country', 'postal_code',
            'is_primary', 'location_type', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class HospitalLocationSerializer(serializers.ModelSerializer):
    """Serializer for HospitalLocation model"""
    location = LocationSerializer(read_only=True)
    
    class Meta:
        model = HospitalLocation
        fields = [
            'id', 'location', 'place_id', 'google_maps_url',
            'accessibility_notes', 'entrance_instructions',
            'has_ambulance_bay', 'emergency_entrance_coordinates'
        ]
        read_only_fields = ['id']


class GeocodingRequestSerializer(serializers.Serializer):
    """Serializer for geocoding requests"""
    address = serializers.CharField(max_length=500, required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    
    def validate(self, data):
        if not data.get('address') and (not data.get('latitude') or not data.get('longitude')):
            raise serializers.ValidationError(
                "Either 'address' or both 'latitude' and 'longitude' must be provided"
            )
        return data


class GeocodingResponseSerializer(serializers.Serializer):
    """Serializer for geocoding responses"""
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    formatted_address = serializers.CharField()
    street = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    county = serializers.CharField(allow_blank=True)
    country = serializers.CharField(allow_blank=True)
    postal_code = serializers.CharField(allow_blank=True)


class DistanceRequestSerializer(serializers.Serializer):
    """Serializer for distance calculation requests"""
    origin_latitude = serializers.FloatField()
    origin_longitude = serializers.FloatField()
    destination_latitude = serializers.FloatField()
    destination_longitude = serializers.FloatField()
    mode = serializers.ChoiceField(
        choices=['driving', 'walking', 'bicycling', 'transit'],
        default='driving'
    )


class DistanceResponseSerializer(serializers.Serializer):
    """Serializer for distance calculation responses"""
    distance_meters = serializers.IntegerField()
    distance_text = serializers.CharField()
    duration_seconds = serializers.IntegerField()
    duration_text = serializers.CharField()


class NearbyHospitalsRequestSerializer(serializers.Serializer):
    """Serializer for nearby hospitals requests"""
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    radius = serializers.IntegerField(default=5000, min_value=100, max_value=50000)
    keyword = serializers.CharField(required=False, default='hospital')


class HospitalSearchResultSerializer(serializers.Serializer):
    """Serializer for hospital search results"""
    place_id = serializers.CharField()
    name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    address = serializers.CharField()
    rating = serializers.FloatField(allow_null=True)
    user_ratings_total = serializers.IntegerField(default=0)
    types = serializers.ListField(child=serializers.CharField())
    business_status = serializers.CharField()
    permanently_closed = serializers.BooleanField(default=False)