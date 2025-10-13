from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('refresh-token/', views.RefreshTokenAPIView.as_view(), name='refresh-token'),
    path('emergency-bypass/', views.EmergencyBypassAPIView.as_view(), name='emergency-bypass'),
    
    # User management endpoints
    path('profile/', views.UserProfileAPIView.as_view(), name='user-profile'),
    path('users/', views.UserListAPIView.as_view(), name='user-list'),
    path('users/active-count/', views.ActiveUsersCountAPIView.as_view(), name='active-users-count'),
    path('users/by-type/', views.UsersByTypeAPIView.as_view(), name='users-by-type'),
]