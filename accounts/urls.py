from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('api/register/', views.RegisterAPIView.as_view(), name='register'),
    path('api/login/', views.LoginAPIView.as_view(), name='login'),
    path('api/logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('api/refresh-token/', views.RefreshTokenAPIView.as_view(), name='refresh-token'),
    path('api/change-password/', views.ChangePasswordAPIView.as_view(), name='change-password'),  
    
    # User management endpoints
    path('api/user/profile/', views.UserProfileAPIView.as_view(), name='user-profile'),
    path('api/users/', views.UserListAPIView.as_view(), name='user-list'),
    path('api/users/active-count/', views.ActiveUsersCountAPIView.as_view(), name='active-users-count'),
    path('api/users/by-type/', views.UsersByTypeAPIView.as_view(), name='users-by-type'),
    path('api/users/<int:user_id>/update-profile/', views.UserUpdateAPIView.as_view(), name='update-user-profile'),
    path('api/users/<int:user_id>/delete/', views.AdminUserDeleteAPIView.as_view(), name='delete-user'),
    # path('api/users/edit/', views.EditProfileAPIView.as_view(), name='edit-user'),

    # Hospital and Organization endpoints
    path('api/hospitals/', views.HospitalListAPIView.as_view(), name='hospital-list'),
    path('api/organizations/', views.OrganizationListAPIView.as_view(), name='organization-list'),
]
