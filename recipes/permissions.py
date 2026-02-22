from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow admin users to create/edit/delete official data,
    while allowing other users to read and create user-generated data.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions require admin status
        return request.user and request.user.is_staff


class IsAdminUser(permissions.BasePermission):
    """
    Permission to restrict access to admin-only data and operations.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class CanCreateUserData(permissions.BasePermission):
    """
    Permission to allow authenticated users to create user-generated data
    (is_official=False), but prevent modification of admin data.
    """
    def has_permission(self, request, view):
        # Only authenticated users can create data
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow full access to admin data only for staff users
        if hasattr(obj, 'is_official') and obj.is_official:
            return request.user and request.user.is_staff
        # Allow read access to user-generated data for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        # Allow modification of own user-generated data
        return not obj.is_official


class CanAccessAdminData(permissions.BasePermission):
    """
    Permission to restrict access to official/admin-added data.
    Only staff users can view is_official=True records.
    """
    def has_object_permission(self, request, view, obj):
        # If the object is marked as official, only staff can access it
        if hasattr(obj, 'is_official') and obj.is_official:
            return request.user and request.user.is_staff
        # Non-official data is accessible to all authenticated users
        return True
