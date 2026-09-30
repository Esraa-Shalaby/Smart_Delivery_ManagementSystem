"""Shared helpers for the role-based web views (driver / manager)."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from apps.notifications.services import NotificationError, create_notification


def display_name(user):
    """Full name if the user has one, otherwise the username."""
    if user is None:
        return ""
    return user.get_full_name().strip() or user.username


def human_duration(delta):
    """timedelta -> '1d 4h 12m' (minutes are always shown)."""
    secs = max(int(delta.total_seconds()), 0)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    parts = [f"{days}d" if days else "", f"{hours}h" if hours else "", f"{rem // 60}m"]
    return " ".join(p for p in parts if p)


def notify(recipient, title, message, notification_type, related_id=None):
    """Create a notification without ever breaking the request if it fails."""
    if recipient is None:
        return None
    try:
        return create_notification(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object_id=related_id,
        )
    except NotificationError:
        return None


class RoleOnlyMixin(LoginRequiredMixin):
    """Class-based views: only users with `role` get in, others go to their own dashboard."""

    role = None

    def dispatch(self, request, *args, **kwargs):
        from .views import dashboard_url  # local import avoids a circular import

        user = request.user
        if user.is_authenticated and self.role and user.role != self.role:
            return redirect(dashboard_url(user))
        return super().dispatch(request, *args, **kwargs)


def role_required(role):
    """Function-based views: same rule as RoleOnlyMixin."""

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                from .views import dashboard_url

                return redirect(dashboard_url(request.user))
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def back_or(request, fallback):
    """Redirect to the page the form was submitted from, else `fallback` (a URL name or path)."""
    return redirect(request.META.get("HTTP_REFERER") or fallback)