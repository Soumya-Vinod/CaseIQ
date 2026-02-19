from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Admin users can write, authenticated users can read.
    """
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(BasePermission):
    """
    Object owner or admin can access the object.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class IsOfficerOrAdmin(BasePermission):
    """
    Only officers and admins can access.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated 
            and request.user.role in ("officer", "admin")
        )