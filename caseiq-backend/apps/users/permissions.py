from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Public users can read (GET).
    Authenticated users can read and write.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class IsOwnerOrReadOnly(BasePermission):
    """
    Only the owner of an object can edit it.
    Anyone can read.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user


class IsAdminRole(BasePermission):
    """
    Only users with admin role can access.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsLegalAidOrAdmin(BasePermission):
    """
    Legal aid officers and admins only.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('legal_aid', 'admin')
        )


class OptionalAuthentication(BasePermission):
    """
    Always allow — but views can check request.user.is_authenticated
    to provide enhanced features for logged-in users.
    """
    def has_permission(self, request, view):
        return True