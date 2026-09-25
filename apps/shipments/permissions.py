"""
Object-level permissions for the shipments app.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsShipmentParticipant(BasePermission):
    """
    CUSTOMER: only their own shipments.
    DRIVER: only shipments they are actively assigned to.
    MANAGER: every shipment.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == User.Role.MANAGER:
            return True
        if user.role == User.Role.CUSTOMER:
            return obj.customer_id == user.id
        if user.role == User.Role.DRIVER:
            return obj.assignments.filter(driver=user, is_active=True).exists()
        return False


class IsManagerRole(BasePermission):
    """
    Only MANAGER users may create or change driver assignments.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.MANAGER
        )


class CanUpdateShipmentStatus(BasePermission):
    """
    MANAGER can update any shipment's status.
    DRIVER can update the status only of shipments assigned to them.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == User.Role.MANAGER:
            return True
        if user.role == User.Role.DRIVER:
            return obj.assignments.filter(driver=user, is_active=True).exists()
        return False