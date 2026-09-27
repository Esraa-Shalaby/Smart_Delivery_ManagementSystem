

from rest_framework.permissions import SAFE_METHODS, BasePermission


def _role(user):
    return getattr(user, "role", None)


def _is_manager(user):
    return bool(
        user
        and user.is_authenticated
        and (_role(user) == "MANAGER" or user.is_staff or user.is_superuser)
    )


class IsManager(BasePermission):

    def has_permission(self, request, view):
        return _is_manager(request.user)


class WarehouseAccessPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if request.method in SAFE_METHODS:
            return True

        return _is_manager(user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS:
            return bool(user and user.is_authenticated)
        return _is_manager(user)