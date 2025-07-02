from rest_framework import permissions

class IsSocietyManager(permissions.BasePermission):
    """
    Custom permission to only allow society managers to access their own societies.
    """
    def has_permission(self, request, view):
        return request.user.role == 'FARMER'

    def has_object_permission(self, request, view, obj):
        return obj.manager == request.user

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to modify objects.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role == 'ADMIN'

class IsSocietyApproved(permissions.BasePermission):
    """
    Custom permission to only allow actions on approved societies.
    """
    def has_object_permission(self, request, view, obj):
        return obj.is_approved
