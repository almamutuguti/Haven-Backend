from rest_framework import permissions

class IsFirstAider(permissions.BasePermission):
    """Allows access only to first aiders"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role == 'first_aider')

class IsHospitalStaff(permissions.BasePermission):
    """Allows access only to hospital staff"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role == 'hospital_staff')

class IsSystemAdmin(permissions.BasePermission):
    """Allows access only to system admins"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role == 'system_admin')

class IsHospitalAdmin(permissions.BasePermission):  # NEW
    """Allows access only to hospital admins"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role == 'hospital_admin')

class IsOrganizationAdmin(permissions.BasePermission):  # NEW
    """Allows access only to organization admins"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role == 'organization_admin')

class IsEmergencyAccess(permissions.BasePermission):
    """Allows access during emergency bypass"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   getattr(request.auth, 'emergency_access', False))

# Combined permissions for dashboard access
class CanAccessHospitalDashboard(permissions.BasePermission):  # NEW
    """Allows access to hospital dashboard for hospital staff and admins"""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and 
                   user.role in ['hospital_staff', 'hospital_admin'])

class CanAccessOrganizationDashboard(permissions.BasePermission):  # NEW
    """Allows access to organization dashboard for first aiders and org admins"""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and 
                   user.role in ['first_aider', 'organization_admin'])