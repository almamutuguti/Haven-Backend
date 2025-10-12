from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import (
    EmergencyHospitalCommunication,
    CommunicationLog,
    HospitalPreparationChecklist,
    FirstAiderAssessment
)

@admin.register(EmergencyHospitalCommunication)
class EmergencyHospitalCommunicationAdmin(admin.ModelAdmin):
    list_display = [
        'alert_reference_id', 'hospital', 'first_aider', 'status', 
        'priority', 'victim_name', 'created_at', 'communication_actions'
    ]
    list_filter = ['status', 'priority', 'hospital', 'created_at']
    search_fields = ['alert_reference_id', 'victim_name', 'hospital__name']
    readonly_fields = ['created_at', 'updated_at', 'alert_reference_id']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Emergency Information', {
            'fields': ('emergency_alert_id', 'alert_reference_id', 'hospital', 'first_aider')
        }),
        ('Victim Information', {
            'fields': ('victim_name', 'victim_age', 'victim_gender')
        }),
        ('Emergency Assessment', {
            'fields': ('chief_complaint', 'vital_signs', 'initial_assessment', 'first_aid_provided')
        }),
        ('Hospital Logistics', {
            'fields': ('estimated_arrival_minutes', 'required_specialties', 'equipment_needed', 'blood_type_required')
        }),
        ('Communication Status', {
            'fields': ('status', 'priority', 'communication_attempts')
        }),
        ('Hospital Response', {
            'fields': (
                'hospital_acknowledged_at', 'hospital_acknowledged_by',
                'doctors_ready', 'nurses_ready', 'equipment_ready', 
                'bed_ready', 'blood_available', 'hospital_preparation_notes'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'sent_to_hospital_at', 'hospital_ready_at', 'patient_arrived_at')
        }),
    )
    
    def communication_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">View Logs</a>&nbsp;'
            '<a class="button" href="{}">Retry</a>',
            f'../communicationlog/?communication__id={obj.id}',
            f'{obj.id}/retry-communication/'
        )
    communication_actions.short_description = 'Actions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hospital', 'first_aider')
    
    def retry_communication(self, request, communication_id, *args, **kwargs):
        """
        Custom admin action to retry failed communications
        """
        from .services import HospitalCommunicationService
        
        communication = EmergencyHospitalCommunication.objects.get(id=communication_id)
        service = HospitalCommunicationService(communication)
        success = service.send_emergency_alert()
        
        if success:
            self.message_user(request, "Communication retried successfully")
        else:
            self.message_user(request, "Failed to retry communication", level='error')
        
        return HttpResponseRedirect(reverse('admin:hospital_comms_emergencyhospitalcommunication_changelist'))
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:communication_id>/retry-communication/',
                self.admin_site.admin_view(self.retry_communication),
                name='retry-communication',
            ),
        ]
        return custom_urls + urls

@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ['communication', 'channel', 'direction', 'message_type', 'is_successful', 'sent_at']
    list_filter = ['channel', 'direction', 'is_successful', 'sent_at']
    search_fields = ['communication__alert_reference_id', 'message_content']
    readonly_fields = ['sent_at']
    date_hierarchy = 'sent_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('communication')

@admin.register(HospitalPreparationChecklist)
class HospitalPreparationChecklistAdmin(admin.ModelAdmin):
    list_display = ['communication', 'completion_percentage', 'checklist_completed', 'updated_at']
    list_filter = ['checklist_completed', 'updated_at']
    search_fields = ['communication__alert_reference_id', 'notes']
    readonly_fields = ['completion_percentage', 'created_at', 'updated_at']
    date_hierarchy = 'updated_at'
    
    fieldsets = (
        ('Medical Team Preparation', {
            'fields': (
                'emergency_doctor_assigned', 'specialist_doctor_notified', 
                'nursing_team_ready', 'anesthesiologist_alerted'
            )
        }),
        ('Facility Preparation', {
            'fields': (
                'emergency_bed_prepared', 'operating_room_reserved', 
                'icu_bed_available'
            )
        }),
        ('Equipment Preparation', {
            'fields': (
                'vital_monitors_ready', 'ventilator_available', 
                'defibrillator_ready', 'emergency_medications_ready'
            )
        }),
        ('Diagnostic Preparation', {
            'fields': (
                'lab_tests_ordered', 'imaging_ready', 
                'blood_products_available'
            )
        }),
        ('Support Services', {
            'fields': (
                'pharmacy_alerted', 'blood_bank_notified', 
                'transport_team_ready'
            )
        }),
        ('Completion Status', {
            'fields': (
                'checklist_completed', 'completed_at', 'completed_by', 'notes'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def completion_percentage(self, obj):
        return f"{obj.completion_percentage}%"
    completion_percentage.short_description = 'Completion %'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('communication', 'completed_by')

@admin.register(FirstAiderAssessment)
class FirstAiderAssessmentAdmin(admin.ModelAdmin):
    list_display = ['communication', 'triage_category', 'gcs_total', 'pain_level', 'created_at']
    list_filter = ['triage_category', 'created_at']
    search_fields = ['communication__alert_reference_id', 'chief_complaint']
    readonly_fields = ['created_at', 'updated_at', 'gcs_total']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Glasgow Coma Scale', {
            'fields': (
                'gcs_eyes', 'gcs_verbal', 'gcs_motor', 'gcs_total'
            )
        }),
        ('Vital Signs', {
            'fields': (
                'heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic',
                'respiratory_rate', 'oxygen_saturation', 'temperature'
            )
        }),
        ('Trauma Assessment', {
            'fields': (
                'mechanism_of_injury', 'injuries_noted', 'pain_level'
            )
        }),
        ('Medical History', {
            'fields': (
                'known_allergies', 'current_medications', 'past_medical_history',
                'last_oral_intake'
            )
        }),
        ('First Aid Interventions', {
            'fields': (
                'interventions_provided', 'medications_administered'
            )
        }),
        ('Triage & Observations', {
            'fields': (
                'triage_category', 'scene_observations', 'safety_concerns'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('communication')

# Custom Admin Actions
def retry_failed_communications(modeladmin, request, queryset):
    """
    Admin action to retry multiple failed communications
    """
    from .services import HospitalCommunicationService
    
    success_count = 0
    fail_count = 0
    
    for communication in queryset.filter(status__in=['failed', 'pending']):
        service = HospitalCommunicationService(communication)
        if service.send_emergency_alert():
            success_count += 1
        else:
            fail_count += 1
    
    modeladmin.message_user(
        request, 
        f"Successfully retried {success_count} communications. Failed: {fail_count}"
    )

retry_failed_communications.short_description = "Retry selected failed communications"

def mark_as_ready(modeladmin, request, queryset):
    """
    Admin action to mark communications as hospital ready
    """
    updated = queryset.update(
        status='ready',
        doctors_ready=True,
        nurses_ready=True,
        equipment_ready=True,
        bed_ready=True,
        hospital_ready_at=admin.utils.timezone.now()
    )
    modeladmin.message_user(request, f"Marked {updated} communications as ready")

mark_as_ready.short_description = "Mark selected as hospital ready"

# Add actions to the EmergencyHospitalCommunication admin
EmergencyHospitalCommunicationAdmin.actions = [retry_failed_communications, mark_as_ready]