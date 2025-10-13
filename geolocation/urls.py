from django.urls import path
from . import views

urlpatterns = [
    # Geocoding endpoints
    path('geocode/', views.GeocodeAddressAPIView.as_view(), name='geocode-address'),
    
    # Distance calculation endpoints
    path('distance/', views.CalculateDistanceAPIView.as_view(), name='calculate-distance'),
    
    # Hospital search endpoints
    path('hospitals/nearby/', views.FindNearbyHospitalsAPIView.as_view(), name='nearby-hospitals'),
    
    # Location management endpoints
    path('locations/', views.LocationListCreateAPIView.as_view(), name='location-list-create'),
    path('locations/<int:pk>/', views.LocationDetailAPIView.as_view(), name='location-detail'),
    path('locations/<int:location_id>/primary/', views.SetPrimaryLocationAPIView.as_view(), name='set-primary-location'),
]