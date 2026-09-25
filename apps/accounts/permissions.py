"""
Reusable role-based permission classes for the accounts app.

These are shared across all apps to restrict access based on
the authenticated user's role (CUSTOMER, DRIVER, MANAGER).
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsCustomer(BasePermission):
    """
    Allows access only to authenticated users with the CUSTOMER role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.CUSTOMER
        )


class IsDriver(BasePermission):
    """
    Allows access only to authenticated users with the DRIVER role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.DRIVER
        )


class IsManager(BasePermission):
    """
    Allows access only to authenticated users with the MANAGER role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.MANAGER
        )