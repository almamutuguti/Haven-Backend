from django.urls import path
from . import views

urlpatterns = [
    # Medical Profile Management
    path('profile/', views.MedicalProfileAPIView.as_view(), name='medical-profile'),
    path('profile/emergency-data/', views.EmergencyDataPacketAPIView.as_view(), name='emergency-data'),
    path('profile/fhir-data/', views.FHIRDataAPIView.as_view(), name='fhir-data'),
    path('profile/emergency-summary/', views.EmergencySummaryAPIView.as_view(), name='emergency-summary'),
    
    # Medical Conditions
    path('profile/conditions/', views.MedicalConditionListCreateAPIView.as_view(), name='medical-conditions'),
    path('profile/conditions/<int:pk>/', views.MedicalConditionDetailAPIView.as_view(), name='medical-condition-detail'),
    
    # Allergies
    path('profile/allergies/', views.AllergyListCreateAPIView.as_view(), name='allergies'),
    path('profile/allergies/<int:pk>/', views.AllergyDetailAPIView.as_view(), name='allergy-detail'),
    
    # Medications
    path('profile/medications/', views.MedicationListCreateAPIView.as_view(), name='medications'),
    path('profile/medications/<int:pk>/', views.MedicationDetailAPIView.as_view(), name='medication-detail'),
    
    # Emergency Contacts
    path('profile/contacts/', views.EmergencyContactListCreateAPIView.as_view(), name='emergency-contacts'),
    path('profile/contacts/<int:pk>/', views.EmergencyContactDetailAPIView.as_view(), name='emergency-contact-detail'),
    path('profile/contacts/<int:contact_id>/primary/', views.SetPrimaryContactAPIView.as_view(), name='set-primary-contact'),
    
    # Insurance Information
    path('profile/insurance/', views.InsuranceListCreateAPIView.as_view(), name='insurance'),
    path('profile/insurance/<int:pk>/', views.InsuranceDetailAPIView.as_view(), name='insurance-detail'),
    
    # Surgical History
    path('profile/surgical-history/', views.SurgicalHistoryListCreateAPIView.as_view(), name='surgical-history'),
    path('profile/surgical-history/<int:pk>/', views.SurgicalHistoryDetailAPIView.as_view(), name='surgery-detail'),
]