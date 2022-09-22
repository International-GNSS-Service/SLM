from rest_framework import permissions
from slm.models import Alert


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user:
            return request.user.is_superuser
        return False


class IsUserOrAdmin(permissions.BasePermission):
    """
    """
    def has_object_permission(self, request, view, obj):
        if request.user:
            return request.user.is_superuser or request.user == obj
        return False


class UpdateAdminOnly(permissions.BasePermission):
    """
    """
    def has_permission(self, request, view):
        if view.action in {'update', 'partial_update'}:
            return request.user.is_superuser
        return True


class CanDeleteAlert(permissions.BasePermission):
    """
    """
    def has_object_permission(self, request, view, obj):
        if view.action in {'destroy'}:
            if request.user.is_superuser:
                return True
            return obj in Alert.objects.accessible_by(request.user)
        return True


class CanEditSite(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.user:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        return (
                request.user and (
                    request.user.is_superuser or
                    obj.owner == request.user or
                    request.user.agency in obj.agencies
                )
            )

