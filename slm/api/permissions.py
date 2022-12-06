from rest_framework import permissions
from slm.models import Alert, Site


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


class CanModerate(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.is_moderator(request.user)


class CanDeleteAlert(permissions.BasePermission):
    """
    """
    def has_object_permission(self, request, view, obj):
        if view.action in {'destroy'}:
            if request.user.is_superuser:
                return True
            return obj in Alert.objects.for_user(request.user)
        return True


class CanEditSite(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'site') and isinstance(obj.site, Site):
            return obj.site.can_edit(request.user)
        return obj.can_edit(request.user)


class CanRequestReview(permissions.BasePermission):

    def has_permission(self, request, view):
        """
        Anyone with edit permission on a site can request a publish.
        """
        if view.action == 'create' and 'site_name' in request.POST:
            site = Site.objects.filter(
                name__iexact=request.POST['site_name']
            ).first()
            return site and site.can_edit(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        return obj.site.can_edit(request.user)


class CanRejectReview(permissions.BasePermission):
    """
    Only site moderators can reject publish requests.
    """
    def has_object_permission(self, request, view, obj):
        if view.action in {'destroy'}:
            return obj.site.is_moderator(request.user)
        return True
