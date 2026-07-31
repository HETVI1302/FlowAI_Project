from rest_framework.permissions import BasePermission

from .models import User


class IsAdminRole(BasePermission):
    """Allows access only to users with the Administrator role."""
    message = 'This action requires administrator privileges.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsOperatorOrAbove(BasePermission):
    """Traffic operators, analysts, and admins — excludes read-only viewers."""
    message = 'This action requires operator-level privileges or higher.'

    ALLOWED_ROLES = {User.Role.ADMIN, User.Role.OPERATOR, User.Role.ANALYST}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )


class IsSelfOrAdmin(BasePermission):
    """Object-level: a user may edit their own profile; admins may edit any."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            obj == request.user or request.user.role == User.Role.ADMIN
        )
