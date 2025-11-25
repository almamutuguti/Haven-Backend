from django.urls import path
from . import views

urlpatterns = [
    # ============================================================================
    # AUTHENTICATION ENDPOINTS
    # ============================================================================
    path('api/register/', views.RegisterAPIView.as_view(), name='register'),
    path('api/login/', views.LoginAPIView.as_view(), name='login'),
    path('api/logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('api/refresh-token/', views.RefreshTokenAPIView.as_view(), name='refresh-token'),
    path('api/change-password/', views.ChangePasswordAPIView.as_view(), name='change-password'),  
    
    # ============================================================================
    # USER MANAGEMENT ENDPOINTS (SYSTEM ADMIN ONLY)
    # ============================================================================
    path('api/user/profile/', views.UserProfileAPIView.as_view(), name='user-profile'),
    path('api/users/', views.UserListAPIView.as_view(), name='user-list'),
    path('api/users/active-count/', views.ActiveUsersCountAPIView.as_view(), name='active-users-count'),
    path('api/users/by-type/', views.UsersByTypeAPIView.as_view(), name='users-by-type'),
    path('api/users/<int:user_id>/update-profile/', views.UserUpdateAPIView.as_view(), name='update-user-profile'),
    path('api/users/<int:user_id>/delete/', views.AdminUserDeleteAPIView.as_view(), name='delete-user'),
    
    # ============================================================================
    # HOSPITAL & ORGANIZATION ENDPOINTS
    # ============================================================================
    path('api/hospitals/', views.HospitalListAPIView.as_view(), name='hospital-list'),
    path('api/organizations/', views.OrganizationListAPIView.as_view(), name='organization-list'),
    
    # ============================================================================
    # DASHBOARD ACCESS CONTROL ENDPOINTS
    # ============================================================================
    path('api/dashboard/access/', views.DashboardAccessAPIView.as_view(), name='dashboard-access'),
    path('api/dashboard/check-role/', views.UserRoleCheckAPIView.as_view(), name='check-role'),
    
    # ============================================================================
    # SYSTEM ADMIN DASHBOARD ENDPOINTS
    # ============================================================================
    path('api/dashboard/system-admin/overview/', views.SystemAdminOverviewAPIView.as_view(), name='system-admin-overview'),
    path('api/dashboard/system-admin/users/', views.SystemAdminUsersAPIView.as_view(), name='system-admin-users'),
    
    # ============================================================================
    # HOSPITAL ADMIN DASHBOARD ENDPOINTS
    # ============================================================================
    path('api/dashboard/hospital-admin/overview/', views.HospitalAdminOverviewAPIView.as_view(), name='hospital-admin-overview'),
    path('api/dashboard/hospital-admin/staff/', views.HospitalStaffManagementAPIView.as_view(), name='hospital-admin-staff'),
    path('api/dashboard/hospital-admin/first-aiders/', views.HospitalAssociatedFirstAidersAPIView.as_view(), name='hospital-admin-first-aiders'),
    
    # ============================================================================
    # ORGANIZATION ADMIN DASHBOARD ENDPOINTS
    # ============================================================================
    path('api/dashboard/organization-admin/overview/', views.OrganizationAdminOverviewAPIView.as_view(), name='organization-admin-overview'),
    path('api/dashboard/organization-admin/first-aiders/', views.OrganizationFirstAidersManagementAPIView.as_view(), name='organization-admin-first-aiders'),
    path('api/dashboard/organization-admin/certifications/', views.OrganizationCertificationsAPIView.as_view(), name='organization-admin-certifications'),
]