from django.urls import path
from . import views



urlpatterns = [
    # Discovery endpoints
    path('nearby/', views.discover_nearby_hospitals, name='nearby-hospitals'),
    path('search/', views.search_hospitals, name='search-hospitals'),
    
    # Hospital details and capabilities
    path('<int:hospital_id>/', views.get_hospital_details, name='hospital-details'),
    path('<int:hospital_id>/capabilities/', views.get_hospital_capabilities, name='hospital-capabilities'),
    path('<int:hospital_id>/availability/', views.check_hospital_availability, name='hospital-availability'),
    path('<int:hospital_id>/statistics/', views.get_hospital_statistics, name='hospital-statistics'),
    
    # Matching endpoints
    path('matching/', views.match_hospitals_for_emergency, name='hospital-matching'),
    path('<int:hospital_id>/fallbacks/', views.get_fallback_hospitals, name='fallback-hospitals'),
    
    # Communication endpoints
    path('<int:hospital_id>/alert/', views.send_hospital_alert, name='hospital-alert'),
    path('comms/status/<str:alert_id>/', views.get_communication_status, name='communication-status'),
    path('comms/fallback/', views.activate_fallback_communication, name='fallback-communication'),
    
    # Ratings endpoints
    path('ratings/', views.hospital_ratings, name='all-ratings'),
    path('<int:hospital_id>/ratings/', views.hospital_ratings, name='hospital-ratings'),
]