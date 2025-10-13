from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('api/register/', views.RegisterAPIView.as_view(), name='register'),
    path('api/login/', views.LoginAPIView.as_view(), name='login'),
    path('api/logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('api/refresh-token/', views.RefreshTokenAPIView.as_view(), name='refresh-token'),
    path('api/emergency-bypass/', views.EmergencyBypassAPIView.as_view(), name='emergency-bypass'),
    
    # User management endpoints
    path('api/profile/', views.UserProfileAPIView.as_view(), name='user-profile'),
    path('api/users/', views.UserListAPIView.as_view(), name='user-list'),
    path('api/users/active-count/', views.ActiveUsersCountAPIView.as_view(), name='active-users-count'),
    path('api/users/by-type/', views.UsersByTypeAPIView.as_view(), name='users-by-type'),
]