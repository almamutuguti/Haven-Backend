from django.contrib import admin
from .models import Location, HospitalLocation


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'latitude', 'longitude', 'city', 'county', 'is_primary', 'location_type']
    list_filter = ['is_primary', 'location_type', 'county', 'created_at']
    search_fields = ['user__email', 'formatted_address', 'city', 'county']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['user']


@admin.register(HospitalLocation)
class HospitalLocationAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_address', 'place_id', 'has_ambulance_bay']
    list_filter = ['has_ambulance_bay']
    search_fields = ['location__formatted_address', 'place_id']
    # readonly_fields = ['created_at', 'updated_at']
    
    def get_address(self, obj):
        return obj.location.formatted_address
    get_address.short_description = 'Address'