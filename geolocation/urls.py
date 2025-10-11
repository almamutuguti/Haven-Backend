from django.urls import path
from . import views



urlpatterns = [
    # Geocoding endpoints
    path('geocode/', views.geocode_address, name='geocode-address'),
    
    # Distance calculation endpoints
    path('distance/', views.calculate_distance, name='calculate-distance'),
    
    # Hospital search endpoints
    path('hospitals/nearby/', views.find_nearby_hospitals, name='nearby-hospitals'),
    
    # Location management endpoints
    path('locations/', views.manage_locations, name='manage-locations'),
    path('locations/<int:location_id>/', views.manage_locations, name='manage-location'),
    path('locations/<int:location_id>/primary/', views.set_primary_location, name='set-primary-location'),
]