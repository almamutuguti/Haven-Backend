from django.contrib import admin
from .models import (
    MedicalProfile, MedicalCondition, Allergy, Medication,
    EmergencyContact, InsuranceInformation, SurgicalHistory, MedicalDocument
)


class MedicalConditionInline(admin.TabularInline):
    model = MedicalCondition
    extra = 1
    fields = ['name', 'severity', 'status', 'is_critical', 'diagnosis_date']


class AllergyInline(admin.TabularInline):
    model = Allergy
    extra = 1
    fields = ['allergen', 'allergy_type', 'severity', 'reaction']


class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 1
    fields = ['name', 'dosage', 'frequency', 'status', 'is_critical']


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1
    fields = ['full_name', 'relationship', 'phone_number', 'is_primary']


class InsuranceInformationInline(admin.TabularInline):
    model = InsuranceInformation
    extra = 1
    fields = ['insurance_provider', 'policy_number', 'is_active', 'verification_status']


class SurgicalHistoryInline(admin.TabularInline):
    model = SurgicalHistory
    extra = 1
    fields = ['procedure_name', 'date_performed', 'hospital']


@admin.register(MedicalProfile)
class MedicalProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'blood_type', 'organ_donor', 'dnr_order', 
        'data_consent_given', 'created_at'
    ]
    list_filter = [
        'blood_type', 'organ_donor', 'dnr_order', 
        'data_consent_given', 'created_at'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'consent_given_at']
    list_select_related = ['user']
    inlines = [
        MedicalConditionInline, AllergyInline, MedicationInline,
        EmergencyContactInline, InsuranceInformationInline, SurgicalHistoryInline
    ]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'blood_type', 'height_cm', 'weight_kg')
        }),
        ('Emergency Information', {
            'fields': ('organ_donor', 'dnr_order', 'advance_directive')
        }),
        ('Medical Care', {
            'fields': ('primary_care_physician', 'physician_phone', 'last_medical_review')
        }),
        ('Data Privacy', {
            'fields': ('data_consent_given', 'consent_given_at', 'data_sharing_preferences')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MedicalCondition)
class MedicalConditionAdmin(admin.ModelAdmin):
    list_display = [
        'medical_profile', 'name', 'severity', 'status', 
        'is_critical', 'diagnosis_date', 'created_at'
    ]
    list_filter = ['severity', 'status', 'is_critical', 'is_chronic', 'created_at']
    search_fields = ['medical_profile__user__email', 'name', 'icd_code']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['medical_profile', 'medical_profile__user']


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = [
        'medical_profile', 'allergen', 'allergy_type', 'severity',
        'epi_pen_required', 'diagnosis_date', 'created_at'
    ]
    list_filter = ['allergy_type', 'severity', 'epi_pen_required', 'created_at']
    search_fields = ['medical_profile__user__email', 'allergen', 'reaction']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['medical_profile', 'medical_profile__user']


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = [
        'medical_profile', 'name', 'dosage', 'frequency', 'status',
        'is_critical', 'start_date', 'created_at'
    ]
    list_filter = ['frequency', 'status', 'is_critical', 'created_at']
    search_fields = ['medical_profile__user__email', 'name', 'purpose']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['medical_profile', 'medical_profile__user']


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = [
        'medical_profile', 'full_name', 'relationship', 'phone_number',
        'is_primary', 'can_make_medical_decisions', 'created_at'
    ]
    list_filter = ['relationship', 'is_primary', 'can_make_medical_decisions', 'created_at']
    search_fields = ['medical_profile__user__email', 'full_name', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['medical_profile', 'medical_profile__user']


@admin.register(InsuranceInformation)
class InsuranceInformationAdmin(admin.ModelAdmin):
    list_display = [
        'medical_profile', 'insurance_provider', 'policy_number',
        'is_active', 'verification_status', 'created_at'
    ]
    list_filter = ['is_active', 'verification_status', 'emergency_coverage', 'created_at']
    search_fields = ['medical_profile__user__email', 'insurance_provider', 'policy_number']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['medical_profile', 'medical_profile__user']


@admin.register(SurgicalHistory)
class SurgicalHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'medical_profile', 'procedure_name', 'date_performed',
        'surgeon', 'has_implants', 'created_at'
    ]
    list_filter = ['has_implants', 'date_performed', 'created_at']
    search_fields = ['medical_profile__user__email', 'procedure_name', 'surgeon']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['medical_profile', 'medical_profile__user']


@admin.register(MedicalDocument)
class MedicalDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'medical_profile', 'document_type', 'title', 'file_name',
        'access_level', 'created_at'
    ]
    list_filter = ['document_type', 'access_level', 'is_encrypted', 'created_at']
    search_fields = ['medical_profile__user__email', 'title', 'file_name']
    readonly_fields = ['created_at', 'updated_at', 'file_size']
    list_select_related = ['medical_profile', 'medical_profile__user']