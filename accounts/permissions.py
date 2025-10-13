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

class IsEmergencyAccess(permissions.BasePermission):
    """Allows access during emergency bypass"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   getattr(request.auth, 'emergency_access', False))