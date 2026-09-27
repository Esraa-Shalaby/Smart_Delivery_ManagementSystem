

from rest_framework.permissions import BasePermission

from .models import Notification


def _role(user):
    return getattr(user, "role", None)


def _is_manager(user):
    return bool(
        user
        and user.is_authenticated
        and (_role(user) == "MANAGER" or user.is_staff or user.is_superuser)
    )


class NotificationAccessPermission(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if obj.recipient_id == user.id:
            return True
        if obj.recipient_id is None and obj.notification_type == Notification.NotificationType.SYSTEM:
            return _is_manager(user)
        return False