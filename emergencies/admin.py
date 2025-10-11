from django.contrib import admin
from .models import EmergencyAlert, EmergencySession, AlertVerification, EmergencyUpdate


@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    list_display = [
        'alert_id', 'user', 'emergency_type', 'priority', 'status', 
        'is_active', 'is_verified', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'emergency_type', 'is_active', 
        'is_verified', 'created_at'
    ]
    search_fields = ['alert_id', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['alert_id', 'created_at', 'updated_at']
    list_select_related = ['user']
    ordering = ['-created_at']


@admin.register(EmergencySession)
class EmergencySessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'alert', 'is_active', 'location_updates_count',
        'last_location_update', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['session_id', 'alert__alert_id']
    readonly_fields = ['session_id', 'created_at']
    list_select_related = ['alert']


@admin.register(AlertVerification)
class AlertVerificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'alert', 'verification_method', 'is_successful',
        'response_received', 'created_at'
    ]
    list_filter = ['verification_method', 'is_successful', 'response_received']
    search_fields = ['alert__alert_id']
    readonly_fields = ['created_at']
    list_select_related = ['alert']


@admin.register(EmergencyUpdate)
class EmergencyUpdateAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'alert', 'update_type', 'previous_status', 'new_status', 'created_at'
    ]
    list_filter = ['update_type', 'created_at']
    search_fields = ['alert__alert_id']
    readonly_fields = ['created_at']
    list_select_related = ['alert', 'created_by']