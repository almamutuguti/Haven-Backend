from django.urls import path
from . import views

urlpatterns = [
    # Alert management endpoints
    path('alert/', views.TriggerEmergencyAlertAPIView.as_view(), name='trigger-emergency'),
    path('<str:alert_id>/status/', views.AlertStatusAPIView.as_view(), name='alert-status'),
    path('<str:alert_id>/location/', views.UpdateAlertLocationAPIView.as_view(), name='update-location'),
    path('<str:alert_id>/cancel/', views.CancelEmergencyAlertAPIView.as_view(), name='cancel-emergency'),
    path('<str:alert_id>/verify/', views.VerifyEmergencyAlertAPIView.as_view(), name='verify-emergency'),
    
    # History and updates
    path('history/', views.EmergencyHistoryAPIView.as_view(), name='emergency-history'),
    path('<str:alert_id>/updates/', views.EmergencyUpdatesAPIView.as_view(), name='emergency-updates'),
    
    # Admin endpoints
    path('active/', views.ActiveEmergenciesAPIView.as_view(), name='active-emergencies'),
]