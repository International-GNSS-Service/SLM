from rest_framework import permissions

from slm.models import Alert, Site


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user:
            return request.user.is_superuser
        return False


class IsUserOrAdmin(permissions.BasePermission):
    """ """

    def has_object_permission(self, request, view, obj):
        if request.user:
            return request.user.is_superuser or request.user == obj
        return False


class UpdateAdminOnly(permissions.BasePermission):
    """ """

    def has_permission(self, request, view):
        if view.action in {"update", "partial_update"}:
            return request.user.is_superuser
        return True


class CanModerate(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.is_moderator(request.user)


class CanDeleteAlert(permissions.BasePermission):
    """ """

    def has_object_permission(self, request, view, obj):
        if view.action in {"destroy"}:
            if request.user.is_superuser:
                return True
            return not obj.sticky and obj in Alert.objects.visible_to(request.user)
        return True


class CanEditSite(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "site") and isinstance(obj.site, Site):
            return obj.site.can_edit(request.user)
        return obj.can_edit(request.user)


class CanRejectReview(permissions.BasePermission):
    """
    Only site moderators can reject publish requests.
    """

    def has_object_permission(self, request, view, obj):
        return obj.is_moderator(request.user)
