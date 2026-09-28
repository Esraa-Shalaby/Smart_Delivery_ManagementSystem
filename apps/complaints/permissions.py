 
from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsCustomerRole(BasePermission):
     

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.CUSTOMER
        )


class IsManagerRole(BasePermission):
  

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.MANAGER
        )


class IsComplaintParticipant(BasePermission):
    

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.CUSTOMER, User.Role.MANAGER)
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == User.Role.MANAGER:
            return True
        return obj.customer_id == user.id