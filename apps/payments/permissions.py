
from rest_framework.permissions import SAFE_METHODS, BasePermission


def _role(user):
    return getattr(user, "role", None)


def _is_manager(user):
    return bool(user and user.is_authenticated and (_role(user) == "MANAGER" or user.is_staff or user.is_superuser))


def _is_customer(user):
    return bool(user and user.is_authenticated and _role(user) == "CUSTOMER")


def _is_driver(user):
    return bool(user and user.is_authenticated and _role(user) == "DRIVER")


class IsManager(BasePermission):
    """Allows access only to managers (or staff/superusers)."""

    def has_permission(self, request, view):
        return _is_manager(request.user)


class PaymentAccessPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if _is_driver(user):
            return False

        if _is_manager(user):
            return True

        if _is_customer(user):
            # Customers may create their own payments and read (list/retrieve).
            if getattr(view, "action", None) == "create":
                return True
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if _is_driver(user):
            return False

        if _is_manager(user):
            return True

        if _is_customer(user):
            if obj.customer_id != user.id:
                return False
            return request.method in SAFE_METHODS

        return False