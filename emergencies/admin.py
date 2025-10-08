# apps/emergencies/admin.py
from django.contrib import admin
from .models import EmergencyAlert, EmergencyStatusUpdate, EmergencyLocationUpdate

@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_name', 'priority', 'status', 'first_aider', 'created_at')
    list_filter = ('priority', 'status', 'emergency_type', 'created_at')
    search_fields = ('patient_name', 'first_aider__badge_number', 'first_aider__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(EmergencyStatusUpdate)
class EmergencyStatusUpdateAdmin(admin.ModelAdmin):
    list_display = ('emergency', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('emergency__patient_name', 'user__badge_number')
    readonly_fields = ('created_at',)

@admin.register(EmergencyLocationUpdate)
class EmergencyLocationUpdateAdmin(admin.ModelAdmin):
    list_display = ('emergency', 'latitude', 'longitude', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('emergency__patient_name',)
    readonly_fields = ('created_at',)