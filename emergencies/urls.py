from django.urls import path
from . import views

urlpatterns = [
    # Alert management endpoints
    path('alert/', views.trigger_emergency_alert, name='trigger-emergency'),
    path('<str:alert_id>/status/', views.get_alert_status, name='alert-status'),
    path('<str:alert_id>/location/', views.update_alert_location, name='update-location'),
    path('<str:alert_id>/cancel/', views.cancel_emergency_alert, name='cancel-emergency'),
    path('<str:alert_id>/verify/', views.verify_emergency_alert, name='verify-emergency'),
    
    # History and updates
    path('history/', views.get_emergency_history, name='emergency-history'),
    path('<str:alert_id>/updates/', views.get_emergency_updates, name='emergency-updates'),
    
    # Admin endpoints
    path('active/', views.get_active_emergencies, name='active-emergencies'),
]