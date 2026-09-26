 

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsDriverRole(BasePermission):
    """
    Only authenticated DRIVER users. Used for a driver's self-service
    endpoints (profile, availability, location, deliveries).
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.DRIVER
        )


class IsManagerRole(BasePermission):
   
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.MANAGER
        )


class IsDriverOwnerOrManager(BasePermission):
   

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.DRIVER, User.Role.MANAGER)
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == User.Role.MANAGER:
            return True
        return obj.user_id == user.id