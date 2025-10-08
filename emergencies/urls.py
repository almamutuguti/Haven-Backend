from django.urls import path
from . import views

urlpatterns = [
    # Emergency alerts
    path('alert/', views.create_emergency_alert, name='create-emergency'),
    path('alert/<uuid:emergency_id>/', views.get_emergency_details, name='emergency-details'),
    path('alert/<uuid:emergency_id>/status/', views.update_emergency_status, name='update-emergency-status'),
    path('alert/<uuid:emergency_id>/location/', views.update_emergency_location, name='update-emergency-location'),
    path('alert/<uuid:emergency_id>/cancel/', views.cancel_emergency_alert, name='cancel-emergency'),
    path('alert/<uuid:emergency_id>/status-updates/', views.get_emergency_status_updates, name='emergency-status-updates'),
    
    # Emergency history
    path('history/', views.get_emergency_history, name='emergency-history'),
]