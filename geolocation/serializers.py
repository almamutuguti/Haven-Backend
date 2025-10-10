from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import Location, GeoFence, LocationLog

# Serializers for the geolocation app that can be used by other apps for location data handling
class LocationSerializer(serializers.ModelSerializer):
    
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    
    class Meta:
        model = Location
        fields = [
            'id', 'user', 'name', 'address', 'city', 'county', 'country',
            'latitude', 'longitude', 'coordinates', 'accuracy', 'altitude',
            'timestamp', 'source', 'emergency_alert', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)
        
        if latitude and longitude:
            validated_data['coordinates'] = Point(longitude, latitude)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)
        
        if latitude and longitude:
            validated_data['coordinates'] = Point(longitude, latitude)
        
        return super().update(instance, validated_data)


class GeoFenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoFence
        fields = [
            'id', 'name', 'description', 'boundary', 'type', 
            'hospital', 'radius', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LocationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class ReverseGeocodeSerializer(serializers.Serializer):
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    language = serializers.CharField(default='en')


class GeocodeSerializer(serializers.Serializer):
    address = serializers.CharField(required=True)
    city = serializers.CharField(required=False)
    county = serializers.CharField(required=False)
    country = serializers.CharField(default='Kenya')


class DistanceMatrixSerializer(serializers.Serializer):
    origins = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    destinations = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    mode = serializers.ChoiceField(
        choices=[('driving', 'Driving'), ('walking', 'Walking'), ('bicycling', 'Bicycling')],
        default='driving'
    )


class NearbySearchSerializer(serializers.Serializer):
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    radius = serializers.IntegerField(default=5000)  # meters
    type = serializers.CharField(required=False)  # hospital, pharmacy, etc.
    keyword = serializers.CharField(required=False)