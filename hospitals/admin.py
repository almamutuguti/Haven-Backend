from django.contrib import admin
from .models import (
    Hospital, HospitalSpecialty, HospitalCapacity,
    HospitalRating, EmergencyResponse, HospitalWorkingHours
)


class HospitalSpecialtyInline(admin.TabularInline):
    model = HospitalSpecialty
    extra = 1
    fields = ['specialty', 'capability_level', 'is_available', 'notes']


class HospitalCapacityInline(admin.StackedInline):
    model = HospitalCapacity
    extra = 1
    fields = [
        'total_beds', 'available_beds', 'emergency_beds_total', 'emergency_beds_available',
        'icu_beds_total', 'icu_beds_available', 'average_wait_time', 'emergency_wait_time',
        'doctors_available', 'nurses_available', 'is_accepting_patients', 'capacity_status'
    ]


class HospitalWorkingHoursInline(admin.TabularInline):
    model = HospitalWorkingHours
    extra = 7
    max_num = 7
    fields = [
        'day', 'opens_at', 'closes_at', 'emergency_opens_at', 'emergency_closes_at',
        'is_24_hours', 'is_emergency_24_hours', 'is_closed'
    ]


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'hospital_type', 'level', 'is_operational', 
        'accepts_emergencies', 'is_verified', 'created_at'
    ]
    list_filter = [
        'hospital_type', 'level', 'is_operational', 
        'accepts_emergencies', 'is_verified', 'created_at'
    ]
    search_fields = ['name', 'mfl_code', 'location__location__city', 'location__location__county']
    readonly_fields = ['created_at', 'updated_at', 'verified_at']
    list_select_related = ['location']
    inlines = [HospitalSpecialtyInline, HospitalCapacityInline, HospitalWorkingHoursInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'hospital_type', 'level', 
                'phone', 'emergency_phone', 'email', 'website'
            )
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Identification', {
            'fields': ('place_id', 'mfl_code')
        }),
        ('Status', {
            'fields': (
                'is_operational', 'is_verified', 'accepts_emergencies',
                'verified_at'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HospitalSpecialty)
class HospitalSpecialtyAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'specialty', 'capability_level', 'is_available']
    list_filter = ['specialty', 'capability_level', 'is_available']
    search_fields = ['hospital__name', 'specialty']
    list_select_related = ['hospital']


@admin.register(HospitalCapacity)
class HospitalCapacityAdmin(admin.ModelAdmin):
    list_display = [
        'hospital', 'capacity_status', 'available_beds', 
        'emergency_beds_available', 'is_accepting_patients', 'last_updated'
    ]
    list_filter = ['capacity_status', 'is_accepting_patients', 'last_updated']
    search_fields = ['hospital__name']
    readonly_fields = ['last_updated']
    list_select_related = ['hospital']


@admin.register(HospitalRating)
class HospitalRatingAdmin(admin.ModelAdmin):
    list_display = [
        'hospital', 'user', 'overall_rating', 'was_emergency', 
        'is_verified', 'is_approved', 'created_at'
    ]
    list_filter = [
        'overall_rating', 'was_emergency', 'is_verified', 
        'is_approved', 'created_at'
    ]
    search_fields = ['hospital__name', 'user__email', 'review_title']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['hospital', 'user']


@admin.register(EmergencyResponse)
class EmergencyResponseAdmin(admin.ModelAdmin):
    list_display = [
        'hospital', 'response_time', 'accepted_patient', 
        'alert_received_at', 'response_sent_at'
    ]
    list_filter = ['accepted_patient', 'alert_received_at', 'response_sent_at']
    search_fields = ['hospital__name']
    readonly_fields = ['response_sent_at']
    list_select_related = ['hospital']


@admin.register(HospitalWorkingHours)
class HospitalWorkingHoursAdmin(admin.ModelAdmin):
    list_display = [
        'hospital', 'day', 'opens_at', 'closes_at', 
        'is_24_hours', 'is_emergency_24_hours', 'is_closed'
    ]
    list_filter = ['day', 'is_24_hours', 'is_emergency_24_hours', 'is_closed']
    search_fields = ['hospital__name']
    list_select_related = ['hospital']