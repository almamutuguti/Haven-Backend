from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('api/register/', views.register_user, name='register'),
    path('api/login/', views.login_user, name='login'),
    
    # Token management
    path('api/refresh/', views.refresh_token, name='token-refresh'),
    path('api/logout/', views.logout, name='logout'),
    
    # Emergency access
    path('api/emergency-bypass/', views.emergency_bypass, name='emergency-bypass'),
    
    # Profile
    path('api/profile/', views.user_profile, name='user-profile'),
]