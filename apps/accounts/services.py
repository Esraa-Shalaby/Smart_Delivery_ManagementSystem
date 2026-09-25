"""
Business logic (services) for the accounts app.

Views and serializers should call these functions rather than
containing business logic themselves.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

User = get_user_model()


@transaction.atomic
def register_user(*, username, email, password, role=None, first_name="", last_name=""):
    """
    Creates a new user with a securely hashed password.
    """
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    if role is not None:
        user.role = role

    user.set_password(password)
    user.full_clean()
    user.save()
    return user


@transaction.atomic
def update_user(*, user, data):
    """
    Updates basic user information (not password, not role).
    `data` is a dict of field -> new value.
    """
    non_updatable_fields = {"password", "role", "id", "created_at", "updated_at"}

    for field, value in data.items():
        if field in non_updatable_fields:
            continue
        setattr(user, field, value)

    user.full_clean()
    user.save()
    return user


@transaction.atomic
def change_user_role(*, acting_user, target_user, new_role):
    """
    Changes a target user's role. Only a MANAGER may perform this action.
    """
    if not acting_user.is_authenticated or acting_user.role != User.Role.MANAGER:
        raise PermissionError("Only a manager can change a user's role.")

    valid_roles = [choice for choice, _ in User.Role.choices]
    if new_role not in valid_roles:
        raise ValidationError(f"Role must be one of: {', '.join(valid_roles)}.")

    target_user.role = new_role
    target_user.full_clean()
    target_user.save(update_fields=["role", "updated_at"])
    return target_user