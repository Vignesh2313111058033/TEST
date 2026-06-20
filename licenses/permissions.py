from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    message = "Administrator privileges are required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
        )

