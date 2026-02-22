from rest_framework import permissions


class IsAdminOrSelf(permissions.BasePermission):
    """Allow access if user is staff (admin) or is the object itself."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj == request.user
#obj is the customUser instance,meaning the users themselves can edit their profile
# think about creating a core/permissions.py instead of tightly coupling permissions
