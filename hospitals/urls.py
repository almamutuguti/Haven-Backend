from django.urls import path
from . import views

urlpatterns = [
    # Discovery endpoints
    path('search/', views.SearchHospitalsAPIView.as_view(), name='search-hospitals'),
    
    # Hospital details and capabilities
    path('<int:hospital_id>/', views.HospitalDetailAPIView.as_view(), name='hospital-details'),
    path('<int:hospital_id>/capabilities/', views.HospitalCapabilitiesAPIView.as_view(), name='hospital-capabilities'),
    path('<int:hospital_id>/availability/', views.CheckHospitalAvailabilityAPIView.as_view(), name='hospital-availability'),
    path('<int:hospital_id>/statistics/', views.HospitalStatisticsAPIView.as_view(), name='hospital-statistics'),
    path('', views.HospitalListCreateAPIView.as_view(), name='hospital-list-create'),
    path('<int:id>/', views.HospitalRetrieveUpdateDestroyAPIView.as_view(), name='hospital-detail'),
    path('<int:id>/update-status/', views.HospitalStatusUpdateAPIView.as_view(), name='hospital-update-status'),
    
    # Matching endpoints
    path('matching/', views.MatchHospitalsForEmergencyAPIView.as_view(), name='hospital-matching'),
    path('<int:hospital_id>/fallbacks/', views.GetFallbackHospitalsAPIView.as_view(), name='fallback-hospitals'),
    
    # Communication endpoints
    path('<int:hospital_id>/alert/', views.SendHospitalAlertAPIView.as_view(), name='hospital-alert'),
    path('comms/status/<str:alert_id>/', views.GetCommunicationStatusAPIView.as_view(), name='communication-status'),
    path('comms/fallback/', views.ActivateFallbackCommunicationAPIView.as_view(), name='fallback-communication'),
    
    # Ratings endpoints
    path('ratings/', views.HospitalRatingListCreateAPIView.as_view(), name='all-ratings'),
    path('<int:hospital_id>/ratings/', views.HospitalRatingDetailAPIView.as_view(), name='hospital-ratings'),
]