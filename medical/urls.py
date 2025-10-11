from django.urls import path
from . import views



urlpatterns = [
    # Medical Profile Management
    path('', views.medical_profile_management, name='medical-profile'),
    path('emergency-data/', views.get_emergency_data_packet, name='emergency-data'),
    path('fhir-data/', views.get_fhir_data, name='fhir-data'),
    path('emergency-summary/', views.get_emergency_summary, name='emergency-summary'),
    
    # Medical Conditions
    path('conditions/', views.medical_conditions_management, name='medical-conditions'),
    path('conditions/<int:condition_id>/', views.medical_condition_detail, name='medical-condition-detail'),
    
    # Allergies
    path('allergies/', views.allergies_management, name='allergies'),
    path('allergies/<int:allergy_id>/', views.allergies_management, name='allergy-detail'),
    
    # Medications
    path('medications/', views.medications_management, name='medications'),
    path('medications/<int:medication_id>/', views.medications_management, name='medication-detail'),
    
    # Emergency Contacts
    path('contacts/', views.emergency_contacts_management, name='emergency-contacts'),
    path('contacts/<int:contact_id>/', views.emergency_contacts_management, name='emergency-contact-detail'),
    path('contacts/<int:contact_id>/primary/', views.set_primary_contact, name='set-primary-contact'),
    
    # Insurance Information
    path('insurance/', views.insurance_management, name='insurance'),
    path('insurance/<int:insurance_id>/', views.insurance_management, name='insurance-detail'),
    
    # Surgical History
    path('surgical-history/', views.surgical_history_management, name='surgical-history'),
    path('surgical-history/<int:surgery_id>/', views.surgical_history_management, name='surgery-detail'),
]